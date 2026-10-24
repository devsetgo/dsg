# -*- coding: utf-8 -*-
"""Resolution behavior against a fake PyPI (see tests/fakepypi.py)."""


def by_name(report):
    return {p.name.lower(): p for p in report.packages}


async def test_upgrade_picks_newest_and_reports_change(resolve):
    spec = {"a": {"1.0": {}, "1.5": {}, "2.0": {}}}
    report, _ = await resolve(spec, "a==1.0")
    assert report.ok
    a = by_name(report)["a"]
    assert (a.current_version, a.resolved_version, a.latest_version) == (
        "1.0",
        "2.0",
        "2.0",
    )
    assert a.change == "upgrade"
    assert report.requirements_txt == "a==2.0 # From 1.0 | Vulnerabilities: None\n"


async def test_requires_python_selects_older_release(resolve):
    spec = {
        "lib": {
            "1.0": {"requires_python": ">=3.8"},
            "2.0": {"requires_python": ">=3.12"},
        }
    }
    old, _ = await resolve(spec, "lib", python="3.10")
    new, _ = await resolve(spec, "lib", python="3.12")
    lib_old = by_name(old)["lib"]
    assert lib_old.resolved_version == "1.0"
    assert (lib_old.latest_version, lib_old.latest_compatible) == ("2.0", "1.0")
    assert lib_old.held_back_by == []  # not held back: 1.0 IS the newest compatible
    assert by_name(new)["lib"].resolved_version == "2.0"


async def test_transitive_dependencies_and_via(resolve):
    spec = {
        "app": {"1.0": {"deps": ["core>=2"]}},
        "core": {"1.0": {}, "2.0": {}, "2.1": {}},
    }
    report, _ = await resolve(spec, "app")
    core = by_name(report)["core"]
    assert not core.is_direct
    assert core.resolved_version == "2.1"
    assert core.required_by == ["app"]
    assert "core==2.1\n    # via app" in report.lock_txt
    assert (
        report.requirements_txt == "app==1.0 # Vulnerabilities: None\n"
    )  # transitive deps only in the lock


async def test_markers_on_dependencies_evaluated_for_target(resolve):
    spec = {
        "app": {
            "1.0": {
                "deps": [
                    'backport; python_version < "3.11"',
                    'winonly; sys_platform == "win32"',
                ]
            }
        },
        "backport": {"1.0": {}},
        "winonly": {"1.0": {}},
    }
    r310, _ = await resolve(spec, "app", python="3.10")
    r312, _ = await resolve(spec, "app", python="3.12")
    rwin, _ = await resolve(spec, "app", python="3.12", platform="windows-amd64")
    assert set(by_name(r310)) == {"app", "backport"}
    assert set(by_name(r312)) == {"app"}
    assert set(by_name(rwin)) == {"app", "winonly"}


async def test_top_level_marker_false_is_skipped_and_kept_in_output(resolve):
    spec = {"requests": {"2.0": {}}}
    report, _ = await resolve(spec, 'requests\npywin32; sys_platform == "win32"')
    assert set(by_name(report)) == {"requests"}
    assert any("marker is false" in issue.reason for issue in report.issues)
    assert 'pywin32; sys_platform == "win32"' in report.requirements_txt


async def test_extras_pull_in_extra_dependencies(resolve):
    spec = {
        "web": {"1.0": {"deps": ["core", 'fast-json; extra == "speed"']}},
        "core": {"1.0": {}},
        "fast-json": {"3.0": {}},
    }
    plain, _ = await resolve(spec, "web")
    extra, _ = await resolve(spec, "web[speed]")
    assert set(by_name(plain)) == {"web", "core"}
    assert set(by_name(extra)) == {"web", "core", "fast-json"}
    assert by_name(extra)["web"].extras == ["speed"]
    assert extra.requirements_txt == "web[speed]==1.0 # Vulnerabilities: None\n"


