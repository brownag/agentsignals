import os
import sqlite3

from tests.opencode_fixture import OpencodeDB, assistant_data, tool_item


def test_fixture_builds_family_with_inline_and_part_content(tmp_path):
    p = tmp_path / "oc.db"
    with OpencodeDB(p) as db:
        db.add_session("root", "/work")
        db.add_session("child", "/work", parent_id="root")
        inline = tool_item("t1", "bash", input={"command": "ls"}, content_text="ok", time_completed=1500)
        m1 = db.add_message("root", "assistant", assistant_data([inline], ["a.py"]))
        m2 = db.add_message("root", "assistant", assistant_data())
        db.add_message("child", "assistant", assistant_data())
        db.add_part(m2, "root", 0, "tool", tool_item("t2", "read", input={"path": "x"}), call_id="c2")
    assert m1 != m2
    c = sqlite3.connect(p)
    assert c.execute("select count(*) from session_v2").fetchone()[0] == 2
    assert c.execute("select parent_id from session_v2 where id='child'").fetchone()[0] == "root"
    assert [r[0] for r in c.execute("select seq from session_message where session_id='root' order by seq")] == [1, 2]
    assert c.execute("select json_extract(data,'$.content[0].state.input.command') from session_message where id=?", (m1,)).fetchone()[0] == "ls"
    assert c.execute("select json_extract(data,'$.snapshot.files[0]') from session_message where id=?", (m1,)).fetchone()[0] == "a.py"
    assert c.execute("select json_extract(data,'$.name'), call_id from session_part").fetchone() == ("read", "c2")
    assert c.execute("select count(*) from migration").fetchone()[0] == 1
    c.close()


def test_conftest_points_opencode_db_at_missing_path(tmp_path):
    db = os.environ["OPENCODE_DB"]
    assert db.startswith(str(tmp_path))
    assert not os.path.exists(db)
    assert os.environ["XDG_DATA_HOME"].startswith(str(tmp_path))


def test_drop_column_removes_column(tmp_path):
    p = tmp_path / "oc.db"
    with OpencodeDB(p, migration=None) as db:
        db.drop_column("session_v2", "idle_outcome")
    c = sqlite3.connect(p)
    cols = [r[1] for r in c.execute("pragma table_info(session_v2)")]
    assert "idle_outcome" not in cols and "time_idle" in cols
    assert c.execute("select count(*) from migration").fetchone()[0] == 0
    c.close()
