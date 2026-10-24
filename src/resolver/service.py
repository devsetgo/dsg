# -*- coding: utf-8 -*-
"""
Resolve a requirements file for a target Python/platform and build the report.

Modes:
- upgrade: keep each requirement's name, extras and marker but drop its
  version constraint, then find the newest set that is consistent as a whole.
- validate: honor the file's specifiers as written - "will this install on
  Python 3.x?" - and explain any conflict.
"""

import asyncio
import time
from dataclasses import dataclass

from loguru import logger
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version
from resolvelib import BaseReporter
from resolvelib.resolvers import (
    Resolution,
    ResolutionImpossible,
    ResolutionTooDeep,
    Result,
)
from resolvelib.structs import DirectedGraph

from .environment import PLATFORMS, TargetEnvironment
from .explain import explain_impossible, held_back_reasons, target_label, why_unusable
from .index import (
    PackageNotFound,
    PyPIIndex,
    Release,
    ResolutionCancelled,
    SyncIndexBridge,
)
from .models import LineIssueModel, Mode, PackageResult, ResolutionReport, Vulnerability
from .parse import InputRequirement, parse_requirements
from .provider import Candidate, PipLikeProvider, Req

VULNERABILITY_LOOKUP_CONCURRENCY = 16


@dataclass
class _Outcome:
    result: Result | None = None
    impossible: ResolutionImpossible | None = None
    too_deep: bool = False


def _build_result(state) -> Result:
    """resolvelib's own _build_result, with the route-to-root search done
    iteratively. Upstream (1.2.1, and main as of 2026-10) recurses through
    parents with no visited set, so a dependency cycle among candidates that
    backtracking left disconnected from the root raises RecursionError after
    an otherwise successful resolution."""
    mapping = state.mapping
    key_of = {id(candidate): key for key, candidate in mapping.items()}
    key_of[id(None)] = None
    parents: dict = {}
    children: dict = {}
    for key, criterion in state.criteria.items():
        # A parent that isn't in the mapping any more was backtracked away.
        keys = [key_of[id(p)] for p in criterion.iter_parent() if id(p) in key_of]
        parents[key] = keys
        for parent in keys:
            children.setdefault(parent, []).append(key)

    connected = {None}
    pending = [None]
    while pending:
        for child in children.get(pending.pop(), ()):
            if child not in connected:
                connected.add(child)
                pending.append(child)

    graph: DirectedGraph = DirectedGraph()
    graph.add(None)  # the requirements file, as every root requirement's parent
    for key in state.criteria:
        if key not in connected:
            continue
        if key not in graph:
            graph.add(key)
        for parent in parents[key]:
            if parent not in graph:
                graph.add(parent)
            graph.connect(parent, key)
    return Result(
        mapping={k: v for k, v in mapping.items() if k in connected},
        graph=graph,
        criteria=state.criteria,
    )


def _run_resolver(
    provider: PipLikeProvider, requirements: list[Req], max_rounds: int
) -> _Outcome:
    # Resolver.resolve() is exactly these two steps; see _build_result for
    # why the second is ours.
    resolution = Resolution(provider, BaseReporter())
    try:
        state = resolution.resolve(requirements, max_rounds=max_rounds)
        return _Outcome(result=_build_result(state))
    except ResolutionImpossible as exc:
        return _Outcome(impossible=exc)
    except ResolutionTooDeep:
        return _Outcome(too_deep=True)


def latest_versions(
    releases: list[Release], provider: PipLikeProvider
) -> tuple[Version | None, Version | None]:
    """(newest release overall, newest release the target can install), ignoring pre-releases
    unless a project has nothing else."""
    live = {r.version: r for r in releases if not r.yanked}
    ordered = list(SpecifierSet().filter(live))
    latest = ordered[0] if ordered else None
    compatible = next((v for v in ordered if provider.usable(live[v])), None)
    return latest, compatible


def _requirement_line(
    display: str, extras: list[str], version: str, ir: InputRequirement | None
) -> str:
    line = (
        f"{display}[{','.join(extras)}]=={version}"
        if extras
        else f"{display}=={version}"
    )
    if ir is not None and ir.requirement.marker is not None:
        line += f"; {ir.requirement.marker}"
    return line


# Old pins can carry 20+ advisories; the file stays readable and the result
# page lists every one with links.
MAX_IDS_IN_COMMENT = 5


def _vuln_ids(vulns: list[Vulnerability]) -> str:
    ids = [v.id or "unknown" for v in vulns]
    shown = ", ".join(ids[:MAX_IDS_IN_COMMENT])
    extra = len(ids) - MAX_IDS_IN_COMMENT
    return f"{shown} +{extra} more" if extra > 0 else shown