async def test_backtracking_and_held_back_attribution(resolve):
    # newest app needs core>=2 but tool pins core<2, so app must fall back.
    spec = {
        "app": {"1.0": {"deps": ["core<2"]}, "2.0": {"deps": ["core>=2"]}},
        "tool": {"1.0": {"deps": ["core<2"]}},
        "core": {"1.5": {}, "2.0": {}},
    }
    report, _ = await resolve(spec, "app\ntool")
    assert report.ok
    packages = by_name(report)
    assert packages["app"].resolved_version == "1.0"
    assert packages["core"].resolved_version == "1.5"
    # core is capped directly by requirements...
    assert any("tool 1.0 requires core<2" in r for r in packages["core"].held_back_by)
    # ...app only indirectly: its newest release needs a core that's not selected.
    assert packages["app"].held_back_by == [
        "app 2.0 requires core>=2, but core 1.5 is selected"
    ]


async def test_validate_mode_keeps_pins(resolve):
    spec = {"a": {"1.0": {}, "2.0": {}}}
    report, _ = await resolve(spec, "a==1.0", mode="validate")
    a = by_name(report)["a"]
    assert a.resolved_version == "1.0"
    assert a.change == "unchanged"
    assert a.held_back_by == ["your requirements file asks for a==1.0"]


async def test_conflict_between_requirements_is_explained(resolve):
    spec = {
        "a": {"1.0": {"deps": ["c<2"]}},
        "b": {"1.0": {"deps": ["c>=2"]}},
        "c": {"1.0": {}, "2.0": {}},
    }
    report, _ = await resolve(spec, "a\nb")
    assert not report.ok
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert conflict.package == "c"
    assert "contradict" in conflict.message
    assert set(conflict.details) == {"a 1.0 requires c<2", "b 1.0 requires c>=2"}
    # the direct packages are still listed with their latest versions
    assert {p.name for p in report.packages} == {"a", "b"}
    assert by_name(report)["a"].latest_version == "1.0"


async def test_pinned_version_unsupported_on_target_python(resolve):
    spec = {
        "numpy": {
            "1.0": {"requires_python": ">=3.8"},
            "2.0": {"requires_python": ">=3.12"},
        }
    }
    report, _ = await resolve(spec, "numpy==2.0", python="3.10", mode="validate")
    assert not report.ok
    message = report.conflicts[0].message
    assert (
        "numpy" in message
        and "Python 3.10" in message
        and "requires Python >=3.12" in message
    )


async def test_no_release_supports_target(resolve):
    spec = {"newpkg": {"1.0": {"requires_python": ">=3.13"}}}
    report, _ = await resolve(spec, "newpkg", python="3.10")
    assert not report.ok
    assert (
        "No release of newpkg can be installed on Python 3.10"
        in report.conflicts[0].message
    )


async def test_unknown_package(resolve):
    report, _ = await resolve({"requests": {"2.0": {}}}, "requests\ndoes-not-exist")
    assert not report.ok
    assert report.conflicts[0].message == "does-not-exist was not found on PyPI."


async def test_yanked_releases_skipped_unless_pinned(resolve):
    spec = {"a": {"1.0": {}, "1.1": {"yanked": True}}}
    upgraded, _ = await resolve(spec, "a")
    pinned, _ = await resolve(spec, "a==1.1", mode="validate")
    assert by_name(upgraded)["a"].resolved_version == "1.0"
    assert by_name(upgraded)["a"].latest_version == "1.0"
    assert by_name(pinned)["a"].resolved_version == "1.1"


async def test_wheel_tags_and_sdist_fallback(resolve):
    spec = {
        # 2.0 only has a Windows wheel: unusable on Linux. 1.0 is universal.
        "winwheel": {"1.0": {}, "2.0": {"wheel": "cp312-cp312-win_amd64"}},
        # sdist-only release: installable (pip would build it).
        "sdistonly": {"1.0": {"wheel": None, "sdist": True, "json_deps": []}},
    }
    linux, _ = await resolve(spec, "winwheel\nsdistonly")
    windows, _ = await resolve(spec, "winwheel", platform="windows-amd64")
    assert by_name(linux)["winwheel"].resolved_version == "1.0"
    assert by_name(linux)["sdistonly"].resolved_version == "1.0"
    assert by_name(windows)["winwheel"].resolved_version == "2.0"


async def test_sdist_without_metadata_is_flagged(resolve):
    spec = {"oldpkg": {"0.1": {"wheel": None, "sdist": True}}}
    report, _ = await resolve(spec, "oldpkg")
    assert report.ok
    assert by_name(report)["oldpkg"].metadata_unknown
    assert any("no dependency metadata" in issue.reason for issue in report.issues)


