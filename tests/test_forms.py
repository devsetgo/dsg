# -*- coding: utf-8 -*-
from src.forms import form_defaults, render_check_form, validate_check_form

VALID = {
    "requirements": "requests==2.31.0",
    "python_version": "3.12",
    "platform": "linux-x86_64",
    "mode": "upgrade",
}


def test_valid_submission():
    result = validate_check_form(VALID)
    assert result.is_valid
    assert result.instance.python_version == "3.12"


def test_defaults_fill_missing_optional_fields():
    result = validate_check_form({"requirements": "requests"})
    assert result.is_valid
    assert result.instance.mode == "upgrade"
    assert result.instance.platform == "linux-x86_64"


def test_rejects_bad_choices_and_empty_text():
    result = validate_check_form(
        {**VALID, "requirements": "", "python_version": "2.7", "platform": "amiga"}
    )
    assert not result.is_valid
    assert set(result.errors) >= {"requirements", "python_version", "platform"}


def test_comment_only_text_is_rejected():
    result = validate_check_form({**VALID, "requirements": "# nothing here\n\n"})
    assert not result.is_valid
    assert "at least one requirement" in str(result.errors["requirements"])


def test_line_limit():
    text = "\n".join(f"pkg{i}" for i in range(101))
    result = validate_check_form({**VALID, "requirements": text})
    assert not result.is_valid
    assert "101 requirement lines" in str(result.errors["requirements"])


async def test_render_preselects_defaults_and_wires_htmx():
    html = await render_check_form()
    assert 'hx-post="/check"' in html and 'hx-target="#check-form"' in html
    assert '<option value="3.14" selected>' in html
    assert 'value="upgrade" checked' in html
    assert 'name="requirements"' in html


async def test_render_with_errors_keeps_submitted_values():
    result = validate_check_form({**VALID, "requirements": "requests\n" + "x\n" * 101})
    html = await result.render_with_errors_async()
    assert "invalid-feedback" in html
    assert "requests" in html


def test_form_defaults():
    assert form_defaults() == {
        "python_version": "3.14",
        "platform": "linux-x86_64",
        "mode": "upgrade",
    }


def test_every_offered_python_version_is_accepted():
    from typing import get_args

    from src.forms import PythonVersion

    assert get_args(PythonVersion)[0] == "3.8" and get_args(PythonVersion)[-1] == "3.15"
    for version in get_args(PythonVersion):
        assert validate_check_form({**VALID, "python_version": version}).is_valid
