"""Golden snapshot tests — the public guarantee of determinism.

Each golden/*.json must compile to exactly its golden/*.txt, byte for byte.
The JS compiler port (widget/src/compiler.js) runs against the same files
in widget/test/golden.test.js, making these fixtures the cross-language
contract. Regenerate after an intentional change: python -m core.tests.regen_goldens
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.compiler import compile_preset
from core.schema import Preset

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_CASES = sorted(GOLDEN_DIR.glob("*.json"))


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=lambda p: p.stem)
def test_golden(case: Path) -> None:
    preset = json.loads(case.read_text())
    expected = case.with_suffix(".txt").read_text()
    assert compile_preset(preset) == expected


def test_compile_is_deterministic() -> None:
    preset = json.loads((GOLDEN_DIR / "full.json").read_text())
    assert compile_preset(preset) == compile_preset(preset)


def test_unknown_compiler_version_rejected() -> None:
    preset = json.loads((GOLDEN_DIR / "minimal.json").read_text())
    preset["compiler_version"] = 99
    with pytest.raises(ValueError, match="compiler_version"):
        compile_preset(preset)


@pytest.mark.parametrize(
    "mutation",
    [
        {"layout": "not_a_layout"},
        {"size": {"width": 10, "height": 1024}},
        {"elements": [{"kind": "text", "content": "x", "zone": "nowhere"}]},
        {"style": {"palette": ["red"]}},
        {"unknown_field": True},
    ],
    ids=["bad-layout", "tiny-width", "bad-zone", "non-hex-color", "extra-field"],
)
def test_invalid_presets_rejected(mutation: dict) -> None:
    preset = json.loads((GOLDEN_DIR / "minimal.json").read_text())
    preset.update(mutation)
    with pytest.raises(ValidationError):
        Preset.model_validate(preset)


def test_empty_element_content_skipped() -> None:
    preset = json.loads((GOLDEN_DIR / "minimal.json").read_text())
    preset["elements"] = [{"kind": "text", "content": "   ", "zone": "center"}]
    assert "Element placement" not in compile_preset(preset)


def test_v2_is_superset_of_v1_for_text_only() -> None:
    """A text/subject-only preset compiles byte-identically under v1 and v2 —
    so v2 is a safe superset and existing presets never drift."""
    preset = json.loads((GOLDEN_DIR / "full.json").read_text())
    v1_out = compile_preset({**preset, "compiler_version": 1})
    v2_out = compile_preset({**preset, "compiler_version": 2})
    assert v1_out == v2_out


def test_v2_input_images_section() -> None:
    preset = json.loads((GOLDEN_DIR / "product_background.json").read_text())
    out = compile_preset(preset)
    assert "Input images (the user will attach these, in order):" in out
    assert "Attached image 1 = PRODUCT" in out
    assert "Attached image 2 = BACKGROUND" in out
    # Image slots must NOT leak into the text "Element placement" lines.
    assert "(subject)" not in out


def test_product_accepts_all_over_and_background_drops_zone() -> None:
    p = Preset.model_validate(
        {
            "size": {"width": 1024, "height": 1024},
            "layout": "full_bleed",
            "elements": [
                {"kind": "product", "content": "x", "zone": "all-over"},
                {"kind": "background", "content": "y", "zone": "center"},
            ],
            "compiler_version": 2,
        }
    )
    assert p.elements[0].zone == "all-over"
    assert p.elements[1].zone is None  # background always covers the full canvas


def test_product_rejects_bad_placement() -> None:
    with pytest.raises(ValidationError):
        Preset.model_validate(
            {
                "size": {"width": 1024, "height": 1024},
                "layout": "full_bleed",
                "elements": [{"kind": "product", "content": "x", "zone": "nowhere"}],
                "compiler_version": 2,
            }
        )