async def test_json_api_fallback_when_no_pep658_metadata(resolve):
    spec = {"app": {"1.0": {"deps": ["core"], "metadata": False}}, "core": {"1.0": {}}}
    report, fake = await resolve(spec, "app")
    assert set(by_name(report)) == {"app", "core"}
    assert fake.count("/pypi/app/1.0/json") >= 1


async def test_prereleases_only_when_nothing_else(resolve):
    spec = {
        "stable": {"1.0": {}, "2.0b1": {}},
        "nightly": {"0.1.dev1": {}, "0.2.dev1": {}},
    }
    report, _ = await resolve(spec, "stable\nnightly")
    packages = by_name(report)
    assert packages["stable"].resolved_version == "1.0"
    assert packages["nightly"].resolved_version == "0.2.dev1"
    explicit, _ = await resolve(spec, "stable>=2.0b1", mode="validate")
    assert by_name(explicit)["stable"].resolved_version == "2.0b1"


async def test_vulnerabilities_attached_to_resolved_version(resolve):
    spec = {
        "lib": {"1.0": {"vulns": [{"id": "PYSEC-1", "fixed_in": ["1.1"]}]}, "1.1": {}}
    }
    pinned, _ = await resolve(spec, "lib==1.0", mode="validate")
    upgraded, _ = await resolve(spec, "lib==1.0")
    vulns = by_name(pinned)["lib"].vulnerabilities
    assert [v.id for v in vulns] == ["PYSEC-1"] and vulns[0].fixed_in == ["1.1"]
    assert by_name(upgraded)["lib"].vulnerabilities == []
    assert pinned.counts()["vulnerable"] == 1


async def test_output_keeps_unresolvable_lines_in_place(resolve):
    spec = {"a": {"1.0": {}}, "b": {"2.0": {}}}
    text = (
        "-r prd.txt\n"
        "a>=0.5 ; python_version >= '3.8'\n"
        'pywin32; sys_platform == "win32"\n'
        "-e ./local\n"
        "b\n"
    )
    report, _ = await resolve(spec, text)
    assert report.requirements_txt.splitlines() == [
        "-r prd.txt",
        'a==1.0; python_version >= "3.8" # Vulnerabilities: None',
        'pywin32; sys_platform == "win32"',
        "-e ./local",
        "b==2.0 # Vulnerabilities: None",
    ]
    # The include is not a warning; the other two kept lines still are.
    assert [issue.line_no for issue in report.issues] == [3, 4]


async def test_nothing_to_resolve(resolve):
    report, _ = await resolve({}, "# only a comment\n-r other.txt")
    assert not report.ok
    assert report.error == "No requirements to resolve."


async def test_timeout_reports_error(resolve):
    spec = {"a": {"1.0": {}}}
    report, _ = await resolve(spec, "a", timeout=0)
    assert not report.ok
    assert "timed out" in report.error


async def test_too_many_rounds(resolve):
    spec = {
        "a": {"1.0": {"deps": ["b"]}},
        "b": {"1.0": {"deps": ["c"]}},
        "c": {"1.0": {}},
    }
    report, _ = await resolve(spec, "a", max_rounds=1)
    assert not report.ok
    assert "rounds" in report.error


async def test_sample_file_parses_and_counts(resolve):
    with open("tests/fixtures/sample_requirements.txt") as handle:
        text = handle.read()
    # Every package unknown to the fake index: all reported as not found,
    # which exercises explain over a large input without the network.
    report, _ = await resolve({}, text)
    assert not report.ok
    assert len(report.packages) == 96


