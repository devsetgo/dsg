# -*- coding: utf-8 -*-
"""
Forms, built with pydantic-schemaforms.

Notes for anyone touching these (found while dogfooding 26.4.1):
- Pass the model's defaults as `form_data` on the first render - the library
  does not pre-select a select/radio default or check a default-True box.
- htmx attributes must be passed with hyphens (`**{"hx-post": ...}`); an
  `hx_post=` keyword is emitted literally as `hx_post`.
- An unchecked checkbox is simply absent from the POST, so a checkbox field
  whose default is True could never be switched off. Give any boolean field
  added here a False default.
"""

from typing import Literal

from pydantic import field_validator
from pydantic_schemaforms import Field, FormModel, render_form_html_async

from .resolver.environment import DEFAULT_PLATFORM, PLATFORMS
from .settings import settings

# The single list of target versions offered (and accepted by /api/check).
PythonVersion = Literal["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15"]
PlatformKey = Literal["linux-x86_64", "linux-aarch64", "macos-arm64", "windows-amd64"]

FORM_TARGET_ID = "check-form"
SUBMIT_URL = "/check"


class PackageCheckForm(FormModel):
    requirements: str = Field(
        ...,
        title="requirements.txt",
        min_length=1,
        max_length=20_000,
        ui_element="textarea",
        ui_placeholder="requests==2.31.0\nnumpy==1.26.2\nfastapi[all]>=0.100",
        ui_help_text=f"Up to {settings.max_requirement_lines} requirement lines. Comments, -r and -e lines are reported, not resolved.",
        ui_options={"rows": 16},
        ui_autofocus=True,
    )
    python_version: PythonVersion = Field(
        settings.default_python_version,
        title="Target Python",
        ui_element="select",
        ui_help_text="Requires-Python and environment markers are evaluated for this version.",
    )
    platform: PlatformKey = Field(
        DEFAULT_PLATFORM,
        title="Platform",
        ui_element="select",
        ui_options={
            "choices": [
                {"value": key, "label": spec["label"]}
                for key, spec in PLATFORMS.items()
            ]
        },
        ui_help_text="Decides which wheels count as installable.",
    )
    mode: Literal["upgrade", "validate"] = Field(
        "upgrade",
        title="Mode",
        ui_element="radio",
        ui_options={
            "choices": [
                {
                    "value": "upgrade",
                    "label": "Upgrade - newest versions that work together",
                },
                {
                    "value": "validate",
                    "label": "Validate - keep my pins, report conflicts",
                },
            ]
        },
    )

    @field_validator("requirements")
    @classmethod
    def limit_lines(cls, value: str) -> str:
        lines = [
            line
            for line in value.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            raise ValueError("Paste at least one requirement.")
        if len(lines) > settings.max_requirement_lines:
            raise ValueError(
                f"{len(lines)} requirement lines; the limit is {settings.max_requirement_lines}."
            )
        return value


def form_defaults() -> dict:
    return {
        name: field.default
        for name, field in PackageCheckForm.model_fields.items()
        if field.default is not None and not field.is_required()
    }


def _form_attrs() -> dict:
    return {
        "hx-post": SUBMIT_URL,
        "hx-target": f"#{FORM_TARGET_ID}",
        "hx-swap": "innerHTML",
        "hx-indicator": "#check-spinner",
        "hx-disabled-elt": "find button[type=submit]",
    }


async def render_check_form(form_data: dict | None = None) -> str:
    return await render_form_html_async(
        PackageCheckForm,
        form_data=form_data or form_defaults(),
        framework="bootstrap",
        layout="vertical",
        submit_url=SUBMIT_URL,
        **_form_attrs(),
    )


def validate_check_form(data: dict):
    return PackageCheckForm.validate(
        data, submit_url=SUBMIT_URL, framework="bootstrap", **_form_attrs()
    )
