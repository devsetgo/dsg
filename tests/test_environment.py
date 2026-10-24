# -*- coding: utf-8 -*-
import pytest
from packaging.markers import Marker
from packaging.tags import Tag

from src.resolver.environment import PLATFORMS, TargetEnvironment


def test_markers_reflect_target_not_running_interpreter():
    env = TargetEnvironment("3.10", "windows-amd64")
    assert Marker('python_version < "3.11"').evaluate(env.marker_env())
    assert Marker('sys_platform == "win32"').evaluate(env.marker_env())
    assert not Marker('platform_system == "Linux"').evaluate(env.marker_env())
    assert Marker('extra == "dev"').evaluate(env.marker_env("dev"))


def test_wheel_tags_for_target():
    env = TargetEnvironment("3.12", "linux-x86_64")
    assert Tag("cp312", "cp312", "manylinux_2_17_x86_64") in env.tags
    assert Tag("cp312", "abi3", "manylinux2014_x86_64") in env.tags
    assert (
        Tag("cp39", "abi3", "manylinux_2_28_x86_64") in env.tags
    )  # abi3 from older CPython
    assert Tag("py3", "none", "any") in env.tags
    assert Tag("cp313", "cp313", "manylinux_2_17_x86_64") not in env.tags
    assert Tag("cp312", "cp312", "win_amd64") not in env.tags


def test_macos_and_windows_tags():
    mac = TargetEnvironment("3.13", "macos-arm64")
    assert Tag("cp313", "cp313", "macosx_11_0_arm64") in mac.tags
    assert Tag("cp313", "cp313", "macosx_14_0_universal2") in mac.tags
    win = TargetEnvironment("3.13", "windows-amd64")
    assert Tag("cp313", "cp313", "win_amd64") in win.tags


def test_requires_python():
    env = TargetEnvironment("3.10")
    assert env.supports_python(None)
    assert env.supports_python(">=3.8")
    assert not env.supports_python(">=3.11")
    assert env.supports_python("not a specifier")  # pip ignores it too


@pytest.mark.parametrize("bad", [{"python_version": "three"}, {"platform": "amiga"}])
def test_invalid_target(bad):
    with pytest.raises(ValueError):
        TargetEnvironment(
            **{"python_version": "3.12", "platform": "linux-x86_64", **bad}
        )


def test_every_platform_builds_tags():
    for key in PLATFORMS:
        assert TargetEnvironment("3.14", key).tags


@pytest.mark.parametrize("version", ["3.8", "3.9", "3.15"])
def test_oldest_and_newest_targets(version):
    major, minor = version.split(".")
    env = TargetEnvironment(version, "linux-x86_64")
    assert (
        Tag(f"cp{major}{minor}", f"cp{major}{minor}", "manylinux_2_17_x86_64")
        in env.tags
    )
    assert Marker(f'python_version == "{version}"').evaluate(env.marker_env())


def test_requires_python_answers_are_cached_across_targets():
    from src.resolver.environment import _python_satisfies

    _python_satisfies.cache_clear()
    for _ in range(3):
        assert TargetEnvironment("3.12", "linux-x86_64").supports_python(">=3.9")
        assert not TargetEnvironment("3.8", "linux-x86_64").supports_python(">=3.9")
        # pip ignores a Requires-Python it can't parse; so do we, and cache that too.
        assert TargetEnvironment("3.12", "linux-x86_64").supports_python("not valid!!")
    info = _python_satisfies.cache_info()
    assert info.misses == 3 and info.hits == 6