async def test_output_annotates_previous_and_new_vulnerabilities(resolve):
    spec = {
        "lib": {
            "1.0": {"vulns": [{"id": "PYSEC-1"}, {"id": "GHSA-2"}]},
            "1.1": {"vulns": [{"id": "PYSEC-9"}]},
            "2.0": {},
        },
        "same": {"3.0": {"vulns": [{"id": "CVE-3"}]}},
    }
    upgraded, _ = await resolve(spec, "lib==1.0\nsame==3.0")
    assert upgraded.requirements_txt.splitlines() == [
        "lib==2.0 # From 1.0 (Vulnerabilities: PYSEC-1, GHSA-2) | Vulnerabilities: None",
        "same==3.0 # Vulnerabilities: CVE-3",
    ]
    lib = by_name(upgraded)["lib"]
    assert [v.id for v in lib.current_vulnerabilities] == ["PYSEC-1", "GHSA-2"]
    assert lib.vulnerabilities == []
    assert upgraded.counts()["fixed"] == 1
    # A new version that is itself vulnerable gets its own advisories listed.
    held, _ = await resolve(spec, "lib==1.0\n", mode="validate")
    assert held.requirements_txt == "lib==1.0 # Vulnerabilities: PYSEC-1, GHSA-2\n"
    stepped, _ = await resolve(
        {"lib": {**spec["lib"], "2.0": {"requires_python": ">=3.13"}}},
        "lib==1.0",
        python="3.12",
    )
    assert stepped.requirements_txt == (
        "lib==1.1 # From 1.0 (Vulnerabilities: PYSEC-1, GHSA-2) | Vulnerabilities: PYSEC-9\n"
    )


def test_long_vulnerability_lists_are_shortened():
    from src.resolver.models import Vulnerability
    from src.resolver.service import annotation

    many = [Vulnerability(id=f"V-{i}") for i in range(8)]
    assert annotation("1.0", "2.0", many, []) == (
        " # From 1.0 (Vulnerabilities: V-0, V-1, V-2, V-3, V-4 +3 more) | Vulnerabilities: None"
    )
    assert annotation("1.0", "1.0", many, many).endswith("V-4 +3 more")


async def test_downgrade_is_flagged_with_reason_and_source_build(resolve):
    # The robyn-on-3.15 case: the pinned release only has cp314 wheels, and the
    # newest release installable on 3.15 is an old sdist.
    spec = {
        "fw": {
            "0.69.0": {"wheel": None, "sdist": True, "json_deps": []},
            "0.88.0": {"wheel": "cp314-cp314-manylinux_2_17_x86_64"},
        }
    }
    report, _ = await resolve(spec, "fw==0.88.0", python="3.15")
    fw = by_name(report)["fw"]
    assert fw.change == "downgrade"
    assert fw.builds_from_source
    assert fw.downgrade_reason == (
        "has no wheel for Python 3.15 on Linux x86_64 and no source distribution"
    )
    assert report.requirements_txt == (
        "fw==0.69.0 # Downgrade from 0.88.0 (has no wheel for Python 3.15 on Linux x86_64"
        " and no source distribution) | Builds from source (no matching wheel)"
        " | Vulnerabilities: None\n"
    )
    assert report.counts()["downgrades"] == 1 and report.counts()["from_source"] == 1
    # Same file on 3.14: the wheel fits, nothing to flag.
    same, _ = await resolve(spec, "fw==0.88.0", python="3.14")
    assert same.requirements_txt == "fw==0.88.0 # Vulnerabilities: None\n"


async def test_downgrade_for_requires_python(resolve):
    spec = {"lib": {"1.0": {}, "2.0": {"requires_python": ">=3.12"}}}
    report, _ = await resolve(spec, "lib==2.0", python="3.10")
    assert report.requirements_txt == (
        "lib==1.0 # Downgrade from 2.0 (requires Python >=3.12) | Vulnerabilities: None\n"
    )


async def test_source_build_without_downgrade(resolve):
    spec = {
        "native": {
            "1.0": {"wheel": "cp312-cp312-win_amd64", "sdist": True, "json_deps": []}
        }
    }
    report, _ = await resolve(spec, "native==1.0")
    assert report.requirements_txt == (
        "native==1.0 # Builds from source (no matching wheel) | Vulnerabilities: None\n"
    )


async def test_vulnerability_lookup_failure_does_not_fail_the_check(
    resolve, monkeypatch
):
    from src.resolver.index import PyPIIndex

    async def advisory_feed_down(self, name, version):
        raise RuntimeError("advisory feed down")

    monkeypatch.setattr(PyPIIndex, "version_info", advisory_feed_down)
    report, _ = await resolve({"a": {"1.0": {}}}, "a")
    assert report.ok
    assert by_name(report)["a"].vulnerabilities == []


