import json
import os
import shutil
import subprocess
import time

import pytest

from agentsignals.memory_git import MemoryRepo
from agentsignals.miner import SessionMiner

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

SLUG = "-home-andrew-AI-claudalizer"
SID = "git-session-uuid"


def _git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", *args], cwd=root, env=env, capture_output=True,
                          text=True, check=True).stdout


def _subjects(root):
    return _git(root, "log", "--format=%s").splitlines()


def _setup(tmp_path, repo=True):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    probe = tmp_root / SLUG / SID / "scratchpad" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text("v1", encoding="utf-8")
    proj_dir = claude_projects / SLUG
    proj_dir.mkdir(parents=True)
    transcript = proj_dir / f"{SID}.jsonl"
    transcript.write_text(json.dumps({"type": "user", "message": {"content": "Remember this"}}) + "\n",
                          encoding="utf-8")
    old = time.time() - 100
    for p in (probe, probe.parent, probe.parent.parent, transcript):
        os.utime(p, (old, old))
    miner = SessionMiner(
        tmp_root=tmp_root, claude_projects=claude_projects, memories_root=memories_root,
        lock_file=tmp_path / "miner.lock",
        repo=MemoryRepo(memories_root) if repo else None,
    )
    dossier = memories_root / SLUG / SID / "dossier.json"
    return miner, probe, dossier, memories_root


def _age(path, seconds):
    t = time.time() - seconds
    os.utime(path, (t, t))


def test_first_scan_creates_baseline_then_scan_commit(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    assert len(miner.scan_and_mine(debounce=False)) == 1

    assert _subjects(root) == ["scan: 1 mined", "baseline: existing memories"]
    assert miner.last_commit


def test_scan_with_no_change_makes_no_commit(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    count = len(_subjects(root))

    assert miner.scan_and_mine(debounce=False) == []
    assert len(_subjects(root)) == count
    assert miner.last_commit is None


def test_remine_commit_lists_session(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    _age(dossier, 50)
    probe.write_text("v2 changed", encoding="utf-8")
    _age(probe, 5)

    miner.scan_and_mine(debounce=False)

    message = _git(root, "log", "-1", "--format=%B")
    assert message.splitlines()[0] == "scan: 1 re-mined"
    assert f"re-mined {SLUG}/{SID}" in message


def test_forced_scan_commit_marked_force(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)

    miner.scan_and_mine(debounce=False, force=True)

    assert _git(root, "log", "-1", "--format=%s").strip() == "scan: 1 re-mined (--force)"


def test_hand_edit_committed_as_external_before_scan(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    (root / "hand_note.md").write_text("typed by hand\n", encoding="utf-8")

    miner.scan_and_mine(debounce=False)  # nothing to mine, so only the external commit

    assert _subjects(root)[0].startswith("external: changes found before scan")
    assert "hand_note.md" in _git(root, "show", "--name-only", "--format=", "HEAD")


def test_previous_dossier_restorable_from_git(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path)
    miner.scan_and_mine(debounce=False)
    old_text = dossier.read_text(encoding="utf-8")

    _age(dossier, 50)
    probe.write_text("v2 changed", encoding="utf-8")
    _age(probe, 5)
    miner.scan_and_mine(debounce=False)

    rel = dossier.relative_to(root).as_posix()
    assert _git(root, "show", f"HEAD~1:{rel}") == old_text


def test_repo_none_changes_nothing(tmp_path):
    miner, probe, dossier, root = _setup(tmp_path, repo=False)
    assert len(miner.scan_and_mine(debounce=False)) == 1
    assert not (root / ".git").exists()
    assert miner.last_commit is None
