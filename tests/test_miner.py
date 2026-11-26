import json
import os
import shutil
import time
from pathlib import Path
import pytest

from claudalizer.miner import (
    SessionMiner,
    decode_slug,
    is_git_discernable,
    parse_transcript_events,
    snapshot_scratchpad,
    file_lock,
    is_file_settled,
)
import claudalizer.miner as miner_module
from claudalizer.distiller import MemoryDistiller
from claudalizer.ipc import emit_waybar_signal
from claudalizer.cli import main as cli_main


def test_slug_decoding(tmp_path):
    # Valid absolute system path
    slug = "-home-andrew-AI-claudalizer"
    decoded = decode_slug(slug)
    assert decoded is not None
    assert "/home/andrew/AI/claudalizer" in decoded

    # Fallback path
    non_existent = "-some-nonexistent-deep-nested-path"
    decoded_fallback = decode_slug(non_existent)
    assert decoded_fallback == "/some/nonexistent/deep/nested/path"

    # Real directories under tmp_path: decode_slug resolves against the filesystem,
    # so the slug is built from the real path (Claude Code replaces "/" with "-").
    def slug_for(path: Path) -> str:
        return "-" + str(path).lstrip("/").replace("/", "-")

    # Multiple dashes inside one directory name
    multi_dash = tmp_path / "my-pkg-v2"
    multi_dash.mkdir()
    assert decode_slug(slug_for(multi_dash)) == str(multi_dash)

    # Nested path with dashes in several segments
    nested = tmp_path / "work" / "src-lib" / "my-pkg"
    nested.mkdir(parents=True)
    assert decode_slug(slug_for(nested)) == str(nested)

    # Trailing dash in the directory name
    trailing = tmp_path / "proj-"
    trailing.mkdir()
    assert decode_slug(slug_for(trailing)) == str(trailing)


def test_is_git_discernable():
    # Clean git log or status is discernable
    assert is_git_discernable("Bash", "git status", "")
    assert is_git_discernable("Bash", "git diff", "")
    assert is_git_discernable("Edit", "/path/to/file.py", "")

    # Tool error or non-git command failure is NOT git-discernable
    assert not is_git_discernable("Bash", "cargo test", "Exit code 101\nfailed to compile")
    assert not is_git_discernable("Bash", "python test.py", "No such file or directory")