async def test_release_load_failure_leaves_latest_empty(resolve, monkeypatch):
    from src.resolver.index import PyPIIndex, SyncIndexBridge

    async def index_down(self, name):
        raise RuntimeError("index down")

    # Force the report to fetch releases itself rather than reuse the resolver's.
    monkeypatch.setattr(SyncIndexBridge, "cached_releases", lambda self, name: None)
    monkeypatch.setattr(PyPIIndex, "releases", index_down)
    report, _ = await resolve({"a": {"1.0": {}}}, "a==1.0", timeout=0)
    assert "timed out" in report.error
    a = by_name(report)["a"]
    assert a.current_version == "1.0"
    assert a.latest_version is None
    assert a.latest_compatible is None


def test_redact_credentials():
    from src.resolver.parse import redact_credentials

    text = (
        "--index-url https://user:p%40ss@pypi.corp.example/simple\n"
        "-i http://token@10.0.0.5:8080/simple\n"
        "git+https://oauth2:abc@gitlab.example/x.git\n"
        "requests  # see https://docs.example/a@b\n"
    )
    assert redact_credentials(text) == (
        "--index-url https://****@pypi.corp.example/simple\n"
        "-i http://****@10.0.0.5:8080/simple\n"
        "git+https://****@gitlab.example/x.git\n"
        "requests  # see https://docs.example/a@b\n"
    )


async def test_downgrade_when_pinned_version_is_not_on_pypi(resolve):
    report, _ = await resolve({"lib": {"1.0": {}}}, "lib==9.9")
    assert by_name(report)["lib"].downgrade_reason == "that version is not on PyPI"


async def test_downgrade_names_what_holds_the_package_back(resolve):
    spec = {
        "a": {"1.0": {}, "2.0": {}},
        "b": {"1.0": {"deps": ["a<2"]}},
    }
    report, _ = await resolve(spec, "a==2.0\nb")
    a = by_name(report)["a"]
    assert a.resolved_version == "1.0"
    assert a.downgrade_reason == a.held_back_by[0]
    assert "b 1.0" in a.downgrade_reason


async def test_unreadable_metadata_keeps_a_generic_held_back_reason(
    resolve, monkeypatch, logged
):
    # x 2.0 needs y<1, but y is pinned at 1.0: x is held back by its own
    # dependency, which _dependency_clashes reads from x 2.0's metadata.
    from src.resolver import service
    from src.resolver.index import PyPIIndex

    spec = {
        "x": {"1.0": {}, "2.0": {"deps": ["y<1"]}},
        "y": {"0.5": {}, "1.0": {}},
    }
    metadata_down = False
    real_dependencies = PyPIIndex.dependencies

    async def dependencies(self, *args, **kwargs):
        if metadata_down:
            raise RuntimeError("metadata host down")
        return await real_dependencies(self, *args, **kwargs)

    def no_direct_reason(*args):
        # Called once resolution is done: fail the explanation's own lookup.
        nonlocal metadata_down
        metadata_down = True
        return []

    monkeypatch.setattr(PyPIIndex, "dependencies", dependencies)
    monkeypatch.setattr(service, "held_back_reasons", no_direct_reason)
    report, _ = await resolve(spec, "x\ny==1.0", mode="validate")
    assert report.ok
    assert by_name(report)["x"].held_back_by == [
        "an older release was needed for the rest of the set to resolve"
    ]
    assert any("could not read x 2.0 metadata" in m for m in logged)


async def test_downgrade_from_a_yanked_pin_says_so(resolve):
    spec = {"lib": {"1.0": {}, "2.0": {"yanked": True}}}
    report, _ = await resolve(spec, "lib==2.0")
    lib = by_name(report)["lib"]
    assert lib.resolved_version == "1.0"
    assert lib.downgrade_reason == "was yanked"
    # Validate mode keeps the == pin, which may select a yanked release.
    kept, _ = await resolve(spec, "lib==2.0", mode="validate")
    assert by_name(kept)["lib"].resolved_version == "2.0"