def annotation(
    current: str | None,
    resolved: str,
    current_vulns: list[Vulnerability],
    resolved_vulns: list[Vulnerability],
    *,
    downgrade_reason: str | None = None,
    builds_from_source: bool = False,
) -> str:
    """The trailing comment on a re-pinned line, in the format the original
    tool used: `# From 1.18.5 | Vulnerabilities: None`. The previous pin's
    advisories are listed too, so an upgrade shows what it fixes, and a
    downgrade or a source build is called out rather than passing as a
    routine change."""
    parts = []
    if current is not None and current != resolved:
        if downgrade_reason is not None:
            previous = f"Downgrade from {current} ({downgrade_reason})"
        else:
            previous = f"From {current}"
        if current_vulns:
            previous += f" (Vulnerabilities: {_vuln_ids(current_vulns)})"
        parts.append(previous)
    if builds_from_source:
        parts.append("Builds from source (no matching wheel)")
    parts.append(
        f"Vulnerabilities: {_vuln_ids(resolved_vulns) if resolved_vulns else 'None'}"
    )
    return " # " + " | ".join(parts)


def has_compatible_wheel(release: Release, target: TargetEnvironment) -> bool:
    return any(
        f.is_wheel
        and not f.yanked
        and target.supports_python(f.requires_python)
        and f.tags & target.tags
        for f in release.files
    )


def _downgrade_reason(
    pinned: Release | None, provider: PipLikeProvider, held_back: list[str]
) -> str:
    """Why the version in the file can't be kept."""
    if pinned is None:
        return "that version is not on PyPI"
    # Yanked files don't count: upgrade mode drops the == pin, and without it
    # the resolver may not pick a yanked release (PEP 592).
    if not provider.usable(pinned):
        # "0.88.0 has no wheel for ..." -> "has no wheel for ..."
        return why_unusable(pinned, provider.target).removeprefix(f"{pinned.version} ")
    # A usable pin newer than the resolved version makes the newest compatible
    # release newer too, so the caller always computed a reason it was held back.
    return held_back[0]


async def _vulnerabilities(
    index: PyPIIndex, pairs: list[tuple[str, str]]
) -> dict[tuple[str, str], list[Vulnerability]]:
    semaphore = asyncio.Semaphore(VULNERABILITY_LOOKUP_CONCURRENCY)

    async def one(name: str, version: str):
        async with semaphore:
            try:
                info = await index.version_info(name, version)
            except Exception as exc:
                logger.warning(
                    f"vulnerability lookup failed for {name} {version}: {exc}"
                )
                return (name, version), []
            return (name, version), [Vulnerability(**v) for v in info.vulnerabilities]

    return dict(await asyncio.gather(*(one(n, v) for n, v in pairs)))


async def _dependency_clashes(
    index: PyPIIndex,
    provider: PipLikeProvider,
    name: str,
    newer: Version,
    releases: list[Release],
    resolved: dict[str, Version],
) -> list[str]:
    """Nothing requires an older `name` directly, so the newer release must
    itself depend on something that clashes with the selected set."""
    fallback = ["an older release was needed for the rest of the set to resolve"]
    # `newer` was picked from these same releases (see latest_versions).
    release = next(r for r in releases if r.version == newer)
    try:
        raw = await index.dependencies(name, release, provider.target.tags)
    except Exception as exc:
        # Only the explanation is lost; the resolution itself stands.
        logger.warning(f"could not read {name} {newer} metadata to explain it: {exc}")
        return fallback
    reasons = []
    for line in raw or []:
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            continue
        if requirement.marker is not None and not requirement.marker.evaluate(
            provider.target.marker_env("")
        ):
            continue
        dep = canonicalize_name(requirement.name)
        if dep in resolved and not requirement.specifier.contains(
            resolved[dep], prereleases=True
        ):
            reasons.append(
                f"{name} {newer} requires {requirement.name}{requirement.specifier}, but {dep} {resolved[dep]} is selected"
            )
    return reasons or fallback


