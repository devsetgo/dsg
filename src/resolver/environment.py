# -*- coding: utf-8 -*-
"""
The interpreter and platform a requirements file is being resolved *for*.

pip evaluates environment markers and wheel compatibility against the running
interpreter; this resolver runs on one Python but answers for another, so the
marker environment and the wheel tag set are synthesized from the target.
"""

from dataclasses import dataclass
from functools import cached_property, lru_cache

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.tags import Tag, compatible_tags, cpython_tags
from packaging.version import Version

# Platform keys offered in the form, mapped to marker values and the wheel
# platform tags pip on that platform would accept (newest first).
_MANYLINUX_GLIBC_MINORS = range(39, 16, -1)  # glibc 2.39 (current distros) down to 2.17


def _manylinux(arch: str) -> list[str]:
    tags = [f"manylinux_2_{minor}_{arch}" for minor in _MANYLINUX_GLIBC_MINORS]
    # Legacy aliases still used by many projects: 2014 == 2_17, 2010 == 2_12, 1 == 2_5.
    tags += [f"manylinux2014_{arch}"]
    if arch == "x86_64":
        tags += [
            f"manylinux_2_12_{arch}",
            f"manylinux2010_{arch}",
            f"manylinux_2_5_{arch}",
            f"manylinux1_{arch}",
        ]
    tags += [f"linux_{arch}"]
    return tags


def _macos_arm64() -> list[str]:
    tags: list[str] = []
    for major in range(15, 10, -1):
        tags += [f"macosx_{major}_0_arm64", f"macosx_{major}_0_universal2"]
    return tags


PLATFORMS: dict[str, dict] = {
    "linux-x86_64": {
        "label": "Linux x86_64",
        "markers": {
            "sys_platform": "linux",
            "platform_system": "Linux",
            "platform_machine": "x86_64",
            "os_name": "posix",
        },
        "tags": _manylinux("x86_64"),
    },
    "linux-aarch64": {
        "label": "Linux aarch64",
        "markers": {
            "sys_platform": "linux",
            "platform_system": "Linux",
            "platform_machine": "aarch64",
            "os_name": "posix",
        },
        "tags": _manylinux("aarch64"),
    },
    "macos-arm64": {
        "label": "macOS Apple Silicon",
        "markers": {
            "sys_platform": "darwin",
            "platform_system": "Darwin",
            "platform_machine": "arm64",
            "os_name": "posix",
        },
        "tags": _macos_arm64(),
    },
    "windows-amd64": {
        "label": "Windows x64",
        "markers": {
            "sys_platform": "win32",
            "platform_system": "Windows",
            "platform_machine": "AMD64",
            "os_name": "nt",
        },
        "tags": ["win_amd64"],
    },
}
DEFAULT_PLATFORM = "linux-x86_64"


@dataclass(frozen=True)
class TargetEnvironment:
    python_version: str = "3.14"
    platform: str = DEFAULT_PLATFORM

    def __post_init__(self):
        if self.platform not in PLATFORMS:
            raise ValueError(
                f"Unknown platform {self.platform!r}; expected one of {sorted(PLATFORMS)}"
            )
        _ = self.version_tuple  # parse eagerly so a bad version fails at construction

    @cached_property
    def version_tuple(self) -> tuple[int, int]:
        parts = self.python_version.split(".")
        if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
            raise ValueError(f"Invalid python version {self.python_version!r}")
        return int(parts[0]), int(parts[1])

    @cached_property
    def full_version(self) -> Version:
        # A feature release's ".0" - patch-level markers are rare, and every
        # patch of a series satisfies the same Requires-Python in practice.
        major, minor = self.version_tuple
        return Version(f"{major}.{minor}.0")

    @cached_property
    def markers(self) -> dict[str, str]:
        major, minor = self.version_tuple
        return {
            "python_version": f"{major}.{minor}",
            "python_full_version": str(self.full_version),
            "implementation_name": "cpython",
            "implementation_version": str(self.full_version),
            "platform_python_implementation": "CPython",
            "platform_release": "",
            "platform_version": "",
            **PLATFORMS[self.platform]["markers"],
        }

    def marker_env(self, extra: str = "") -> dict[str, str]:
        return {**self.markers, "extra": extra}

    @cached_property
    def tags(self) -> frozenset[Tag]:
        major, minor = self.version_tuple
        platforms = PLATFORMS[self.platform]["tags"]
        # Pass the ABI explicitly: left as None, packaging derives it from the
        # *running* interpreter's sysconfig, not the target's.
        abi = f"cp{major}{minor}"
        tags = list(
            cpython_tags(python_version=(major, minor), abis=[abi], platforms=platforms)
        )
        tags += list(
            compatible_tags(
                python_version=(major, minor), interpreter=abi, platforms=platforms
            )
        )
        return frozenset(tags)

    def supports_python(self, requires_python: str | None) -> bool:
        if not requires_python:
            return True
        return _python_satisfies(requires_python, self.full_version)


# Every file of every release carries a Requires-Python, but only a few
# distinct strings exist; a check asks about each one ~100k times while
# resolving, and parsing the SpecifierSet each time was half the CPU of a warm
# check. Shared across checks: the answer for (string, version) never changes.
@lru_cache(maxsize=8192)
def _python_satisfies(requires_python: str, version: Version) -> bool:
    try:
        return SpecifierSet(requires_python).contains(version, prereleases=True)
    except InvalidSpecifier:
        # pip ignores an unparseable Requires-Python rather than rejecting the file.
        return True
