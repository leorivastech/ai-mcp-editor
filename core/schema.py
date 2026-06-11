"""Pydantic schema for Preset v1 — the single source of truth for validation."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import ELEMENT_KINDS, LAYOUTS, ZONES

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

LayoutKey = Literal[
    "full_bleed",
    "split_v",
    "split_h",
    "diagonal",
    "grid_2x2",
    "three_col",
    "hero_cta",
    "frame",
    "overlay",
]
ZoneKey = Literal[
    "top-left",
    "top-center",
    "top-right",
    "middle-left",
    "center",
    "middle-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]


class Size(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = Field(ge=64, le=8192)
    height: int = Field(ge=64, le=8192)
    aspect_label: Optional[str] = Field(default=None, max_length=16)


class Element(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["text", "subject"]
    content: str = Field(min_length=1, max_length=300)
    zone: ZoneKey


class Style(BaseModel):
    model_config = ConfigDict(extra="forbid")

    art_style: Optional[str] = Field(default=None, max_length=80)
    palette: list[str] = Field(default_factory=list, max_length=8)
    typography: Optional[str] = Field(default=None, max_length=120)
    lighting: Optional[str] = Field(default=None, max_length=120)

    @field_validator("palette")
    @classmethod
    def _hex_colors(cls, v: list[str]) -> list[str]:
        for color in v:
            if not HEX_COLOR_RE.match(color):
                raise ValueError(
                    f"palette colors must be hex like #1a2b3c, got: {color!r}"
                )
        return [c.lower() for c in v]


class Preset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    name: Optional[str] = Field(default=None, max_length=80)
    size: Size
    layout: LayoutKey
    elements: list[Element] = Field(default_factory=list, max_length=12)
    style: Style = Field(default_factory=Style)
    restrictions: list[str] = Field(default_factory=list, max_length=20)
    free_text: Optional[str] = Field(default=None, max_length=1500)
    compiler_version: int = Field(default=1, ge=1)


# Sanity guards: Literal types above must stay in sync with constants.py
assert set(LayoutKey.__args__) == set(LAYOUTS)  # type: ignore[attr-defined]
assert set(ZoneKey.__args__) == set(ZONES)  # type: ignore[attr-defined]
assert set(Element.model_fields["kind"].annotation.__args__) == set(ELEMENT_KINDS)  # type: ignore[union-attr]
