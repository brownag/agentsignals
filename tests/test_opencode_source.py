import os
import sqlite3
import time

from claudalizer.sources import opencode as oc
from claudalizer.miner import SessionMiner
from tests.opencode_fixture import OpencodeDB, assistant_data, tool_item

S = "s1"
LONG = "please do the thing now"


def _db(tmp_path):
    db = OpencodeDB(tmp_path / "oc.db")
    db.add_session(S, "/work/proj")
    return db


def _run(db, directory="/work/proj"):
    return oc.extract_session(db.conn, S, directory)


def test_slug_from_directory_matches_claude_code_rule():
    assert oc.slug_for_directory("/home/a/my.proj_x") == "-home-a-my-proj-x"


def test_prompts_from_user_messages_only(tmp_path):
    with _db(tmp_path) as db:
        db.add_message(S, "user", {"text": f"  {LONG}  "})
        db.add_message(S, "user", {"text": "short"})
        db.add_message(S, "synthetic", {"text": LONG})
        db.add_message(S, "system", {"text": LONG})
        prompts, _, _ = _run(db)
    assert prompts == [LONG]


def test_inline_and_part_content_merged_in_order(tmp_path):
    with _db(tmp_path) as db:
        mid = db.add_message(S, "assistant", assistant_data([{"type": "text", "text": "inline"}]))
        db.add_part(mid, S, 1, "tool", {"name": "x"}, call_id="c2")
        db.add_part(mid, S, 0, "text", {"text": "p0"})
        msgs = oc.load_messages(db.conn, S)
        parts = oc.load_parts(db.conn, S)
    content = oc.assistant_content(msgs[0]["data"], parts)
    assert content[0] == {"text": "p0", "type": "text"}
    assert content[1] == {"name": "x", "type": "tool", "id": "c2"}
    assert content[2]["text"] == "inline"


def test_tool_error_status_recorded(tmp_path):
    with _db(tmp_path) as db:
        item = tool_item("t1", "read", status="error", input={"filePath": "a.py"},
                         error={"type": "io", "message": "boom"}, time_completed=2000)
        db.add_message(S, "assistant", assistant_data([item]))
        _, errs, _ = _run(db)
    assert len(errs) == 1
    e = errs[0]
    assert e.error_output == "io error: boom" and e.exit_code is None
    assert e.tool_use_id == "t1" and e.command_or_input == "a.py"
    assert e.timestamp == "1970-01-01T00:00:02+00:00"


def test_failed_shell_exit_code_recorded(tmp_path):
    with _db(tmp_path) as db:
        item = tool_item("t1", "shell", input={"command": "make"}, metadata={"exit": 2},
                         content_text="oops")
        db.add_message(S, "assistant", assistant_data([item]))
        _, errs, _ = _run(db)
    assert errs[0].exit_code == 2
    assert errs[0].error_output == "oops\nExit code: 2"
    assert errs[0].timestamp == "1970-01-01T00:00:01+00:00"


def test_zero_exit_shell_not_recorded(tmp_path):
    with _db(tmp_path) as db:
        item = tool_item("t1", "shell", input={"command": "ls"}, metadata={"exit": 0},
                         content_text="ok")
        db.add_message(S, "assistant", assistant_data([item]))
        _, errs, _ = _run(db)
    assert errs == []


def test_shell_timeout_recorded(tmp_path):
    with _db(tmp_path) as db:
        item = tool_item("t1", "shell", input={"command": "sleep 9"},
                         metadata={"timeout": True}, content_text="timed out")
        item2 = tool_item("t2", "shell", input={"command": "x"}, content_text="Exit code: 3")
        db.add_message(S, "assistant", assistant_data([item, item2]))
        _, errs, _ = _run(db)
    assert errs[0].error_output == "timed out" and errs[0].exit_code is None
    assert errs[1].exit_code == 3


def test_failed_idle_turn_recorded(tmp_path):
    with _db(tmp_path) as db:
        db.add_message(S, "idle", {"outcome": "failed", "error": {"message": "rate limit"}})
        db.add_message(S, "idle", {"outcome": "succeeded"})
        _, errs, _ = _run(db)
    assert len(errs) == 1
    assert errs[0].tool_name == "session" and errs[0].error_output == "turn error: rate limit"
    assert errs[0].tool_use_id is None


def test_touched_files_from_snapshot_edit_and_patch(tmp_path):
    patch = "*** Begin Patch\n*** Add File: new/n.py\n+x\n*** Update File: /abs/u.py\n*** Delete File: d.py\n"
    items = [
        tool_item("e", "edit", input={"filePath": "src/a.py"}),
        tool_item("w", "write", input={"filePath": "/work/proj/src/../b.py"}),
        tool_item("p", "patch", input={"patchText": patch}),
    ]
    with _db(tmp_path) as db:
        db.add_message(S, "assistant", assistant_data(items, snapshot_files=["s.py", "src/a.py"]))
        _, _, files = _run(db)
    assert files == sorted([
        "/work/proj/s.py", "/work/proj/src/a.py", "/work/proj/b.py",
        "/work/proj/new/n.py", "/abs/u.py", "/work/proj/d.py",
    ])