async def resolve_requirements(
    text: str,
    *,
    index: PyPIIndex,
    target: TargetEnvironment,
    mode: Mode = "upgrade",
    timeout: float = 180,
    max_rounds: int = 2000,
) -> ResolutionReport:
    started = time.monotonic()
    parsed = parse_requirements(text)
    issues = [
        LineIssueModel(line_no=i.line_no, line=i.line, reason=i.reason)
        for i in parsed.issues
    ]

    active: list[InputRequirement] = []
    # Lines copied into the output verbatim, keyed by line number so they go
    # back where they were in the pasted file.
    verbatim: list[tuple[int, str]] = list(parsed.passthrough)
    verbatim += [(issue.line_no, issue.line) for issue in parsed.issues]
    for ir in parsed.requirements:
        marker = ir.requirement.marker
        if marker is not None and not marker.evaluate(target.marker_env("")):
            issues.append(
                LineIssueModel(
                    line_no=ir.line_no,
                    line=ir.line,
                    reason=f"Skipped: its marker is false for {target_label(target)}.",
                )
            )
            verbatim.append((ir.line_no, ir.line))
            continue
        active.append(ir)
    issues.sort(key=lambda issue: issue.line_no)

    report = ResolutionReport(
        ok=True,
        python_version=target.python_version,
        platform=target.platform,
        mode=mode,
        issues=issues,
    )
    if not active:
        report.ok = False
        report.error = "No requirements to resolve."
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    reqs = [
        Req.from_requirement(ir.requirement, drop_specifier=(mode == "upgrade"))
        for ir in active
    ]
    bridge = SyncIndexBridge(
        index, asyncio.get_running_loop(), preferred_tags=target.tags
    )
    provider = PipLikeProvider(bridge, target, direct={r.identifier for r in reqs})

    # Fetch every direct requirement's index page concurrently up front; the
    # resolver would otherwise request them one at a time.
    await asyncio.gather(
        *(index.file_rows(r.name) for r in reqs), return_exceptions=True
    )

    try:
        outcome = await asyncio.wait_for(
            asyncio.to_thread(_run_resolver, provider, reqs, max_rounds), timeout
        )
    except TimeoutError:
        # The thread can't be killed; this makes its next index call raise.
        bridge.cancelled.set()
        outcome = None
    except (
        ResolutionCancelled
    ):  # pragma: no cover - only reachable via the timeout path above
        outcome = None

    first_line: dict[str, InputRequirement] = {}
    for ir in active:
        first_line.setdefault(ir.name, ir)

    async def releases_for(name: str) -> list[Release]:
        cached = bridge.cached_releases(name)
        if cached is not None:
            return cached
        try:
            return await index.releases(name)
        except PackageNotFound:
            return []
        except Exception as exc:
            logger.warning(f"could not load releases for {name}: {exc}")
            return []

    async def latest_for(name: str) -> tuple[str | None, str | None]:
        latest, compatible = latest_versions(await releases_for(name), provider)
        return (
            str(latest) if latest else None,
            str(compatible) if compatible else None,
        )

    if outcome is None or outcome.result is None:
        report.ok = False
        if outcome is None:
            report.error = f"Resolution timed out after {int(timeout)} seconds."
        elif outcome.too_deep:
            report.error = f"Gave up after {max_rounds} resolution rounds; the set needs too much backtracking."
        else:
            report.conflicts = explain_impossible(outcome.impossible, provider)
        for name, ir in first_line.items():
            latest, compatible = await latest_for(name)
            report.packages.append(
                PackageResult(
                    name=ir.display_name,
                    extras=sorted(ir.extras),
                    input_spec=str(ir.requirement.specifier) or None,
                    current_version=ir.pinned_version,
                    latest_version=latest,
                    latest_compatible=compatible,
                    is_direct=True,
                )
            )
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    result = outcome.result
    resolved: dict[str, Version] = {}
    extras_of: dict[str, set[str]] = {}
    for candidate in result.mapping.values():
        resolved[candidate.name] = candidate.version
        extras_of.setdefault(candidate.name, set()).update(candidate.extras)

    # resolvelib's graph and criteria still carry requirements from candidates
    # that were pinned during backtracking but ended up unreachable from the
    # root; result.mapping drops those, so they aren't installed and must not
    # be reported as anyone's parent or as a reason something was held back.
    def installed(parent: Candidate | None) -> bool:
        return parent is None or result.mapping.get(parent.identifier) == parent

    def parents_of(name: str) -> list[str]:
        parents: set[str] = set()
        identifiers = [i for i in result.mapping if result.mapping[i].name == name]
        for identifier in identifiers:
            for parent in result.graph.iter_parents(identifier):
                if parent is None:
                    parents.add("(requirements file)")
                elif parent in result.mapping and result.mapping[parent].name != name:
                    parents.add(result.mapping[parent].name)
        return sorted(parents)

    # The resolved versions, plus each direct requirement's current pin when
    # it changed - so the report shows what an upgrade fixes.
    lookups = {(n, str(v)) for n, v in resolved.items()}
    lookups |= {
        (name, ir.pinned_version)
        for name, ir in first_line.items()
        if ir.pinned_version
        and name in resolved
        and ir.pinned_version != str(resolved[name])
    }
    vulns = await _vulnerabilities(index, sorted(lookups))

    for name in sorted(resolved, key=lambda n: (n not in first_line, n)):
        version = resolved[name]
        ir = first_line.get(name)
        latest, compatible = await latest_for(name)
        held_back: list[str] = []
        if compatible is not None and version < Version(compatible):
            informations = []
            for identifier, criterion in result.criteria.items():
                if (
                    result.mapping.get(identifier) is not None
                    and result.mapping[identifier].name == name
                ):
                    informations.extend(
                        info for info in criterion.information if installed(info.parent)
                    )
            held_back = held_back_reasons(
                name, Version(compatible), informations
            ) or await _dependency_clashes(
                index,
                provider,
                name,
                Version(compatible),
                await releases_for(name),
                resolved,
            )
        releases_by_version = {r.version: r for r in await releases_for(name)}
        resolved_release = releases_by_version.get(version)
        downgrade_reason = None
        if ir is not None and ir.pinned_version:
            try:
                pinned = Version(ir.pinned_version)
            except InvalidVersion:
                pinned = None
            if pinned is not None and version < pinned:
                downgrade_reason = _downgrade_reason(
                    releases_by_version.get(pinned), provider, held_back
                )
        report.packages.append(
            PackageResult(
                name=ir.display_name if ir else name,
                downgrade_reason=downgrade_reason,
                builds_from_source=resolved_release is not None
                and not has_compatible_wheel(resolved_release, target),
                extras=sorted(extras_of.get(name, ())),
                input_spec=(str(ir.requirement.specifier) or None) if ir else None,
                current_version=ir.pinned_version if ir else None,
                latest_version=latest,
                latest_compatible=compatible,
                resolved_version=str(version),
                is_direct=ir is not None,
                required_by=parents_of(name),
                held_back_by=held_back,
                vulnerabilities=vulns.get((name, str(version)), []),
                current_vulnerabilities=(
                    vulns.get((name, ir.pinned_version), [])
                    if ir and ir.pinned_version
                    else []
                ),
                metadata_unknown=name in provider.unknown_metadata,
            )
        )

    # requirements.txt: the user's file, in its order, re-pinned; lines this
    # tool can't act on are kept verbatim so the output stays a drop-in file.
    numbered: list[tuple[int, str]] = list(verbatim)
    by_canonical = {canonicalize_name(p.name): p for p in report.packages}
    emitted: set[str] = set()
    for ir in active:
        if ir.name in emitted:
            continue
        emitted.add(ir.name)
        # The user's own extras: ones other packages pull in belong in the lock file only.
        version = str(resolved[ir.name])
        line = _requirement_line(ir.display_name, sorted(ir.extras), version, ir)
        current = ir.pinned_version
        package = by_canonical[ir.name]
        numbered.append(
            (
                ir.line_no,
                line
                + annotation(
                    current,
                    version,
                    vulns.get((ir.name, current), []) if current else [],
                    vulns.get((ir.name, version), []),
                    downgrade_reason=package.downgrade_reason,
                    builds_from_source=package.builds_from_source,
                ),
            )
        )
    lines = [text for _line_no, text in sorted(numbered, key=lambda item: item[0])]
    report.requirements_txt = "\n".join(lines) + "\n"

    header = f"# Resolved for {target_label(target)} ({mode})\n"
    lock_lines = []
    by_name = {canonicalize_name(p.name): p for p in report.packages}
    for name in sorted(by_name):
        package = by_name[name]
        lock_lines.append(
            _requirement_line(
                package.name,
                package.extras,
                package.resolved_version,
                first_line.get(name),
            )
        )
        # Every resolved package is reachable from the requirements file, so
        # it always has at least one parent.
        lock_lines.append(f"    # via {', '.join(package.required_by)}")
    report.lock_txt = header + "\n".join(lock_lines) + "\n"

    if provider.unknown_metadata:
        report.issues.append(
            LineIssueModel(
                line_no=0,
                line=", ".join(sorted(provider.unknown_metadata)),
                reason="These releases publish no dependency metadata (sdist only); their dependencies were not resolved.",
            )
        )
    report.duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        f"resolved {len(active)} requirements -> {len(resolved)} packages for {target.python_version}/"
        f"{PLATFORMS[target.platform]['label']} in {report.duration_ms}ms"
    )
    return report
