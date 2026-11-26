"""Read-only access to the opencode SQLite database behind a schema guard."""

from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import quote

log = logging.getLogger(__name__)

KNOWN_OPENCODE_MIGRATION = "20261120004954_machine-key"

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "migration": {"id"},
    "session_v2": {
        "id", "parent_id", "directory", "project_id", "version",
        "time_created", "time_updated", "time_busy", "time_idle", "idle_outcome",
    },
    "session_message": {"session_id", "type", "seq", "time_updated", "data"},
    "session_part": {
        "session_id", "message_id", "ordinal", "type", "call_id",
        "time_updated", "data",
    },
}

_warned: set[str] = set()


def _reset_warnings() -> None:
    _warned.clear()


def _warn_once(key: str, msg: str, *args: object) -> None:
    if key in _warned:
        return
    _warned.add(key)
    log.warning(msg, *args)


def resolve_db_path(flag: Optional[str]) -> Path:
    """Flag, then $OPENCODE_DB, then $XDG_DATA_HOME, then ~/.local/share."""
    if flag:
        return Path(flag).expanduser()
    env = os.environ.get("OPENCODE_DB")
    if env:
        return Path(env).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "opencode" / "opencode.db"
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def open_readonly(path: Path) -> Optional[Tuple[sqlite3.Connection, str]]:
    """Open read-only and validate the schema. Returns (conn, migration_id) or None."""
    path = Path(path)
    if not path.is_file():
        log.debug("opencode database not found: %s", path)
        return None
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True, timeout=5)
        missing = []
        for table, cols in REQUIRED_COLUMNS.items():
            have = {r[1] for r in conn.execute(f"pragma table_info({table})")}
            missing.extend(f"{table}.{c}" for c in sorted(cols - have))
        if missing:
            _warn_once("columns", "opencode schema missing %s; skipping source",
                       ", ".join(missing))
            conn.close()
            return None
        row = conn.execute("SELECT id FROM migration ORDER BY id DESC LIMIT 1").fetchone()
        mig = (row[0] or "") if row else ""
        if not mig or mig > KNOWN_OPENCODE_MIGRATION:
            _warn_once("migration", "opencode migration %r is unknown (known %s); continuing",
                       mig, KNOWN_OPENCODE_MIGRATION)
        return conn, mig
    except sqlite3.Error as exc:
        _warn_once("sqlite_error", "opencode database error: %s; skipping source", exc)
        if conn is not None:
            conn.close()
        return None
