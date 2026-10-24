# -*- coding: utf-8 -*-
"""
Parse requirements.txt text into PEP 508 requirements.

Replaces the old regex `clean_packages`: names, extras, specifiers and markers
come from `packaging.requirements.Requirement`, and anything this resolver
cannot act on (includes, editables, URLs, local paths) is reported back as a
LineIssue instead of being dropped silently.
"""

import re
from dataclasses import dataclass, field

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

# The userinfo part of a URL: `https://user:token@host` -> `https://****@host`.
_URL_CREDENTIALS_RE = re.compile(r"(?P<scheme>\b[a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s]+@")


def redact_credentials(text: str) -> str:
    """Strip credentials from URLs. Pasted files often carry a private index
    (`--extra-index-url https://deploy:<token>@...`); nothing that stores or
    displays submitted text should ever keep the token."""
    return _URL_CREDENTIALS_RE.sub(r"\g<scheme>****@", text)


# pip options that may trail a requirement on the same line.
_TRAILING_OPTION_RE = re.compile(r"\s--(hash|config-settings|global-option)[=\s]\S+")
_COMMENT_RE = re.compile(r"(^|\s+)#.*$")


@dataclass(frozen=True)
class InputRequirement:
    line_no: int
    line: str
    requirement: Requirement

    @property
    def name(self) -> str:
        return canonicalize_name(self.requirement.name)

    @property
    def display_name(self) -> str:
        return self.requirement.name

    @property
    def extras(self) -> frozenset[str]:
        return frozenset(canonicalize_name(e) for e in self.requirement.extras)

    @property
    def pinned_version(self) -> str | None:
        """The version of an exact `==` pin (no wildcard), i.e. what's installed today."""
        specs = list(self.requirement.specifier)
        if (
            len(specs) == 1
            and specs[0].operator in ("==", "===")
            and not specs[0].version.endswith(".*")
        ):
            return specs[0].version
        return None


@dataclass(frozen=True)
class LineIssue:
    line_no: int
    line: str
    reason: str


@dataclass
class ParsedRequirements:
    requirements: list[InputRequirement] = field(default_factory=list)
    issues: list[LineIssue] = field(default_factory=list)
    # Lines carried into the output untouched and not worth a warning:
    # `-r`/`-c` includes, which are routinely pasted along with the file.
    passthrough: list[tuple[int, str]] = field(default_factory=list)


def _logical_lines(text: str):
    """Yield (first line number, joined line), honoring `\\` continuations."""
    buffer: list[str] = []
    start = 0
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not buffer:
            start = line_no
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buffer.append(stripped[:-1])
            continue
        buffer.append(stripped)
        yield start, " ".join(part.strip() for part in buffer)
        buffer = []
    if buffer:
        yield start, " ".join(part.strip() for part in buffer)


def parse_requirements(text: str) -> ParsedRequirements:
    result = ParsedRequirements()
    for line_no, line in _logical_lines(text):
        content = _COMMENT_RE.sub("", line).strip()
        if not content:
            continue
        if content.startswith("-"):
            option = content.split()[0]
            if option in ("-r", "--requirement", "-c", "--constraint"):
                result.passthrough.append((line_no, line))
                continue
            if option in ("-e", "--editable"):
                reason = "Editable installs point at local or VCS sources and can't be resolved from PyPI."
            else:
                reason = f"pip option {option} is ignored."
            result.issues.append(LineIssue(line_no, line, reason))
            continue
        content = _TRAILING_OPTION_RE.sub("", f" {content}").strip()
        try:
            requirement = Requirement(content)
        except InvalidRequirement as exc:
            looks_like_path = content.startswith((".", "/", "~")) or "://" in content
            reason = (
                "Local paths and URLs can't be resolved from PyPI."
                if looks_like_path
                else f"Not a valid requirement: {exc}"
            )
            result.issues.append(LineIssue(line_no, line, reason))
            continue
        if requirement.url:
            result.issues.append(
                LineIssue(
                    line_no,
                    line,
                    "Direct URL requirements are installed as-is; skipped.",
                )
            )
            continue
        result.requirements.append(InputRequirement(line_no, line, requirement))
    return result
