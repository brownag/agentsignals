"""Builder for synthetic opencode SQLite databases (tests only)."""

import json
import sqlite3
from typing import Any, Optional

_SCHEMA = """
CREATE TABLE migration (id TEXT PRIMARY KEY, time_completed INTEGER);
CREATE TABLE session_v2 (
    id TEXT PRIMARY KEY, parent_id TEXT, directory TEXT, project_id TEXT, version TEXT,
    time_created INTEGER, time_updated INTEGER, time_busy INTEGER, time_idle INTEGER,
    idle_outcome TEXT
);
CREATE TABLE session_message (
    id TEXT PRIMARY KEY, session_id TEXT, type TEXT, seq INTEGER,
    time_created INTEGER, time_updated INTEGER, data TEXT
);
CREATE TABLE session_part (
    message_id TEXT, session_id TEXT, ordinal INTEGER, type TEXT, call_id TEXT,
    time_created INTEGER, time_updated INTEGER, data TEXT,
    PRIMARY KEY (message_id, ordinal)
);
CREATE INDEX session_message_session_seq_idx ON session_message (session_id, seq);
CREATE INDEX session_part_session_message_idx ON session_part (session_id, message_id, ordinal);
"""


class OpencodeDB:
    def __init__(self, path, migration: Optional[str] = "20261120004954_machine-key"):
        self.path = path
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(_SCHEMA)
        if migration is not None:
            self.conn.execute("INSERT INTO migration VALUES (?, ?)", (migration, 1000))
        self.conn.commit()
        self._msg_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.conn.commit()
        self.conn.close()

    def add_session(self, id, directory, parent_id=None, time_busy=1000, time_idle=2000,
                    idle_outcome="succeeded", time_created=1000, time_updated=1000,
                    version="2.4.1", project_id="p1"):
        self.conn.execute(
            "INSERT INTO session_v2 (id, parent_id, directory, project_id, version, time_created,"
            " time_updated, time_busy, time_idle, idle_outcome) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (id, parent_id, directory, project_id, version, time_created, time_updated,
             time_busy, time_idle, idle_outcome),
        )
        self.conn.commit()

    def add_message(self, session_id, type, data, seq=None, time_updated=1000, time_created=1000):
        if seq is None:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM session_message WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            seq = row[0]
        self._msg_count += 1
        msg_id = f"msg_{session_id}_{self._msg_count}"
        self.conn.execute(
            "INSERT INTO session_message VALUES (?,?,?,?,?,?,?)",
            (msg_id, session_id, type, seq, time_created, time_updated, json.dumps(data)),
        )
        self.conn.commit()
        return msg_id

    def add_part(self, message_id, session_id, ordinal, type, data, call_id=None, time_updated=1000):
        self.conn.execute(
            "INSERT INTO session_part VALUES (?,?,?,?,?,?,?,?)",
            (message_id, session_id, ordinal, type, call_id, time_updated, time_updated,
             json.dumps(data)),
        )
        self.conn.commit()

    def drop_column(self, table, column):
        self.conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        self.conn.commit()


def tool_item(id, name, status="completed", input=None, metadata=None, content_text=None,
              error=None, time_completed=None) -> dict[str, Any]:
    return {
        "type": "tool",
        "id": id,
        "name": name,
        "state": {
            "status": status,
            "input": input if input is not None else {},
            "metadata": metadata if metadata is not None else {},
            "content": [{"type": "text", "text": content_text}] if content_text is not None else [],
            "error": error,
        },
        "time": {"created": 1000, "completed": time_completed},
    }


def assistant_data(content=None, snapshot_files=None) -> dict[str, Any]:
    data: dict[str, Any] = {"content": content or []}
    if snapshot_files is not None:
        data["snapshot"] = {"files": snapshot_files}
    return data
