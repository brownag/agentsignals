"""tests/test_scan_report.py - scan skip reporting and transcript-driven re-mining.

Every test uses tmp_path for tmp_root, claude_projects, and memories_root.
"""

import json
import os
import time

from claudalizer.cli import format_skip_summary
from claudalizer.miner import SessionMiner


def _age(path, seconds):
    t = time.time() - seconds
    os.utime(path, (t, t))


def _write_transcript(path, prompts):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in prompts:
            f.write(json.dumps({"type": "user", "message": {"content": p}}) + "\n")


def _make_session(tmp_root, claude_projects, slug, session_id, prompts):
    sess_dir = tmp_root / slug / session_id
    scratch = sess_dir / "scratchpad"
    scratch.mkdir(parents=True)
    probe = scratch / "probe.py"
    probe.write_text("# probe", encoding="utf-8")
    transcript = claude_projects / slug / f"{session_id}.jsonl"
    _write_transcript(transcript, prompts)
    _age(probe, 30)
    _age(scratch, 30)
    _age(sess_dir, 30)
    return sess_dir, probe, transcript


def _miner(tmp_path):
    return SessionMiner(
        tmp_root=tmp_path / "tmp_claude",
        claude_projects=tmp_path / "projects",
        memories_root=tmp_path / "memories",
        lock_file=tmp_path / "miner.lock",
    )


def test_transcript_change_alone_triggers_remine(tmp_path):
    slug = "-home-andrew-AI-demo"
    session_id = "transcript-only-uuid"
    _sess, _probe, transcript = _make_session(
        tmp_path / "tmp_claude", tmp_path / "projects", slug, session_id, ["Please rewrite the distiller tests now"]
    )
    miner = _miner(tmp_path)
    assert len(miner.scan_and_mine(debounce=True)) == 1

    # New prompt appended to the transcript only; the scratchpad is untouched.
    _write_transcript(transcript, ["Please rewrite the distiller tests now", "Also check the transcript-only re-mine path"])
    dossier_json = tmp_path / "memories" / slug / session_id / "dossier.json"
    _age(dossier_json, 8)
    _age(transcript, 0)

    dossiers = miner.scan_and_mine(debounce=True)
    assert [d.session_id for d in dossiers] == [session_id]
    saved = json.loads(dossier_json.read_text(encoding="utf-8"))
    assert saved["user_prompts"] == ["Please rewrite the distiller tests now", "Also check the transcript-only re-mine path"]


def test_scan_counts_up_to_date_and_active_sessions(tmp_path):
    slug = "-home-andrew-AI-demo"
    tmp_root = tmp_path / "tmp_claude"
    projects = tmp_path / "projects"
    _make_session(tmp_root, projects, slug, "settled-uuid-0001", ["Finish the earlier settled session work"])
    sess_b, probe_b, _ = _make_session(tmp_root, projects, slug, "active-uuid-0002", ["Still typing this request out in the terminal"])
    miner = _miner(tmp_path)
    assert len(miner.scan_and_mine(debounce=True)) == 2

    # B is written to now: active. A is already mined and unchanged: up to date.
    _age(probe_b, 0)
    _age(probe_b.parent, 0)
    _age(sess_b, 0)
    assert miner.scan_and_mine(debounce=True) == []
    assert miner.skipped["active"] == [f"{slug}/active-uuid-0002"]
    assert miner.skipped["up_to_date"] == 1
    assert miner.skipped["no_content"] == 0


def test_session_with_no_content_is_counted(tmp_path):
    slug = "-home-andrew-AI-demo"
    session_id = "empty-uuid-0003"
    tmp_root = tmp_path / "tmp_claude"
    sess_dir = tmp_root / slug / session_id
    (sess_dir / "scratchpad").mkdir(parents=True)
    transcript = tmp_path / "projects" / slug / f"{session_id}.jsonl"
    _write_transcript(transcript, [])
    for p in (sess_dir / "scratchpad", sess_dir):
        _age(p, 30)
    miner = _miner(tmp_path)

    assert miner.scan_and_mine(debounce=True) == []
    assert miner.skipped["no_content"] == 1
    assert miner.skipped["active"] == []


def test_format_skip_summary_names_active_sessions():
    text = format_skip_summary(
        {"active": ["-home-andrew-AI-demo/abc"], "up_to_date": 7, "no_content": 2}
    )
    assert "Skipped: 1 active" in text
    assert "7 already up to date" in text
    assert "2 with no content" in text
    assert "still active: -home-andrew-AI-demo/abc" in text


def test_format_skip_summary_with_nothing_skipped():
    text = format_skip_summary({"active": [], "up_to_date": 0, "no_content": 0})
    assert text.splitlines() == [
        "Skipped: 0 active (still changing; picked up on a later scan), 0 already up to date, 0 with no content."
    ]


def test_format_skip_summary_mentions_recent_only_when_nonzero():
    base = {"active": [], "up_to_date": 0, "no_content": 0}
    assert "less than" not in format_skip_summary({**base, "recent": 0})
    assert "less than" not in format_skip_summary(base)
    assert "2 re-mined less than 60 s ago" in format_skip_summary({**base, "recent": 2})
