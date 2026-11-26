"""Extraction functions for opencode sessions (pure functions over a sqlite3 connection)."""

import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from agentsignals.miner import (
    EXIT_CODE_PATTERN,
    MIN_PROMPT_LENGTH,
    SETTLE_DEBOUNCE_SECONDS,
    ToolErrorEvent,
    has_nonzero_exit_code,
    is_git_discernable,
)
from agentsignals.sources import Extraction, SessionRef
from agentsignals.sources.opencode_schema import open_readonly

log = logging.getLogger(__name__)

OPENCODE_QUIET_SECONDS = 600
MAX_FAMILY_DEPTH = 64
MAX_TOUCHED_FILES = 500
_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)


def _d(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _loads(raw: Any) -> Optional[Any]:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def slug_for_directory(directory: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", directory)


def load_messages(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, type, seq, data FROM session_message WHERE session_id=? ORDER BY seq",
        (session_id,),
    ).fetchall()
    out = []
    for mid, mtype, seq, raw in rows:
        data = _loads(raw)
        if data is None:
            continue
        out.append({"id": mid, "type": mtype, "seq": seq, "data": data})
    return out


def load_parts(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT message_id, ordinal, type, call_id, data FROM session_part"
        " WHERE session_id=? ORDER BY message_id, ordinal",
        (session_id,),
    ).fetchall()
    out = []
    for mid, ordinal, ptype, call_id, raw in rows:
        data = _loads(raw)
        if data is None:
            continue
        out.append(
            {"message_id": mid, "ordinal": ordinal, "type": ptype, "call_id": call_id, "data": data}
        )
    return out


def assistant_content(message_data: Any, part_rows: list[dict]) -> list:
    items: list = []
    for row in sorted(part_rows, key=lambda r: r.get("ordinal") or 0):
        item = dict(_d(row.get("data")))
        if "type" not in item and row.get("type") is not None:
            item["type"] = row["type"]
        if "id" not in item and row.get("call_id") is not None:
            item["id"] = row["call_id"]
        items.append(item)
    inline = _d(message_data).get("content")
    if isinstance(inline, list):
        items.extend(inline)
    return items


def user_prompts(messages: list[dict]) -> list[str]:
    prompts = []
    for m in messages:
        if m.get("type") != "user":
            continue
        text = _d(m.get("data")).get("text")
        if not isinstance(text, str):
            continue
        text = text.strip()
        if len(text) >= MIN_PROMPT_LENGTH:
            prompts.append(text)
    return prompts


def _iso(ms: Any) -> Optional[str]:
    if isinstance(ms, bool) or not isinstance(ms, (int, float)) or not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def _command_or_input(inp: dict) -> str:
    if inp.get("command"):
        val = str(inp["command"])
    elif inp.get("filePath"):
        val = str(inp["filePath"])
    elif inp.get("patchText"):
        val = str(inp["patchText"]).split("\n", 1)[0]
    else:
        val = json.dumps(inp, sort_keys=True, default=str)
    return val[:500]


def _text_of(state: dict) -> str:
    content = state.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        c["text"] for c in content
        if isinstance(c, dict) and c.get("type") == "text" and isinstance(c.get("text"), str)
    )


def tool_error_events(content: list) -> list[ToolErrorEvent]:
    events = []
    for item in content:
        item = _d(item)
        if item.get("type") != "tool":
            continue
        state = _d(item.get("state"))
        name = item.get("name")
        meta = _d(state.get("metadata"))
        status = state.get("status")
        exit_code: Optional[int] = None
        error_output: Optional[str] = None
        if status == "error":
            err = _d(state.get("error"))
            error_output = f"{err.get('type', 'unknown')} error: {err.get('message', '')}"
        elif name == "shell" and status == "completed":
            text = _text_of(state)
            ex = meta.get("exit")
            if isinstance(ex, int) and not isinstance(ex, bool):
                if ex != 0 or meta.get("signal") or meta.get("timeout"):
                    exit_code = ex
                    error_output = text
                    if not any(int(c) == ex for c in EXIT_CODE_PATTERN.findall(text)):
                        error_output += f"\nExit code: {ex}"
            elif meta.get("signal") or meta.get("timeout"):
                error_output = text
            elif "exit" not in meta and has_nonzero_exit_code(text):
                error_output = text
                exit_code = next(int(c) for c in EXIT_CODE_PATTERN.findall(text) if int(c) != 0)
        if error_output is None:
            continue
        cmd = _command_or_input(_d(state.get("input")))
        if is_git_discernable(name, cmd, error_output):
            continue
        t = _d(item.get("time"))
        events.append(
            ToolErrorEvent(
                tool_use_id=item.get("id"),
                tool_name=name,
                command_or_input=cmd,
                error_output=error_output,
                exit_code=exit_code,
                timestamp=_iso(t.get("completed")) or _iso(t.get("created")),
            )
        )
    return events


def failed_turn_events(messages: list[dict]) -> list[ToolErrorEvent]:
    events = []
    for m in messages:
        data = _d(m.get("data"))
        if m.get("type") == "idle" and data.get("outcome") == "failed":
            msg = _d(data.get("error")).get("message", "")
            events.append(
                ToolErrorEvent(
                    tool_use_id=None,
                    tool_name="session",
                    command_or_input=None,
                    error_output=f"turn error: {msg}",
                )
            )
    return events


def touched_files(messages: list[dict], contents: list[list], directory: str) -> list[str]:
    paths: set[str] = set()
    for m in messages:
        if m.get("type") != "assistant":
            continue
        files = _d(_d(m.get("data")).get("snapshot")).get("files")
        if isinstance(files, list):
            paths.update(f for f in files if isinstance(f, str) and f)
    for content in contents:
        for item in content:
            item = _d(item)
            if item.get("type") != "tool":
                continue
            inp = _d(_d(item.get("state")).get("input"))
            name = item.get("name")
            if name in ("edit", "write") and isinstance(inp.get("filePath"), str) and inp["filePath"]:
                paths.add(inp["filePath"])
            elif name == "patch" and isinstance(inp.get("patchText"), str):
                paths.update(p.strip() for p in _PATCH_FILE_RE.findall(inp["patchText"]))
    norm = {os.path.normpath(os.path.join(directory, p)) for p in paths if p}
    return sorted(norm)[:MAX_TOUCHED_FILES]


def extract_session(
    conn: sqlite3.Connection, session_id: str, directory: str
) -> tuple[list[str], list[ToolErrorEvent], list[str]]:
    messages = load_messages(conn, session_id)
    parts_by_msg: dict[str, list[dict]] = {}
    for row in load_parts(conn, session_id):
        parts_by_msg.setdefault(row["message_id"], []).append(row)
    prompts = user_prompts(messages)
    errors: list[ToolErrorEvent] = []
    contents: list[list] = []
    for m in messages:
        if m["type"] == "assistant":
            content = assistant_content(m["data"], parts_by_msg.get(m["id"], []))
            contents.append(content)
            errors.extend(tool_error_events(content))
        elif m["type"] == "idle":
            errors.extend(failed_turn_events([m]))
    return prompts, errors, touched_files(messages, contents, directory)


_MARKER_SQL = """
SELECT s.id, s.parent_id, s.directory, s.time_created, s.time_busy, s.time_idle,
       max(coalesce(s.time_updated,0), coalesce(s.time_idle,0),
           coalesce((SELECT max(time_updated) FROM session_message WHERE session_id=s.id),0),
           coalesce((SELECT max(time_updated) FROM session_part WHERE session_id=s.id),0))
FROM session_v2 s
"""


def _now() -> float:
    return time.time()


def _find_root(rows: dict[str, tuple], sid: str) -> str:
    seen = {sid}
    cur = sid
    for _ in range(MAX_FAMILY_DEPTH):
        parent = rows[cur][1]
        if parent is None or parent not in rows:
            return cur
        if parent in seen:
            log.warning("opencode session parent loop at %s", cur)
            return cur
        seen.add(parent)
        cur = parent
    log.warning("opencode session nesting deeper than %d at %s", MAX_FAMILY_DEPTH, cur)
    return cur


class OpencodeSource:
    name = "opencode"

    def __init__(self, db_path: Path, skip_if_unchanged: bool = False) -> None:
        self.db_path = Path(db_path)
        self.skip_if_unchanged = skip_if_unchanged
        # root id -> [{"id", "directory", "time_created"}, ...], root first
        self._families: dict[str, list[dict]] = {}
        self._last_mtimes: Optional[tuple[float, float]] = None
        self._had_unsettled = False

    def _db_mtimes(self) -> tuple[float, float]:
        out = []
        for p in (self.db_path, Path(str(self.db_path) + "-wal")):
            try:
                out.append(p.stat().st_mtime)
            except OSError:
                out.append(0.0)
        return out[0], out[1]

    def iter_sessions(self, target_slug: Optional[str]) -> Iterator[SessionRef]:
        mtimes = self._db_mtimes()
        if (
            self.skip_if_unchanged
            and self._last_mtimes == mtimes
            and not self._had_unsettled
        ):
            return
        self._families = {}
        had_unsettled = False
        opened = open_readonly(self.db_path)
        if opened is None:
            return
        conn, _ = opened
        try:
            rows = {r[0]: r for r in conn.execute(_MARKER_SQL).fetchall()}
        finally:
            conn.close()
        groups: dict[str, list[tuple]] = {}
        for sid in rows:
            groups.setdefault(_find_root(rows, sid), []).append(rows[sid])
        now = _now()
        for root_id, members in groups.items():
            root = rows[root_id]
            slug = slug_for_directory(root[2] or "")
            if target_slug and slug != target_slug:
                continue
            changed_at = max(m[6] for m in members) / 1000
            age = now - changed_at
            idle_all = all(
                m[5] is not None and m[5] >= (m[4] or 0) for m in members
            )
            settled = (idle_all and age >= SETTLE_DEBOUNCE_SECONDS) or age >= OPENCODE_QUIET_SECONDS
            children = sorted((m for m in members if m[0] != root_id), key=lambda m: m[3] or 0)
            ordered = [root] + children
            if not settled:
                had_unsettled = True
            self._families[root_id] = [
                {"id": m[0], "directory": m[2], "time_created": m[3]} for m in ordered
            ]
            yield SessionRef(
                source=self.name,
                slug=slug,
                session_id=root_id,
                decoded_path=root[2],
                changed_at=changed_at,
                settled=settled,
            )
        # Committed only after every ref was consumed; an aborted pass stays stale.
        self._last_mtimes = mtimes
        self._had_unsettled = had_unsettled

    def extract(self, ref: SessionRef) -> Extraction:
        opened = open_readonly(self.db_path)
        if opened is None:
            raise RuntimeError(f"opencode database unavailable: {self.db_path}")
        conn, migration = opened
        try:
            members = self._families.get(ref.session_id) or [
                {"id": ref.session_id, "directory": ref.decoded_path}
            ]
            prompts: list[str] = []
            errors: list[ToolErrorEvent] = []
            files: set[str] = set()
            for m in members:
                p, e, f = extract_session(conn, m["id"], m["directory"] or "")
                prompts.extend(p)
                errors.extend(e)
                files.update(f)
            row = conn.execute(
                "SELECT project_id, version, idle_outcome FROM session_v2 WHERE id=?",
                (ref.session_id,),
            ).fetchone() or (None, None, None)
        finally:
            conn.close()
        return Extraction(
            user_prompts=prompts,
            tool_errors=errors,
            scratchpad_dir=None,
            touched_files=sorted(files)[:MAX_TOUCHED_FILES],
            transcript_found=True,
            source_meta={
                "project_id": row[0],
                "opencode_version": row[1],
                "idle_outcome": row[2],
                "subagent_session_ids": sorted(m["id"] for m in members[1:]),
                "schema_migration": migration,
            },
        )
