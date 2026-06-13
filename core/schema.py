"""Pydantic schema for Preset v1 — the single source of truth for validation."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.constants import ELEMENT_KINDS, LAYOUTS, PRODUCT_PLACEMENTS, ZONES

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

    kind: Literal["text", "subject", "product", "background"]
    # text/subject: the verbatim text or subject description (required).
    # product/background: an optional hint about the attached photo.
    content: Optional[str] = Field(default=None, max_length=300)
    # text/subject/product: a placement zone (product also allows "all-over").
    # background: ignored — it always covers the whole canvas.
    zone: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def _check_per_kind(self) -> "Element":
        if self.kind in ("text", "subject"):
            if not self.content:
                raise ValueError(f"{self.kind} element requires content")
            if self.zone not in ZONES:
                raise ValueError(
                    f"{self.kind} zone must be one of {ZONES}, got {self.zone!r}"
                )
        elif self.kind == "product":
            placement = self.zone or "center"
            if placement not in PRODUCT_PLACEMENTS:
                raise ValueError(
                    f"product placement must be one of {PRODUCT_PLACEMENTS}, "
                    f"got {self.zone!r}"
                )
            self.zone = placement
        elif self.kind == "background":
            # A background always covers the full canvas — drop any zone.
            self.zone = None
        return self


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