def test_git_state_filtering(tmp_path):
    transcript_file = tmp_path / "session-git.jsonl"

    def tool_use(tool_id, command):
        return {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "id": tool_id, "name": "Bash", "input": {"command": command}}]
            },
        }

    def tool_result(tool_id, text):
        return {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": False, "content": text}]
            },
        }

    lines = [
        {"type": "user", "message": {"content": "Check the repo state before the release."}},
        tool_use("git-fail", "git diff HEAD~1"),
        tool_result("git-fail", "Exit code 1\nfatal: bad revision"),
        tool_use("exit-zero", "pytest tests/"),
        tool_result("exit-zero", "Exit code 0\n12 passed"),
        tool_use("git-ok", "git status"),
        tool_result("git-ok", ""),
    ]
    with open(transcript_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")

    _, tool_errors = parse_transcript_events(transcript_file)
    kept = {event.tool_use_id for event in tool_errors}
    assert "git-fail" in kept
    assert "exit-zero" not in kept
    assert "git-ok" not in kept


def test_jsonl_corrupt_recovery(tmp_path):
    transcript_file = tmp_path / "session-corrupt.jsonl"
    valid_first = json.dumps(
        {"type": "user", "message": {"content": "First valid prompt that is long enough."}}
    ).encode("utf-8")
    valid_second = json.dumps(
        {"type": "user", "message": {"content": "Second valid prompt after the damage."}}
    ).encode("utf-8")
    half_written = b'{"type": "user", "message": {"content": "half'
    truncated = b'{"type": "us'
    not_utf8 = b"\xff\xfe"
    transcript_file.write_bytes(b"\n".join([valid_first, half_written, truncated, not_utf8, valid_second]) + b"\n")

    prompts, _ = parse_transcript_events(transcript_file)

    assert "First valid prompt that is long enough." in prompts
    assert "Second valid prompt after the damage." in prompts


def test_transcript_parsing(tmp_path):
    transcript_file = tmp_path / "session-123.jsonl"
    lines = [
        {"type": "user", "message": {"content": "Short"}},  # < 15 chars, filtered
        {"type": "user", "message": {"content": "This is a legitimate long user prompt setting goals."}},
        {"type": "user", "message": {"content": "<local-command-caveat> ignored"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest tests/"}}
                ]
            },
        },
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "is_error": True,
                        "content": "Exit code 1\nFAILED tests/test_foo.py::test_bar",
                    }
                ]
            },
        },
    ]

    with open(transcript_file, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")

    prompts, errors = parse_transcript_events(transcript_file)
    assert len(prompts) == 1
    assert "legitimate long user prompt" in prompts[0]
    assert len(errors) == 1
    assert errors[0].tool_name == "Bash"
    assert errors[0].exit_code == 1
    assert "FAILED tests/test_foo.py" in errors[0].error_output


def test_snapshot_scratchpad(tmp_path):
    src_dir = tmp_path / "scratchpad"
    dest_dir = tmp_path / "mined_scratchpad"
    src_dir.mkdir()

    # Valid text file
    txt_file = src_dir / "test_spike.py"
    txt_file.write_text("print('hello world')", encoding="utf-8")

    # Binary file (contains null byte)
    bin_file = src_dir / "binary.dat"
    bin_file.write_bytes(b"\x00\x01\x02\x03")

    # Large file (>250KB)
    large_file = src_dir / "large.txt"
    large_file.write_bytes(b"a" * (255 * 1024))

    # Subdirectory with virtualenv (should be skipped)
    venv_file = src_dir / "venv" / "bin" / "python"
    venv_file.parent.mkdir(parents=True)
    venv_file.write_text("echo", encoding="utf-8")

    copied, _ = snapshot_scratchpad(src_dir, dest_dir)
    assert "test_spike.py" in copied
    assert "binary.dat" not in copied
    assert "large.txt" not in copied
    assert not any("venv" in c for c in copied)
    assert (dest_dir / "test_spike.py").exists()


def test_snapshot_reports_skipped_files(tmp_path, monkeypatch):
    src_dir = tmp_path / "scratchpad"
    dest_dir = tmp_path / "mined"
    src_dir.mkdir()
    (src_dir / "ok.txt").write_text("fine", encoding="utf-8")
    (src_dir / "big.txt").write_bytes(b"a" * (255 * 1024))
    (src_dir / "bin.dat").write_bytes(b"\x00\x01")
    (src_dir / "locked.txt").write_text("secret", encoding="utf-8")
    (src_dir / "venv").mkdir()
    (src_dir / "venv" / "x.txt").write_text("x", encoding="utf-8")

    real_copy2 = shutil.copy2

    def fake_copy2(src, dst, *a, **k):
        if Path(src).name == "locked.txt":
            raise PermissionError("denied")
        return real_copy2(src, dst, *a, **k)

    monkeypatch.setattr(miner_module.shutil, "copy2", fake_copy2)

    copied, skipped = snapshot_scratchpad(src_dir, dest_dir)
    reasons = {s["path"]: s["reason"] for s in skipped}
    assert reasons == {"big.txt": "oversized", "bin.dat": "binary", "locked.txt": "unreadable"}
    sizes = {s["path"]: s["size_bytes"] for s in skipped}
    assert sizes["big.txt"] == 255 * 1024
    assert copied == ["ok.txt"]
    assert not (dest_dir / "big.txt").exists()
    assert not (dest_dir / "bin.dat").exists()
    assert not (dest_dir / "locked.txt").exists()


def test_filter_oversized_scratchpad(tmp_path):
    src_dir = tmp_path / "scratchpad"
    dest_dir = tmp_path / "mined"
    src_dir.mkdir()
    small_names = ["small.py", "small.sh", "small.log"]
    for name in small_names:
        (src_dir / name).write_text("ok\n", encoding="utf-8")
    big_size = miner_module.MAX_SCRATCHPAD_FILE_BYTES + 1
    (src_dir / "big.log").write_bytes(b"a" * big_size)
    (src_dir / "blob.bin").write_bytes(b"\x00binary text")

    copied, skipped = snapshot_scratchpad(src_dir, dest_dir)

    assert sorted(copied) == sorted(small_names)
    for name in small_names:
        assert (dest_dir / name).exists()
    assert not (dest_dir / "big.log").exists()
    assert not (dest_dir / "blob.bin").exists()
    assert len(skipped) == 2
    by_path = {s["path"]: s for s in skipped}
    assert by_path["big.log"]["reason"] == "oversized"
    assert by_path["big.log"]["size_bytes"] == big_size
    assert by_path["blob.bin"]["reason"] == "binary"


def test_file_lock(tmp_path):
    lock_file = tmp_path / "test.lock"
    with file_lock(lock_file):
        assert lock_file.exists()


def test_session_miner_pipeline(tmp_path):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    lock_file = tmp_path / "miner.lock"

    slug = "-home-andrew-AI-claudalizer"
    session_id = "test-session-uuid-456"

    # Create dummy session structure in tmp_root
    sess_dir = tmp_root / slug / session_id
    scratchpad_dir = sess_dir / "scratchpad"
    scratchpad_dir.mkdir(parents=True)
    (scratchpad_dir / "debug_probe.py").write_text("# debug probe", encoding="utf-8")

    # Create dummy transcript in claude_projects
    proj_dir = claude_projects / slug
    proj_dir.mkdir(parents=True)
    transcript_file = proj_dir / f"{session_id}.jsonl"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "Debug why the unit test is failing in pipeline"}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest"}}]}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "Exit code 1\nAssertionError in test"}]}}) + "\n")

    miner = SessionMiner(
        tmp_root=tmp_root,
        claude_projects=claude_projects,
        memories_root=memories_root,
        lock_file=lock_file,
    )

    dossiers = miner.scan_and_mine(debounce=False)
    assert len(dossiers) == 1
    d = dossiers[0]
    assert d.slug == slug
    assert d.session_id == session_id
    assert len(d.user_prompts) == 1
    assert len(d.tool_errors) == 1
    assert "debug_probe.py" in d.scratchpad_files

    # Verify dossier.json written to disk
    dossier_json = memories_root / slug / session_id / "dossier.json"
    assert dossier_json.exists()
    data = json.loads(dossier_json.read_text(encoding="utf-8"))
    assert data["session_id"] == session_id


