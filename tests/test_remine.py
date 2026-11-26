import json
import os
import time
from pathlib import Path

from claudalizer.miner import SessionMiner

SLUG = "-home-andrew-AI-claudalizer"


def _setup(tmp_path, session_id="remine-session-uuid"):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    sess_dir = tmp_root / SLUG / session_id
    probe = sess_dir / "scratchpad" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text("v1", encoding="utf-8")
    proj_dir = claude_projects / SLUG
    proj_dir.mkdir(parents=True)
    transcript = proj_dir / f"{session_id}.jsonl"
    transcript.write_text(
        json.dumps({"type": "user", "message": {"content": "Keep the dossier stable"}}) + "\n",
        encoding="utf-8",
    )
    old = time.time() - 100
    for p in (probe, probe.parent, sess_dir, transcript):
        os.utime(p, (old, old))
    dossier = memories_root / SLUG / session_id / "dossier.json"
    miner = SessionMiner(tmp_root=tmp_root, claude_projects=claude_projects,
                         memories_root=memories_root, lock_file=tmp_path / "miner.lock")
    return miner, probe, transcript, dossier


def _age(path: Path, seconds: float):
    t = time.time() - seconds
    os.utime(path, (t, t))


def test_unchanged_remine_does_not_rewrite_dossier(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    assert len(miner.scan_and_mine(debounce=False)) == 1
    before = dossier.read_bytes()
    _age(dossier, 50)
    stale_mtime = dossier.stat().st_mtime

    _age(transcript, 10)  # transcript is newer than the dossier, but its content is the same
    assert miner.scan_and_mine(debounce=False) == []

    assert dossier.read_bytes() == before
    assert dossier.stat().st_mtime > stale_mtime
    assert miner.skipped["up_to_date"] == 1


def test_transcript_touch_without_new_content_keeps_dossier(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    before = dossier.read_bytes()
    _age(dossier, 50)
    _age(transcript, 10)

    miner.scan_and_mine(debounce=False)

    assert dossier.read_bytes() == before
    assert miner.pass_log == []


def test_scratchpad_byte_change_rewrites_dossier(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    _age(dossier, 50)
    probe.write_text("v2 with different bytes", encoding="utf-8")
    _age(probe, 5)

    dossiers = miner.scan_and_mine(debounce=False)

    assert len(dossiers) == 1
    saved = dossier.parent / "scratchpad" / "probe.py"
    assert saved.read_text(encoding="utf-8") == "v2 with different bytes"
    assert miner.pass_log == [f"re-mined {SLUG}/remine-session-uuid"]


def test_force_always_rewrites(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    before = dossier.read_bytes()
    stored_ts = json.loads(before)["scan_timestamp"]
    time.sleep(0.01)

    dossiers = miner.scan_and_mine(debounce=False, force=True)

    assert len(dossiers) == 1
    assert json.loads(dossier.read_bytes())["scan_timestamp"] > stored_ts
    assert miner.pass_log == [f"re-mined (--force) {SLUG}/remine-session-uuid"]


def test_min_remine_interval_skips_recent_dossier(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    before = dossier.read_bytes()
    miner.min_remine_seconds = 60.0
    probe.write_text("changed but recent", encoding="utf-8")
    _age(probe, 5)

    assert miner.scan_and_mine(debounce=False) == []

    assert miner.skipped["recent"] == 1
    assert dossier.read_bytes() == before


def test_min_remine_zero_by_default(tmp_path):
    miner, *_ = _setup(tmp_path)
    assert miner.min_remine_seconds == 0.0
    assert miner.skipped["recent"] == 0


def test_pass_log_names_mined_and_remined(tmp_path):
    miner, probe, transcript, dossier = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    assert miner.pass_log == [f"mined {SLUG}/remine-session-uuid"]

    _age(dossier, 50)
    probe.write_text("v2 again", encoding="utf-8")
    _age(probe, 5)
    miner.scan_and_mine(debounce=False)
    assert miner.pass_log == [f"re-mined {SLUG}/remine-session-uuid"]