async def test_downgrade_when_only_the_fitting_wheel_was_yanked(resolve, monkeypatch):
    from tests import fakepypi

    # 2.0's Windows wheel is fine, but the Linux one this target needs was yanked.
    linux_wheel = "lib-2.0-py3-none-manylinux_2_17_x86_64.whl"
    real_files = fakepypi.FakePyPI._files

    def files(self, name):
        return real_files(self, name) + [
            {
                "filename": linux_wheel,
                "url": f"{fakepypi.FILES}/{linux_wheel}",
                "yanked": True,
            }
        ]

    monkeypatch.setattr(fakepypi.FakePyPI, "_files", files)
    spec = {"lib": {"1.0": {}, "2.0": {"wheel": "py3-none-win_amd64"}}}
    report, _ = await resolve(spec, "lib==2.0")
    assert by_name(report)["lib"].downgrade_reason == "was yanked"


async def test_dependency_clash_skips_unparseable_and_inapplicable_lines(resolve):
    spec = {
        "x": {
            "1.0": {},
            "2.0": {"deps": ["not a requirement!!", 'z; python_version < "3"', "y<1"]},
        },
        "y": {"0.5": {}, "1.0": {}},
    }
    report, _ = await resolve(spec, "x\ny==1.0", mode="validate")
    assert by_name(report)["x"].held_back_by == [
        "x 2.0 requires y<1, but y 1.0 is selected"
    ]


async def test_arbitrary_equality_pin_is_not_called_a_downgrade(resolve):
    report, _ = await resolve({"lib": {"1.0": {}}}, "lib===legacy-build")
    lib = by_name(report)["lib"]
    assert lib.resolved_version == "1.0"
    assert lib.downgrade_reason is None


async def test_duplicate_lines_are_written_once(resolve):
    report, _ = await resolve({"a": {"1.0": {}}}, "a\na==1.0")
    assert report.requirements_txt.count("a==1.0") == 1


async def test_extras_node_pin_is_not_a_held_back_reason(resolve):
    spec = {
        "a": {
            "1.0": {"deps": ['c; extra == "x"']},
            "2.0": {"deps": ['c; extra == "x"']},
        },
        "b": {"1.0": {"deps": ["a<2"]}},
        "c": {"1.0": {}},
    }
    report, _ = await resolve(spec, "a[x]\nb")
    assert by_name(report)["a"].held_back_by == ["b 1.0 requires a<2"]


async def test_conflict_spanning_many_parent_versions_is_summarized(resolve):
    spec = {
        "p": {v: {"deps": ["q>=2"]} for v in ("1.0", "1.1", "1.2")},
        "q": {"1.0": {}, "2.0": {}},
    }
    report, _ = await resolve(spec, "p\nq==1.0", mode="validate")
    details = [d for c in report.conflicts for d in c.details]
    assert any("p 1.0 – 1.2 (3 versions) requires q>=2" in d for d in details)


async def test_conflict_where_every_allowed_version_clashes(resolve):
    # Found by a randomized search: d's range is open, but backtracking ruled
    # out every d candidate through its own dependencies.
    spec = {
        "a": {"1.0": {"deps": ["d"]}, "2.0": {}, "3.0": {"deps": ["e==3.0"]}},
        "b": {
            "1.0": {"deps": ["d<2", "e>=3"]},
            "2.0": {"deps": ["d<3"]},
            "3.0": {"deps": ["c==1.0", "d>=2"]},
        },
        "c": {
            "1.0": {"deps": ["b==1.0"]},
            "2.0": {"deps": ["b<3"]},
            "3.0": {"deps": ["a==3.0", "d>=2"]},
        },
        "d": {
            "1.0": {"deps": ["b>=3", "c"]},
            "2.0": {"deps": ["b<2", "e<2"]},
            "3.0": {"deps": ["e<2"]},
        },
        "e": {
            "1.0": {"deps": ["c>=3", "d>=3"]},
            "2.0": {"deps": ["b==1.0"]},
            "3.0": {"deps": ["a==1.0", "d"]},
        },
    }
    report, _ = await resolve(spec, "d\nb\na", mode="validate")
    assert any(c.message.startswith("Every version of") for c in report.conflicts)


