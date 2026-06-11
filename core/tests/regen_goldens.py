"""Regenerate golden .txt files from their .json presets.

Run only after an INTENTIONAL compiler change, then review the diff:
    python -m core.tests.regen_goldens
"""

from __future__ import annotations

import json
from pathlib import Path

from core.compiler import compile_preset

GOLDEN_DIR = Path(__file__).parent / "golden"


def main() -> None:
    for case in sorted(GOLDEN_DIR.glob("*.json")):
        prompt = compile_preset(json.loads(case.read_text()))
        case.with_suffix(".txt").write_text(prompt)
        print(f"wrote {case.with_suffix('.txt').name}")


if __name__ == "__main__":
    main()
