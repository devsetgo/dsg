# -*- coding: utf-8 -*-
from src.resolver.parse import parse_requirements


def test_parses_names_extras_specifiers_and_markers():
    parsed = parse_requirements(
        'Django>=4,<5\nfastapi[all,standard]==0.100.0\npywin32; sys_platform == "win32"\n'
    )
    names = [r.name for r in parsed.requirements]
    assert names == ["django", "fastapi", "pywin32"]
    fastapi = parsed.requirements[1]
    assert fastapi.extras == {"all", "standard"}
    assert fastapi.pinned_version == "0.100.0"
    assert parsed.requirements[0].pinned_version is None
    assert str(parsed.requirements[2].requirement.marker) == 'sys_platform == "win32"'
    assert parsed.issues == []


def test_names_are_canonicalized_but_display_name_kept():
    parsed = parse_requirements("PyYAML==6.0.1\nzope.interface\n")
    assert [r.name for r in parsed.requirements] == ["pyyaml", "zope-interface"]
    assert parsed.requirements[0].display_name == "PyYAML"


def test_comments_blank_lines_and_inline_comments():
    parsed = parse_requirements(
        "# header\n\nrequests==2.31.0  # pinned for reasons\n   \n"
    )
    assert [r.name for r in parsed.requirements] == ["requests"]
    assert parsed.requirements[0].pinned_version == "2.31.0"


def test_hashes_and_line_continuations():
    text = "requests==2.31.0 \\\n    --hash=sha256:aaa \\\n    --hash=sha256:bbb\nidna==3.6 --hash=sha256:ccc\n"
    parsed = parse_requirements(text)
    assert [(r.name, r.pinned_version) for r in parsed.requirements] == [
        ("requests", "2.31.0"),
        ("idna", "3.6"),
    ]
    assert parsed.requirements[0].line_no == 1
    assert parsed.issues == []


def test_unsupported_lines_are_reported_not_dropped():
    text = "-r base.txt\n-c constraints.txt\n-e git+https://github.com/x/y.git#egg=y\n--index-url https://example.com\n./local/pkg\nfoo @ https://example.com/foo.whl\nnot a requirement!!\nrequests\n"
    parsed = parse_requirements(text)
    assert [r.name for r in parsed.requirements] == ["requests"]
    reasons = {issue.line_no: issue.reason for issue in parsed.issues}
    assert set(reasons) == {3, 4, 5, 6, 7}
    # Includes are passed through quietly, not reported.
    assert parsed.passthrough == [(1, "-r base.txt"), (2, "-c constraints.txt")]
    assert "Editable" in reasons[3]
    assert "ignored" in reasons[4]
    assert "Local paths" in reasons[5]
    assert "Direct URL" in reasons[6]
    assert "Not a valid requirement" in reasons[7]


def test_wildcard_pin_is_not_an_exact_version():
    parsed = parse_requirements("django==4.2.*\n")
    assert parsed.requirements[0].pinned_version is None


def test_a_trailing_continuation_backslash_keeps_the_last_line():
    parsed = parse_requirements("idna==3.4 \\")
    assert [r.name for r in parsed.requirements] == ["idna"]
