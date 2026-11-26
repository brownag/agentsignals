import logging
import os
import shutil
import subprocess

import pytest

from claudalizer import memory_git
from claudalizer.memory_git import GIT_IGNORE_LINES, MemoryRepo

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


@pytest.fixture(autouse=True)
def _fresh_warnings():
    memory_git._reset_warnings()
    yield
    memory_git._reset_warnings()


def _git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", *args], cwd=root, env=env, capture_output=True,
                          text=True, check=True).stdout


def _count(root):
    return int(_git(root, "rev-list", "--count", "HEAD").strip())


def test_ensure_creates_repo_with_baseline_and_gitignore(tmp_path):
    root = tmp_path / "memories"
    (root / "proj").mkdir(parents=True)
    (root / "proj" / "memory.md").write_text("old\n", encoding="utf-8")

    repo = MemoryRepo(root)
    assert repo.ensure() is True

    assert (root / ".git").is_dir()
    assert (root / ".gitignore").read_text(encoding="utf-8").splitlines() == GIT_IGNORE_LINES
    assert _git(root, "log", "--format=%s").splitlines() == ["baseline: existing memories"]
    assert "proj/memory.md" in _git(root, "ls-files")
    assert repo.active


def test_ensure_is_idempotent(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    assert repo.ensure()
    assert repo.ensure()
    assert MemoryRepo(root).ensure()
    assert _count(root) == 1


def test_commit_pass_commits_only_when_changed(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    repo.ensure()

    (root / "a.json").write_text("{}", encoding="utf-8")
    sha = repo.commit_pass("scan: 1 mined", ["mined p/s"])
    assert sha
    assert _count(root) == 2

    assert repo.commit_pass("scan: nothing", ["x"]) is None
    assert _count(root) == 2


def test_commit_message_has_title_and_lines(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    repo.ensure()
    (root / "a.json").write_text("{}", encoding="utf-8")
    repo.commit_pass("scan: 2 mined", ["mined p/one", "mined p/two"])

    message = _git(root, "log", "-1", "--format=%B")
    assert message.splitlines()[0] == "scan: 2 mined"
    assert "mined p/one" in message.splitlines()
    assert "mined p/two" in message.splitlines()


def test_commit_external_records_dirty_tree(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    repo.ensure()
    assert repo.commit_external("scan") is None  # clean tree

    (root / "hand_edit.md").write_text("edited\n", encoding="utf-8")
    sha = repo.commit_external("scan")
    assert sha
    assert _git(root, "log", "-1", "--format=%s") == "external: changes found before scan\n"
    assert "hand_edit.md" in _git(root, "show", "--name-only", "--format=", "HEAD")


def test_scan_status_and_tmp_files_are_ignored(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    repo.ensure()
    (root / "scan_status.json").write_text("{}", encoding="utf-8")
    (root / "dossier.json.tmp").write_text("{}", encoding="utf-8")
    (root / ".PROJECT_MEMORY.md.tmp").write_text("x", encoding="utf-8")

    assert repo.commit_pass("scan: none", ["x"]) is None
    assert _count(root) == 1


def test_disabled_repo_is_noop(tmp_path):
    root = tmp_path / "memories"
    repo = MemoryRepo(root, enabled=False)
    assert repo.ensure() is False
    assert repo.active is False
    assert repo.commit_external("scan") is None
    assert repo.commit_pass("scan: x", ["x"]) is None
    assert not (root / ".git").exists()


def test_missing_git_warns_once_and_continues(tmp_path, monkeypatch, caplog):
    root = tmp_path / "memories"

    def _no_git(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(memory_git.shutil, "which", lambda _name: "/usr/bin/git")
    monkeypatch.setattr(memory_git.subprocess, "run", _no_git)
    repo = MemoryRepo(root)
    with caplog.at_level(logging.WARNING):
        assert repo.ensure() is False
        assert repo.commit_pass("scan: x", ["x"]) is None
        assert repo.commit_external("scan") is None
    warnings = [r for r in caplog.records if "git not found" in r.getMessage()]
    assert len(warnings) == 1


def test_git_env_vars_do_not_leak(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "bogus.git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "elsewhere"))
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    assert repo.ensure()
    (root / "a.json").write_text("{}", encoding="utf-8")
    assert repo.commit_pass("scan: 1", ["x"])
    assert _count(root) == 2


def test_commits_use_bot_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Someone Else")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "someone@example.invalid")
    root = tmp_path / "memories"
    repo = MemoryRepo(root)
    repo.ensure()
    (root / "a.json").write_text("{}", encoding="utf-8")
    repo.commit_pass("scan: 1", ["x"])
    assert _git(root, "log", "--format=%an <%ae>").splitlines() == [
        "claudalizer <claudalizer@localhost>",
        "claudalizer <claudalizer@localhost>",
    ]


def test_real_memories_root_refused_under_tests(monkeypatch):
    monkeypatch.setenv("CLAUDALIZER_TESTING", "1")
    with pytest.raises(RuntimeError):
        MemoryRepo(memory_git.Path.home() / ".claude-mined-memories")
