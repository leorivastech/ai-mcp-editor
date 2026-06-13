"""Versioned compiler dispatch.

A preset carries `compiler_version`; saved presets keep compiling with the
exact compiler they were created with, so the same preset always produces
the same prompt — even after the project evolves.
"""

from __future__ import annotations

from typing import Any, Callable

from core.compiler.v1 import compile_v1
from core.compiler.v2 import compile_v2
from core.schema import Preset

COMPILERS: dict[int, Callable[[Preset], str]] = {
    1: compile_v1,
    2: compile_v2,
}

LATEST_COMPILER_VERSION = max(COMPILERS)


def compile_preset(preset: Preset | dict[str, Any]) -> str:
    """Validate (if needed) and compile a preset into its prompt."""
    if not isinstance(preset, Preset):
        preset = Preset.model_validate(preset)
    compiler = COMPILERS.get(preset.compiler_version)
    if compiler is None:
        raise ValueError(
            f"Unknown compiler_version {preset.compiler_version}; "
            f"this build supports: {sorted(COMPILERS)}"
        )
    return compiler(preset)