def test_settle_sees_nested_rewrite(tmp_path):
    sess_dir = tmp_path / "session"
    nested = sess_dir / "scratchpad" / "notes.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("old", encoding="utf-8")

    # Age everything well past the settle window
    old = time.time() - 10
    for p in (nested, nested.parent, sess_dir):
        os.utime(p, (old, old))
    assert is_file_settled(sess_dir, 2.0)

    # Rewrite only the nested file: the session dir's own mtime stays old
    nested.write_text("new", encoding="utf-8")
    assert os.stat(sess_dir).st_mtime < time.time() - 5
    assert not is_file_settled(sess_dir, 2.0)

    # Once the nested file has been quiet for the window, the session settles
    os.utime(nested, (old, old))
    assert is_file_settled(sess_dir, 2.0)


def test_rewritten_scratchpad_is_recaptured(tmp_path):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "rewrite-session-uuid"

    sess_dir = tmp_root / slug / session_id
    probe = sess_dir / "scratchpad" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text("v1", encoding="utf-8")
    proj_dir = claude_projects / slug
    proj_dir.mkdir(parents=True)
    with open(proj_dir / f"{session_id}.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "Rewrite the scratchpad after mining"}}) + "\n")

    old = time.time() - 10
    for p in (probe, probe.parent, sess_dir):
        os.utime(p, (old, old))
    miner = SessionMiner(tmp_root=tmp_root, claude_projects=claude_projects,
                         memories_root=memories_root, lock_file=tmp_path / "miner.lock")

    assert len(miner.scan_and_mine(debounce=True)) == 1
    saved = memories_root / slug / session_id / "scratchpad" / "probe.py"
    assert saved.read_text(encoding="utf-8") == "v1"

    # Nothing changed: the already-mined session is still skipped
    assert miner.scan_and_mine(debounce=True) == []

    # Rewrite the source after the dossier was written; the next scan must re-capture it
    # Age the dossier to 8 s ago, then rewrite the probe 5 s ago: settled, and newer than the dossier
    dossier_json = memories_root / slug / session_id / "dossier.json"
    os.utime(dossier_json, (time.time() - 8, time.time() - 8))
    probe.write_text("v2", encoding="utf-8")
    os.utime(probe, (time.time() - 5, time.time() - 5))
    assert len(miner.scan_and_mine(debounce=True)) == 1
    assert saved.read_text(encoding="utf-8") == "v2"


def test_skipped_session_is_mined_on_next_scan(tmp_path):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "retry-session-uuid"

    sess_dir = tmp_root / slug / session_id
    scratch = sess_dir / "scratchpad"
    scratch.mkdir(parents=True)
    probe = scratch / "probe.py"
    probe.write_text("# probe", encoding="utf-8")

    proj_dir = claude_projects / slug
    proj_dir.mkdir(parents=True)
    with open(proj_dir / f"{session_id}.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "Retry the skipped session on next poll"}}) + "\n")

    miner = SessionMiner(
        tmp_root=tmp_root,
        claude_projects=claude_projects,
        memories_root=tmp_path / "memories",
        lock_file=tmp_path / "miner.lock",
    )

    # First poll: the session was written just now, so it is not settled and is skipped
    assert miner.scan_and_mine(debounce=True) == []

    # Second poll, after the write has been quiet long enough: the session is mined
    old = time.time() - 10
    for p in (probe, scratch, sess_dir):
        os.utime(p, (old, old))
    dossiers = miner.scan_and_mine(debounce=True)
    assert [d.session_id for d in dossiers] == [session_id]


def _make_mineable_session(tmp_root, claude_projects, slug, session_id):
    scratch = tmp_root / slug / session_id / "scratchpad"
    scratch.mkdir(parents=True)
    (scratch / "probe.py").write_text("# probe", encoding="utf-8")
    proj = claude_projects / slug
    proj.mkdir(parents=True)
    with open(proj / f"{session_id}.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "Atomic dossier write probe prompt"}}) + "\n")
    return scratch


def test_failed_dossier_write_keeps_previous_dossier(tmp_path, monkeypatch):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "atomic-session-uuid"
    scratch = _make_mineable_session(tmp_root, claude_projects, slug, session_id)

    miner = SessionMiner(tmp_root=tmp_root, claude_projects=claude_projects,
                         memories_root=memories_root, lock_file=tmp_path / "miner.lock")
    first = miner._mine_session(slug, None, session_id, scratch, force=True)
    assert first is not None
    dossier_json = memories_root / slug / session_id / "dossier.json"
    before = dossier_json.read_text(encoding="utf-8")

    # Make the next write fail partway through, as if the process crashed
    real_dump = json.dump

    def partial_dump(obj, fp, **kwargs):
        fp.write('{"session_id": "trunc')
        raise OSError("simulated crash during dossier write")

    monkeypatch.setattr(miner_module.json, "dump", partial_dump)
    with pytest.raises(OSError):
        miner._mine_session(slug, None, session_id, scratch, force=True)
    monkeypatch.setattr(miner_module.json, "dump", real_dump)

    # The previous dossier must survive intact and still parse
    assert dossier_json.read_text(encoding="utf-8") == before
    assert json.loads(before)["session_id"] == session_id


def test_successful_dossier_write_leaves_no_temp_file(tmp_path):
    tmp_root = tmp_path / "tmp_claude"
    claude_projects = tmp_path / "projects"
    memories_root = tmp_path / "memories"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "clean-write-session-uuid"
    scratch = _make_mineable_session(tmp_root, claude_projects, slug, session_id)

    miner = SessionMiner(tmp_root=tmp_root, claude_projects=claude_projects,
                         memories_root=memories_root, lock_file=tmp_path / "miner.lock")
    assert miner._mine_session(slug, None, session_id, scratch, force=True) is not None

    session_out = memories_root / slug / session_id
    assert json.loads((session_out / "dossier.json").read_text(encoding="utf-8"))["session_id"] == session_id
    assert not list(session_out.glob("*.tmp"))


def test_distiller_with_llm(tmp_path, fake_llm):
    memories_root = tmp_path / "memories"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "test-session-uuid-456"

    sess_dir = memories_root / slug / session_id
    sess_dir.mkdir(parents=True)
    dossier_data = {
        "slug": slug,
        "session_id": session_id,
        "decoded_path": "/home/andrew/AI/claudalizer",
        "user_prompts": ["Fix python env error in test suite"],
        "tool_errors": [
            {
                "tool_name": "Bash",
                "command_or_input": "python run.py",
                "error_output": "Exit code 127\nNo such file or directory: 'python'",
                "exit_code": 127,
            }
        ],
        "scratchpad_files": ["probe.py"],
    }
    with open(sess_dir / "dossier.json", "w", encoding="utf-8") as f:
        json.dump(dossier_data, f)

    distiller = MemoryDistiller(memories_root=memories_root)
    res = distiller.distill_session(slug, session_id, llm_endpoint="http://127.0.0.1:9/v1")
    assert res is not None
    assert res.exists()

    content = res.read_text(encoding="utf-8")
    assert "Tool / Skill Friction" in content
    assert "Blind Alleys & Discarded Spikes" in content
    assert "Directives for CLAUDE.md" in content
    assert "python run.py" in content

    # Check project-level aggregated memory
    proj_mem = memories_root / slug / "PROJECT_MEMORY.md"
    assert proj_mem.exists()


def test_cli_dry_run(capsys):
    ret = cli_main(["install-systemd", "--dry-run"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "claudalizer.service" in captured
    assert "claudalizer.path" not in captured
    assert "claudalizer.conf" in captured


def test_ipc_waybar_status(tmp_path):
    status_file = tmp_path / "status.json"
    emit_waybar_signal(status_file=status_file, status="extracted", message="Mined 1 session", mined_count=1)
    assert status_file.exists()
    data = json.loads(status_file.read_text(encoding="utf-8"))
    assert data["alt"] == "extracted"
    assert data["count"] == 1


def test_session_with_only_skipped_file_gets_dossier(tmp_path):
    tmp_root = tmp_path / "tmp_claude"
    memories_root = tmp_path / "memories"
    slug = "-home-andrew-AI-claudalizer"
    session_id = "skipped-only-session"

    scratchpad_dir = tmp_root / slug / session_id / "scratchpad"
    scratchpad_dir.mkdir(parents=True)
    (scratchpad_dir / "big.txt").write_bytes(b"a" * (miner_module.MAX_SCRATCHPAD_FILE_BYTES + 1))

    miner = SessionMiner(
        tmp_root=tmp_root,
        claude_projects=tmp_path / "projects",
        memories_root=memories_root,
        lock_file=tmp_path / "miner.lock",
    )
    dossiers = miner.scan_and_mine(debounce=False)
    assert len(dossiers) == 1

    dossier_json = memories_root / slug / session_id / "dossier.json"
    assert dossier_json.exists()
    for data in (dossiers[0].to_dict(), json.loads(dossier_json.read_text(encoding="utf-8"))):
        assert len(data["skipped_files"]) == 1
        assert data["skipped_files"][0]["reason"] == "oversized"
        assert data["stats"]["skipped_count"] == 1
        assert data["scratchpad_files"] == []
