from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.storage import PresetStore

GOLDEN_DIR = Path(__file__).parents[2] / "core" / "tests" / "golden"


@pytest.fixture()
def store(tmp_path: Path) -> PresetStore:
    return PresetStore(tmp_path / "presets.db")


@pytest.fixture()
def sample_preset() -> dict:
    return json.loads((GOLDEN_DIR / "full.json").read_text())


def test_save_and_get(store: PresetStore, sample_preset: dict) -> None:
    saved = store.save("promo dark", sample_preset)
    assert saved["name"] == "promo dark"

    fetched = store.get("promo dark")
    assert fetched is not None
    assert fetched["preset"]["layout"] == "diagonal"
    # case-insensitive and by id
    assert store.get("PROMO DARK") is not None
    assert store.get(saved["id"]) is not None


def test_save_upserts_by_name(store: PresetStore, sample_preset: dict) -> None:
    first = store.save("promo", sample_preset)
    changed = {**sample_preset, "layout": "overlay"}
    second = store.save("Promo", changed)
    assert second["id"] == first["id"]
    assert store.get("promo")["preset"]["layout"] == "overlay"
    assert len(store.list()) == 1


def test_list_query_and_sort(store: PresetStore, sample_preset: dict) -> None:
    store.save("promo dark", sample_preset)
    store.save("promo light", sample_preset)
    store.save("menu grid", sample_preset)

    assert len(store.list()) == 3
    assert len(store.list(query="promo")) == 2
    names = [r["name"] for r in store.list(sort="name")]
    assert names == ["menu grid", "promo dark", "promo light"]
    # list records are summaries, not full presets
    assert "preset" not in store.list()[0]
    assert store.list()[0]["layout"] == "diagonal"


def test_get_touches_last_used(store: PresetStore, sample_preset: dict) -> None:
    store.save("a", sample_preset)
    store.save("b", sample_preset)
    store.get("a")  # most recently used now
    assert store.list(sort="last_used")[0]["name"] == "a"


def test_delete(store: PresetStore, sample_preset: dict) -> None:
    store.save("bye", sample_preset)
    assert store.delete("BYE") == "bye"
    assert store.get("bye") is None
    assert store.delete("missing") is None


def test_empty_name_rejected(store: PresetStore, sample_preset: dict) -> None:
    with pytest.raises(ValueError):
        store.save("   ", sample_preset)
