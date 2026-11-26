"""Extraction functions for opencode sessions (pure functions over a sqlite3 connection)."""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from claudalizer.miner import (
    EXIT_CODE_PATTERN,
    MIN_PROMPT_LENGTH,
    ToolErrorEvent,
    has_nonzero_exit_code,
    is_git_discernable,
)

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
