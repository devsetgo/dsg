# -*- coding: utf-8 -*-
"""Pydantic models for a resolution report (stored as JSON on the Check row)."""

from typing import Literal

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, Field

Mode = Literal["upgrade", "validate"]


class Vulnerability(BaseModel):
    id: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str | None = None
    fixed_in: list[str] = Field(default_factory=list)
    link: str | None = None


class PackageResult(BaseModel):
    name: str
    extras: list[str] = Field(default_factory=list)
    input_spec: str | None = None
    current_version: str | None = None
    latest_version: str | None = None
    latest_compatible: str | None = None
    resolved_version: str | None = None
    is_direct: bool = True
    required_by: list[str] = Field(default_factory=list)
    held_back_by: list[str] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    # Advisories against the version pinned in the submitted file, if it changed.
    current_vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    metadata_unknown: bool = False
    # Why the version in the submitted file can't be kept, when the result
    # is older than it (e.g. "0.88.0 has no wheel for Python 3.15 on ...").
    downgrade_reason: str | None = None
    # No wheel matches the target, so pip would build the sdist (needs a
    # compiler/toolchain for packages with native code).
    builds_from_source: bool = False

    @property
    def is_held_back(self) -> bool:
        return bool(self.held_back_by)

    @property
    def change(self) -> Literal["upgrade", "downgrade", "unchanged", "new", "none"]:
        if self.resolved_version is None:
            return "none"
        if self.current_version is None:
            return "new"
        try:
            current, resolved = Version(self.current_version), Version(
                self.resolved_version
            )
        except InvalidVersion:
            return "new"
        if resolved > current:
            return "upgrade"
        if resolved < current:
            return "downgrade"
        return "unchanged"


class Conflict(BaseModel):
    package: str
    message: str
    details: list[str] = Field(default_factory=list)


class LineIssueModel(BaseModel):
    line_no: int
    line: str
    reason: str


class ResolutionReport(BaseModel):
    ok: bool
    python_version: str
    platform: str
    mode: Mode
    packages: list[PackageResult] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    issues: list[LineIssueModel] = Field(default_factory=list)
    requirements_txt: str = ""
    lock_txt: str = ""
    duration_ms: int = 0
    error: str | None = None

    @property
    def direct(self) -> list[PackageResult]:
        return [p for p in self.packages if p.is_direct]

    @property
    def transitive(self) -> list[PackageResult]:
        return [p for p in self.packages if not p.is_direct]

    def counts(self) -> dict[str, int]:
        direct = self.direct
        return {
            "direct": len(direct),
            "transitive": len(self.transitive),
            "upgrades": sum(p.change == "upgrade" for p in direct),
            "held_back": sum(p.is_held_back for p in self.packages),
            "vulnerable": sum(bool(p.vulnerabilities) for p in self.packages),
            "downgrades": sum(p.change == "downgrade" for p in direct),
            "from_source": sum(p.builds_from_source for p in self.packages),
            "fixed": sum(
                bool(p.current_vulnerabilities) and not p.vulnerabilities
                for p in self.direct
            ),
            "conflicts": len(self.conflicts),
            "issues": len(self.issues),
        }
