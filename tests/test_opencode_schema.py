import logging
from pathlib import Path

import pytest

from claudalizer.sources import opencode_schema as s
from tests.opencode_fixture import OpencodeDB


@pytest.fixture(autouse=True)
def _reset():
    s._reset_warnings()


def _make(tmp_path, **kw):
    p = tmp_path / "oc.db"
    OpencodeDB(p, **kw).close()
    return p


def test_missing_column_returns_none_and_warns(tmp_path, caplog):
    p = tmp_path / "oc.db"
    db = OpencodeDB(p)
    db.drop_column("session_v2", "idle_outcome")
    db.close()
    with caplog.at_level(logging.WARNING):
        assert s.open_readonly(p) is None
        assert s.open_readonly(p) is None
    msgs = [r.message for r in caplog.records]
    assert len(msgs) == 1 and "session_v2.idle_outcome" in msgs[0]


def test_unknown_migration_warns_and_reads(tmp_path, caplog):
    p = _make(tmp_path, migration="29990101000000_future")
    with caplog.at_level(logging.WARNING):
        conn, mig = s.open_readonly(p)
    assert mig == "29990101000000_future"
    assert conn.execute("select count(*) from session_v2").fetchone()[0] == 0
    conn.close()
    assert len(caplog.records) == 1


def test_empty_migration_table_warns_and_reads(tmp_path, caplog):
    p = _make(tmp_path, migration=None)
    with caplog.at_level(logging.WARNING):
        conn, mig = s.open_readonly(p)
    conn.close()
    assert mig == ""
    assert len(caplog.records) == 1


def test_known_migration_is_quiet(tmp_path, caplog):
    p = _make(tmp_path)
    with caplog.at_level(logging.WARNING):
        conn, mig = s.open_readonly(p)
    conn.close()
    assert mig == s.KNOWN_OPENCODE_MIGRATION
    assert not caplog.records


def test_missing_db_is_silent(tmp_path, caplog):
    with caplog.at_level(logging.DEBUG):
        assert s.open_readonly(tmp_path / "nope.db") is None
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_corrupt_db_returns_none_and_warns(tmp_path, caplog):
    p = tmp_path / "bad.db"
    p.write_bytes(b"this is not a sqlite database" * 100)
    with caplog.at_level(logging.WARNING):
        assert s.open_readonly(p) is None
    assert len(caplog.records) == 1


def test_open_does_not_modify_db(tmp_path):
    p = _make(tmp_path)
    before, mt = p.read_bytes(), p.stat().st_mtime_ns
    conn, _ = s.open_readonly(p)
    conn.execute("select * from session_v2").fetchall()
    conn.close()
    assert p.read_bytes() == before
    assert p.stat().st_mtime_ns == mt


def test_opencode_db_resolution_order(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("OPENCODE_DB", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert s.resolve_db_path(None) == tmp_path / "home/.local/share/opencode/opencode.db"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert s.resolve_db_path(None) == tmp_path / "xdg/opencode/opencode.db"
    monkeypatch.setenv("OPENCODE_DB", str(tmp_path / "env.db"))
    assert s.resolve_db_path(None) == tmp_path / "env.db"
    assert s.resolve_db_path(str(tmp_path / "flag.db")) == tmp_path / "flag.db"
    monkeypatch.setenv("OPENCODE_DB", "")
    monkeypatch.setenv("XDG_DATA_HOME", "")
    assert s.resolve_db_path("") == tmp_path / "home/.local/share/opencode/opencode.db"
    assert isinstance(s.resolve_db_path(None), Path)