def test_command_or_input_fallback_chain(tmp_path):
    items = [
        tool_item("1", "x", status="error", input={"command": "c", "filePath": "f"}),
        tool_item("2", "x", status="error", input={"filePath": "f"}),
        tool_item("3", "x", status="error", input={"patchText": "line1\nline2"}),
        tool_item("4", "x", status="error", input={"b": 1, "a": 2}),
        tool_item("5", "x", status="error", input={"command": "z" * 600}),
    ]
    with _db(tmp_path) as db:
        db.add_message(S, "assistant", assistant_data(items))
        _, errs, _ = _run(db)
    got = [e.command_or_input for e in errs]
    assert got[:4] == ["c", "f", "line1", '{"a": 2, "b": 1}']
    assert len(got[4]) == 500


def test_bad_json_rows_skipped(tmp_path):
    with _db(tmp_path) as db:
        db.conn.execute("INSERT INTO session_message VALUES ('m','s1','user',9,1,1,'{bad')")
        db.conn.commit()
        assert oc.load_messages(db.conn, S) == []
        assert isinstance(db.conn, sqlite3.Connection)


# ---- OpencodeSource discovery and settle ----

NOW_MS = int(time.time() * 1000)


def _fam_db(tmp_path):
    db = OpencodeDB(tmp_path / "fam.db")
    return db


def _sess(db, sid, directory="/work/proj", parent=None, age_s=0, idle=True, busy=1000, **kw):
    t = NOW_MS - int(age_s * 1000)
    db.add_session(sid, directory, parent_id=parent, time_busy=t - 1 if idle else t,
                   time_idle=t if idle else None, time_created=t, time_updated=t, **kw)
    return t


def _prompt(db, sid, t):
    db.add_message(sid, "user", {"text": LONG}, time_updated=t)


def _miner(tmp_path, db_path):
    return SessionMiner(
        tmp_root=tmp_path / "none", claude_projects=tmp_path / "cp",
        memories_root=tmp_path / "mem", lock_file=tmp_path / "lock",
        sources=[oc.OpencodeSource(db_path)],
    )


def _dossier(tmp_path, slug="-work-proj", sid="a"):
    return tmp_path / "mem" / slug / sid / "dossier.json"


def test_busy_session_not_mined(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "a", age_s=5, idle=False)
        _prompt(db, "a", t)
    m = _miner(tmp_path, db.path)
    assert m.scan_and_mine(debounce=True) == []
    assert m.skipped["active"] == ["-work-proj/a"]


def test_unmarked_session_mined_after_quiet_window(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "a", age_s=oc.OPENCODE_QUIET_SECONDS + 60, idle=False)
        _prompt(db, "a", t)
    m = _miner(tmp_path, db.path)
    assert len(m.scan_and_mine(debounce=True)) == 1
    assert _dossier(tmp_path).exists()


def test_unchanged_session_is_up_to_date(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "a", age_s=100)
        _prompt(db, "a", t)
    m = _miner(tmp_path, db.path)
    assert len(m.scan_and_mine()) == 1
    assert m.scan_and_mine() == []
    assert m.skipped["up_to_date"] == 1


def test_part_update_triggers_remine(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "a", age_s=100)
        mid = db.add_message("a", "assistant", assistant_data([]), time_updated=t)
        db.add_part(mid, "a", 0, "text", {"text": "x"}, time_updated=t)
        _prompt(db, "a", t)
    m = _miner(tmp_path, db.path)
    assert len(m.scan_and_mine()) == 1
    old = time.time() - 50
    os.utime(_dossier(tmp_path), (old, old))
    conn = sqlite3.connect(str(db.path))
    conn.execute("UPDATE session_part SET time_updated=?", (int((old + 20) * 1000),))
    conn.commit()
    conn.close()
    assert len(m.scan_and_mine()) == 1


def test_busy_subagent_holds_root(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "a", age_s=100)
        _sess(db, "c", parent="a", age_s=100, idle=False)
        _prompt(db, "a", t)
    m = _miner(tmp_path, db.path)
    assert m.scan_and_mine(debounce=True) == []
    assert m.skipped["active"] == ["-work-proj/a"]


def test_orphan_subagent_becomes_root(tmp_path):
    with _fam_db(tmp_path) as db:
        t = _sess(db, "o", parent="missing", age_s=100)
        _prompt(db, "o", t)
    src = oc.OpencodeSource(db.path)
    refs = list(src.iter_sessions(None))
    assert [r.session_id for r in refs] == ["o"]
    assert src._families["o"][0]["id"] == "o"


def test_target_slug_filters_families(tmp_path):
    with _fam_db(tmp_path) as db:
        _sess(db, "a", "/work/one", age_s=100)
        _sess(db, "b", "/work/two", age_s=100)
        _sess(db, "c", "/work/two", parent="b", age_s=100)
    src = oc.OpencodeSource(db.path)
    refs = list(src.iter_sessions("-work-two"))
    assert [r.session_id for r in refs] == ["b"]
    assert [f["id"] for f in src._families["b"]] == ["b", "c"]
