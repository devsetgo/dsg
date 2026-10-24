# -*- coding: utf-8 -*-
"""
Human-readable explanations: why a set can't be resolved, and why a package
resolved to something older than its newest compatible release.
"""

from collections import defaultdict

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from resolvelib.resolvers import RequirementInformation, ResolutionImpossible

from .environment import PLATFORMS, TargetEnvironment
from .index import Release
from .models import Conflict
from .provider import PipLikeProvider, Req


def describe_cause(cause: RequirementInformation) -> str:
    requirement: Req = cause.requirement
    wanted = (
        f"{requirement.identifier}{requirement.specifier}"
        if requirement.specifier
        else f"{requirement.identifier} (any version)"
    )
    if cause.parent is None:
        return f"your requirements file asks for {wanted}"
    return f"{cause.parent.identifier} {cause.parent.version} requires {wanted}"


def why_unusable(release: Release, target: TargetEnvironment) -> str:
    """Explain why pip on the target would skip every file of this release."""
    if release.yanked:
        return f"{release.version} was yanked"
    python_ok = [f for f in release.files if target.supports_python(f.requires_python)]
    if not python_ok:
        requires = sorted(
            {f.requires_python for f in release.files if f.requires_python}
        )
        return f"{release.version} requires Python {' / '.join(requires) or '?'}"
    if any(not f.is_wheel or f.tags & target.tags for f in python_ok):
        # Some file fits the target, so the ones that fit were all yanked.
        return f"{release.version} was yanked"
    return f"{release.version} has no wheel for {target_label(target)} and no source distribution"


def describe_causes(causes: list[RequirementInformation]) -> list[str]:
    """describe_cause for each, but with one line per (parent package, requirement):
    a backtracking resolver typically tried dozens of versions of the same parent."""
    groups: dict[tuple[str | None, str], list[Version]] = defaultdict(list)
    roots: list[str] = []
    for cause in causes:
        if cause.parent is None:
            roots.append(describe_cause(cause))
            continue
        groups[(cause.parent.identifier, str(cause.requirement))].append(
            cause.parent.version
        )
    lines = list(dict.fromkeys(roots))
    for (parent, requirement), versions in groups.items():
        versions = sorted(set(versions))
        if len(versions) == 1:
            span = str(versions[0])
        else:
            span = f"{versions[0]} – {versions[-1]} ({len(versions)} versions)"
        lines.append(f"{parent} {span} requires {requirement}")
    return lines


def target_label(target: TargetEnvironment) -> str:
    return f"Python {target.python_version} on {PLATFORMS[target.platform]['label']}"


def explain_impossible(
    exc: ResolutionImpossible, provider: PipLikeProvider
) -> list[Conflict]:
    target = provider.target
    by_name: dict[str, list[RequirementInformation]] = defaultdict(list)
    for cause in exc.causes:
        by_name[cause.requirement.name].append(cause)

    conflicts: list[Conflict] = []
    for name, causes in by_name.items():
        details = describe_causes(causes)
        if name in provider.not_found:
            conflicts.append(
                Conflict(
                    package=name,
                    message=f"{name} was not found on PyPI.",
                    details=details,
                )
            )
            continue

        releases = [r for r in provider.releases(name) if not r.yanked]
        if not any(provider.usable(r) for r in releases):
            newest = releases[0] if releases else None
            reason = (
                f" The newest release, {why_unusable(newest, target)}."
                if newest
                else ""
            )
            conflicts.append(
                Conflict(
                    package=name,
                    message=f"No release of {name} can be installed on {target_label(target)}.{reason}",
                    details=details,
                )
            )
            continue

        combined = SpecifierSet()
        for cause in causes:
            combined &= cause.requirement.specifier
        by_version = {r.version: r for r in releases}
        in_range = list(combined.filter(by_version))
        if len(details) > 1 and not in_range:
            message = f"The requirements on {name} contradict each other: no version satisfies all of them."
        elif in_range:
            # Versions exist in range, but none can be installed here, or each
            # one's own dependencies clash with the rest of the set.
            unusable = [
                why_unusable(by_version[v], target)
                for v in in_range[:3]
                if not provider.usable(by_version[v])
            ]
            if unusable and len(unusable) == min(3, len(in_range)):
                message = (
                    f"No version of {name} matching {combined or 'the request'} works on {target_label(target)}: "
                    + "; ".join(unusable)
                    + "."
                )
            else:
                message = f"Every version of {name} allowed here ({combined or 'any'}) conflicts with another package's requirements."
        else:
            message = f"No release of {name} matches {combined}."
        conflicts.append(Conflict(package=name, message=message, details=details))
    return conflicts


def held_back_reasons(
    name: str,
    latest_compatible: Version,
    informations: list[RequirementInformation],
) -> list[str]:
    """Which requirements exclude `latest_compatible`, so the resolver chose older."""
    reasons = []
    for info in informations:
        parent = info.parent
        # An extras node pins its own base package to the same version; that
        # pin follows the choice rather than causing it.
        if parent is not None and parent.name == name:
            continue
        if not info.requirement.specifier.contains(latest_compatible, prereleases=True):
            reasons.append(describe_cause(info))
    return list(dict.fromkeys(reasons))
