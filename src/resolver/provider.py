# -*- coding: utf-8 -*-
"""
A resolvelib provider that makes the same choices pip does, for a target
interpreter/platform instead of the running one.

Modeled on pip's own provider (pip/_internal/resolution/resolvelib):
- a package with extras is its own node (`name[extra]`) that depends on the
  plain package at the same version, so extras never fork the version;
- candidates are tried newest first, filtered by every specifier on the
  package, the target's Requires-Python, wheel tag compatibility (an sdist is
  an acceptable fallback, as pip would build it) and the yanked flag;
- pre-releases are only considered when a specifier asks for one or nothing
  else matches (PEP 440 semantics, as implemented by SpecifierSet.filter).
"""

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version
from resolvelib import AbstractProvider
from resolvelib.resolvers import RequirementInformation

from .environment import TargetEnvironment
from .index import PackageNotFound, Release, SyncIndex


def make_identifier(name: str, extras: frozenset[str]) -> str:
    return f"{name}[{','.join(sorted(extras))}]" if extras else name


@dataclass(frozen=True)
class Req:
    name: str  # canonical
    extras: frozenset[str] = frozenset()
    specifier: SpecifierSet = field(default_factory=SpecifierSet)
    # The original PEP 508 text, kept for messages.
    text: str = ""

    @property
    def identifier(self) -> str:
        return make_identifier(self.name, self.extras)

    @classmethod
    def from_requirement(
        cls, requirement: Requirement, *, drop_specifier: bool = False
    ) -> "Req":
        specifier = SpecifierSet() if drop_specifier else requirement.specifier
        name = canonicalize_name(requirement.name)
        extras = frozenset(canonicalize_name(e) for e in requirement.extras)
        text = f"{make_identifier(name, extras)}{specifier}"
        return cls(name, extras, specifier, text)

    def __str__(self) -> str:
        return self.text or f"{self.identifier}{self.specifier}"


@dataclass(frozen=True)
class Candidate:
    name: str
    version: Version
    extras: frozenset[str] = frozenset()
    release: Release | None = field(default=None, compare=False, hash=False, repr=False)

    @property
    def identifier(self) -> str:
        return make_identifier(self.name, self.extras)

    def __str__(self) -> str:
        return f"{self.identifier} {self.version}"


class PipLikeProvider(AbstractProvider):
    def __init__(
        self, index: SyncIndex, target: TargetEnvironment, direct: Iterable[str] = ()
    ) -> None:
        self.index = index
        self.target = target
        self.direct = set(direct)
        self.not_found: set[str] = set()
        self.unknown_metadata: set[str] = set()
        self.invalid_dependencies: list[str] = []

    # ---- identity -------------------------------------------------------

    def identify(self, requirement_or_candidate) -> str:
        return requirement_or_candidate.identifier

    # ---- ordering -------------------------------------------------------

    def get_preference(
        self,
        identifier: str,
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterator[RequirementInformation]],
        backtrack_causes: Sequence[RequirementInformation],
    ):
        # Lower sorts first. Same priorities as pip: work on whatever caused
        # the last backtrack, then exact pins (cheap, rarely wrong), then the
        # user's direct requirements, then everything else alphabetically for
        # determinism.
        infos = list(information[identifier])
        pinned = any(
            spec.operator in ("==", "===") and "*" not in spec.version
            for info in infos
            for spec in info.requirement.specifier
        )
        is_cause = any(
            cause.requirement.name == identifier.split("[")[0]
            or (
                cause.parent is not None
                and cause.parent.name == identifier.split("[")[0]
            )
            for cause in backtrack_causes
        )
        is_direct = identifier in self.direct
        return (not is_cause, not pinned, not is_direct, identifier)

    # ---- candidates -----------------------------------------------------

    def usable(self, release: Release, *, allow_yanked: bool = False) -> bool:
        """Whether pip on the target would install some file of this release."""
        files = [
            f
            for f in release.files
            if self.target.supports_python(f.requires_python)
            and (allow_yanked or not f.yanked)
        ]
        tags = self.target.tags
        return any(not f.is_wheel or f.tags & tags for f in files)

    def releases(self, name: str) -> list[Release]:
        try:
            return self.index.get_releases(name)
        except PackageNotFound:
            self.not_found.add(name)
            return []

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator[Req]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
    ) -> list[Candidate]:
        reqs = list(requirements[identifier])
        if not reqs:
            return []
        name = reqs[0].name
        extras = frozenset().union(*(r.extras for r in reqs))
        specifier = SpecifierSet()
        for r in reqs:
            specifier &= r.specifier
        bad = {c.version for c in incompatibilities[identifier]}

        by_version = {r.version: r for r in self.releases(name)}
        # An exact == pin may select a yanked release (PEP 592); nothing else may.
        exact_pins = {
            Version(s.version)
            for s in specifier
            if s.operator in ("==", "===") and "*" not in s.version
        }
        allowed = [v for v in specifier.filter(by_version) if v not in bad]
        matches = [
            Candidate(name, v, extras, by_version[v])
            for v in allowed
            if self.usable(by_version[v], allow_yanked=v in exact_pins)
        ]
        if matches:
            # Warm the metadata for the versions resolvelib will try first.
            self.index.prefetch_dependencies(name, (c.release for c in matches))
        return matches

    def is_satisfied_by(self, requirement: Req, candidate: Candidate) -> bool:
        return (
            requirement.name == candidate.name
            and requirement.extras <= candidate.extras
            and requirement.specifier.contains(candidate.version, prereleases=True)
        )

    # ---- dependencies ---------------------------------------------------

    def _applies(self, marker: Marker | None, extras: Iterable[str]) -> bool:
        if marker is None:
            return True
        return any(marker.evaluate(self.target.marker_env(extra)) for extra in extras)

    def get_dependencies(self, candidate: Candidate) -> list[Req]:
        raw = self.index.get_dependencies(candidate.name, candidate.release)
        if raw is None:
            self.unknown_metadata.add(candidate.name)
            raw = []

        deps: list[Req] = []
        if candidate.extras:
            # The extras node pins the base package to the same version and
            # adds only the requirements that its extras switch on.
            deps.append(
                Req(
                    candidate.name,
                    frozenset(),
                    SpecifierSet(f"=={candidate.version}"),
                    f"{candidate.name}=={candidate.version}",
                )
            )
            evaluate_with = [canonicalize_name(e) for e in sorted(candidate.extras)]
        else:
            evaluate_with = [""]

        for line in raw:
            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                self.invalid_dependencies.append(f"{candidate}: {line}")
                continue
            if requirement.url:
                continue
            if candidate.extras and self._applies(requirement.marker, [""]):
                # Not gated on an extra: the base node already contributes it.
                continue
            if not self._applies(requirement.marker, evaluate_with):
                continue
            deps.append(Req.from_requirement(requirement))

        self.index.prefetch_releases(d.name for d in deps)
        return deps
