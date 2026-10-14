"""Append-only audit trail at output/audit_trail.json.

The file is one JSON array that only ever grows: each write loads what is
there, adds the new entry, and swaps the file in atomically so a crash never
leaves half-written JSON. If the existing file cannot be parsed it is moved
aside (never deleted) and a fresh array is started.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import AUDIT_PATH, AUDIT_TEXT_LIMIT
from backend.models import AuditEntry

_lock = threading.Lock()


def clip(value: Any, limit: int = AUDIT_TEXT_LIMIT) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"… (+{len(text) - limit} chars)"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _load(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    path.rename(path.with_name(f"{path.stem}.unreadable-{datetime.now():%Y%m%d-%H%M%S}{path.suffix}"))
    return []


def read_all(path: Path = AUDIT_PATH) -> list:
    """Every entry so far, oldest first. Read-only: never moves or rewrites the file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def append(entry: AuditEntry, path: Path = AUDIT_PATH) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = _load(path)
        entries.append(entry.model_dump(mode="json", exclude_none=True))
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        os.replace(tmp, path)