async def test_dependency_cycle_left_by_backtracking_does_not_crash(resolve):
    # Found by a randomized search: resolvelib 1.2.1's own result builder
    # recursed forever on this (RecursionError); see service._build_result.
    spec = {
        "a": {
            "1.0": {"deps": ["d", "e<3"]},
            "2.0": {"deps": ["b==3.0"]},
            "3.0": {"deps": ["c>=2", "e==3.0"]},
        },
        "b": {
            "1.0": {},
            "2.0": {"deps": ["c<3"]},
            "3.0": {"deps": ["a<2", "c==3.0", "d==3.0"]},
        },
        "c": {"1.0": {"deps": ["b<3", "d<2"]}, "2.0": {}, "3.0": {}},
        "d": {
            "1.0": {"deps": ["c==1.0"]},
            "2.0": {"deps": ["a>=2", "c==1.0"]},
            "3.0": {"deps": ["a<3"]},
        },
        "e": {
            "1.0": {"deps": ["d<3"]},
            "2.0": {"deps": ["a<2", "b<3"]},
            "3.0": {},
        },
    }
    report, _ = await resolve(spec, "b\ne\nc", mode="validate")
    assert report.ok
    assert set(by_name(report)) >= {"b", "c", "e"}


async def test_backtracking_leftovers_are_not_reported_as_parents(resolve):
    # Found by a randomized search: while backtracking, c is pinned and its
    # requirements recorded, then c drops out of the final set. resolvelib's
    # result graph still names c as a parent of a.
    spec = {
        "a": {"1.0": {"deps": ["c<2"]}, "2.0": {}, "3.0": {}},
        "b": {
            "1.0": {"deps": ["a>=3"]},
            "2.0": {"deps": ["c>=2"]},
            "3.0": {"deps": ["c<2"]},
        },
        "c": {
            "1.0": {"deps": ["d<3"]},
            "2.0": {"deps": ["a<2"]},
            "3.0": {"deps": ["a==1.0", "b>=3", "d==1.0"]},
        },
        "d": {
            "1.0": {"deps": ["a>=2", "b>=2"]},
            "2.0": {"deps": ["b<3"]},
            "3.0": {"deps": ["b==3.0"]},
        },
    }
    report, _ = await resolve(spec, "b\nd\na==3.0", mode="validate")
    assert report.ok
    packages = by_name(report)
    installed = set(packages)
    for package in packages.values():
        assert set(package.required_by) <= installed | {"(requirements file)"}
        assert not any(
            reason.split(" ")[0] not in installed | {"your"}
            for reason in package.held_back_by
        )


async def test_no_release_matches_a_single_requirement(resolve):
    report, _ = await resolve({"lib": {"1.0": {}}}, "lib>=5", mode="validate")
    assert [c.message for c in report.conflicts] == ["No release of lib matches >=5."]


def test_find_matches_without_requirements_finds_nothing():
    # resolvelib asks this while backtracking, after a requirement was dropped
    # (108 times across 6,000 random package sets).
    from src.resolver.environment import TargetEnvironment
    from src.resolver.provider import PipLikeProvider

    provider = PipLikeProvider(object(), TargetEnvironment("3.12", "linux-x86_64"))
    assert provider.find_matches("a", {"a": iter([])}, {"a": iter([])}) == []


async def test_direct_url_dependencies_in_metadata_are_not_resolved(resolve):
    spec = {
        "app": {"1.0": {"deps": ["vendored @ https://example.com/vendored-1.0.whl"]}}
    }
    report, _ = await resolve(spec, "app")
    assert report.ok
    assert set(by_name(report)) == {"app"}  # nothing to look up on PyPI for it


def test_unparseable_current_version_counts_as_new():
    from src.resolver.models import PackageResult

    package = PackageResult(
        name="x", current_version="legacy-build", resolved_version="1.0"
    )
    assert package.change == "new"


async def test_dependency_clash_explanation_skips_requirements_the_set_satisfies(
    resolve,
):
    spec = {
        "x": {"1.0": {}, "2.0": {"deps": ["y>=0.1", "y<1"]}},
        "y": {"0.5": {}, "1.0": {}},
    }
    report, _ = await resolve(spec, "x\ny==1.0", mode="validate")
    # y>=0.1 holds for the selected y 1.0, so only y<1 is named.
    assert by_name(report)["x"].held_back_by == [
        "x 2.0 requires y<1, but y 1.0 is selected"
    ]
