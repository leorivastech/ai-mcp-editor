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
