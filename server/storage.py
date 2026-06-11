"""Preset storage — a single SQLite file. Single-user by design.

This project is self-hosted (one instance per user/team), so there is no
auth layer and no multi-tenancy: the whole "database" is one file whose
path comes from PRESETS_DB (default ./data/presets.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS presets (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    preset_json   TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    last_used_at  TEXT NOT NULL
);
"""

_SORT_COLUMNS = {
    "last_used": "last_used_at DESC",
    "created": "created_at DESC",
    "updated": "updated_at DESC",
    "name": "name COLLATE NOCASE ASC",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PresetStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path or os.environ.get("PRESETS_DB", "data/presets.db"))
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row, *, with_preset: bool = True) -> dict[str, Any]:
        record: dict[str, Any] = {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_used_at": row["last_used_at"],
        }
        preset = json.loads(row["preset_json"])
        if with_preset:
            record["preset"] = preset
        else:
            record["layout"] = preset.get("layout")
            record["size"] = preset.get("size")
        return record

    def _find_row(self, name_or_id: str) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM presets WHERE id = ? OR name = ? COLLATE NOCASE",
            (name_or_id, name_or_id),
        )
        return cur.fetchone()

    # -- operations ---------------------------------------------------------

    def save(self, name: str, preset: dict[str, Any]) -> dict[str, Any]:
        """Insert or update (by name, case-insensitive). Returns the record."""
        name = name.strip()
        if not name:
            raise ValueError("preset name must not be empty")
        preset = {**preset, "name": name}
        now = _now()
        with self._lock:
            existing = self._conn.execute(
                "SELECT id FROM presets WHERE name = ? COLLATE NOCASE", (name,)
            ).fetchone()
            if existing:
                self._conn.execute(
                    "UPDATE presets SET name = ?, preset_json = ?, updated_at = ?, "
                    "last_used_at = ? WHERE id = ?",
                    (name, json.dumps(preset), now, now, existing["id"]),
                )
                preset_id = existing["id"]
            else:
                preset_id = uuid.uuid4().hex[:12]
                self._conn.execute(
                    "INSERT INTO presets VALUES (?, ?, ?, ?, ?, ?)",
                    (preset_id, name, json.dumps(preset), now, now, now),
                )
            self._conn.commit()
            row = self._find_row(preset_id)
        assert row is not None
        return self._row_to_record(row)

    def get(self, name_or_id: str, *, touch: bool = True) -> Optional[dict[str, Any]]:
        """Fetch one preset; by default marks it as used (last_used_at)."""
        with self._lock:
            row = self._find_row(name_or_id.strip())
            if row is None:
                return None
            if touch:
                self._conn.execute(
                    "UPDATE presets SET last_used_at = ? WHERE id = ?",
                    (_now(), row["id"]),
                )
                self._conn.commit()
                row = self._find_row(row["id"])
                assert row is not None
        return self._row_to_record(row)

    def list(
        self,
        query: Optional[str] = None,
        sort: str = "last_used",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        order = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["last_used"])
        sql = "SELECT * FROM presets"
        args: list[Any] = []
        if query:
            sql += " WHERE name LIKE ? COLLATE NOCASE"
            args.append(f"%{query.strip()}%")
        sql += f" ORDER BY {order} LIMIT ?"
        args.append(max(1, min(int(limit), 100)))
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [self._row_to_record(r, with_preset=False) for r in rows]

    def delete(self, name_or_id: str) -> Optional[str]:
        """Delete one preset; returns its name, or None if not found."""
        with self._lock:
            row = self._find_row(name_or_id.strip())
            if row is None:
                return None
            self._conn.execute("DELETE FROM presets WHERE id = ?", (row["id"],))
            self._conn.commit()
        return row["name"]
