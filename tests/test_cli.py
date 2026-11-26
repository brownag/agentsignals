import json
from types import SimpleNamespace

import pytest

import agentsignals.cli as cli
import agentsignals.ipc as ipc


def _args(tmp_path, command, *options):
    args = cli.build_parser().parse_args([command, *options])
    args.tmp_root = str(tmp_path / "tmp_claude")
    args.claude_projects = str(tmp_path / "projects")
    args.memories_root = str(tmp_path / "memories")
    args.lock_file = str(tmp_path / "lock")
    args.auto_distill = False
    return args


def _fake_miner(batches, active=()):
    class FakeMiner:
        def __init__(self, **kwargs):
            self.skipped = {"active": active, "up_to_date": 0, "no_content": 0}
            self.batches = iter(batches)

        def scan_and_mine(self, **kwargs):
            return next(self.batches)

    return FakeMiner


def _dossier(session_id="abc12345"):
    return SimpleNamespace(
        slug="-home-andrew-AI-claudalizer",
        session_id=session_id,
        tool_errors=[],
        scratchpad_files=["notes.md"],
    )


@pytest.mark.parametrize("command", ["scan", "watch"])
def test_parser_options(command):
    parser = cli.build_parser()
    defaults = parser.parse_args([command])
    assert defaults.notify is False
    assert defaults.history_limit == 50
    args = parser.parse_args([command, "--notify", "--history-limit", "0"])
    assert args.notify is True
    assert args.history_limit == 0
    with pytest.raises(SystemExit):
        parser.parse_args([command, "--history-limit", "-1"])


def test_watch_auto_distill_can_be_turned_off():
    parser = cli.build_parser()
    assert parser.parse_args(["watch"]).auto_distill is True
    assert parser.parse_args(["watch", "--auto-distill"]).auto_distill is True
    assert parser.parse_args(["watch", "--no-auto-distill"]).auto_distill is False


@pytest.mark.parametrize("notify", [False, True])
def test_scan_records_batch_and_notifies_once(tmp_path, monkeypatch, notify):
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([[_dossier(), _dossier("second")]], ["a", "b"]))
    notifications = []
    monkeypatch.setattr(cli, "send_notification", lambda *args: notifications.append(args))
    args = _args(tmp_path, "scan", "--history-limit", "1")
    args.notify = notify

    assert cli.handle_scan(args) == 0
    state = ipc.load_scan_state(tmp_path / "memories")
    assert state["total_scans"] == 1
    assert state["total_mined"] == 2
    assert state["latest"]["active"] == 2
    assert state["latest"]["mined"] == 2
    assert state["latest"]["summary"]
    assert len(state["history"]) == 1
    status = json.loads(ipc.DEFAULT_STATUS_FILE.read_text())
    assert status["count"] == 2
    assert status["text"] == "🧠 2 | 2"
    assert len(notifications) == int(notify)
    if notify:
        assert "2" in notifications[0][1]


def test_empty_scan_records_latest_and_zero_history(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([[]], ["active"]))
    notifications = []
    monkeypatch.setattr(cli, "send_notification", lambda *args: notifications.append(args))
    args = _args(tmp_path, "scan", "--notify", "--history-limit", "0")
    ipc.record_scan(tmp_path / "memories", 3, 0)

    assert cli.handle_scan(args) == 0
    state = ipc.load_scan_state(tmp_path / "memories")
    assert state["total_scans"] == 2
    assert state["total_mined"] == 3
    assert state["latest"]["mined"] == 0
    assert state["latest"]["active"] == 1
    assert state["history"] == []
    assert json.loads(ipc.DEFAULT_STATUS_FILE.read_text())["text"] == "🧠 1 | 3"
    assert notifications == []


@pytest.mark.parametrize("notify", [False, True])
def test_watch_records_each_batch_and_preserves_latest_on_shutdown(tmp_path, monkeypatch, notify):
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([[_dossier(), _dossier("second")], []], ["active"]))
    notifications = []
    monkeypatch.setattr(cli, "send_notification", lambda *args: notifications.append(args))
    # Model lifecycle hooks writing their own status, without contacting a compositor.
    monkeypatch.setattr(cli, "dispatch_wm_hook", lambda event, details: ipc.emit_waybar_signal(status=event))
    sleeps = iter([None, KeyboardInterrupt()])

    def sleep(_):
        result = next(sleeps)
        if isinstance(result, BaseException):
            raise result

    monkeypatch.setattr(cli.time, "sleep", sleep)
    args = _args(tmp_path, "watch", "--history-limit", "1")
    args.notify = notify

    assert cli.handle_watch(args) == 0
    state = ipc.load_scan_state(tmp_path / "memories")
    assert state["total_scans"] == 2
    assert state["total_mined"] == 2
    assert state["latest"]["mined"] == 0
    assert state["latest"]["active"] == 1
    assert len(state["history"]) == 1
    assert json.loads(ipc.DEFAULT_STATUS_FILE.read_text())["text"] == "🧠 1 | 2"
    assert len(notifications) == int(notify)


def _kinds(sources):
    return [type(s).__name__ for s in sources]


def test_source_flag_limits_sources(tmp_path):
    args = cli.build_parser().parse_args(["--source", "claude", "scan"])
    assert _kinds(cli.build_sources(args, watch=False)) == ["ClaudeCodeSource"]
    args = cli.build_parser().parse_args(["scan"])
    assert _kinds(cli.build_sources(args, watch=False)) == ["ClaudeCodeSource", "OpencodeSource"]
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--source", "bogus", "scan"])


def test_watch_builds_opencode_source_with_precheck(tmp_path, monkeypatch):
    seen = {}

    class FakeMiner:
        def __init__(self, **kwargs):
            seen["sources"] = kwargs["sources"]
            self.skipped = {}

        def scan_and_mine(self, **kwargs):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "SessionMiner", FakeMiner)
    monkeypatch.setattr(cli, "dispatch_wm_hook", lambda *a, **k: None)
    args = _args(tmp_path, "watch")
    try:
        cli.handle_watch(args)
    except (KeyboardInterrupt, SystemExit):
        pass
    oc = [s for s in seen["sources"] if type(s).__name__ == "OpencodeSource"]
    assert len(oc) == 1 and oc[0].skip_if_unchanged is True
    scan_args = _args(tmp_path, "scan")
    oc = [s for s in cli.build_sources(scan_args, watch=False) if type(s).__name__ == "OpencodeSource"]
    assert oc[0].skip_if_unchanged is False


def test_both_sources_share_project_memory(tmp_path, fake_llm):
    import os
    import time

    from agentsignals.distiller import MemoryDistiller
    from agentsignals.miner import SessionMiner
    from agentsignals.sources.opencode import slug_for_directory
    from tests.opencode_fixture import OpencodeDB

    proj_dir = str(tmp_path / "work" / "proj")
    slug = slug_for_directory(proj_dir)
    tmp_root = tmp_path / "tmp_claude"
    projects = tmp_path / "projects"
    scratch = tmp_root / slug / "claude-sess" / "scratchpad"
    scratch.mkdir(parents=True)
    (scratch / "probe.py").write_text("# probe", encoding="utf-8")
    (projects / slug).mkdir(parents=True)
    (projects / slug / "claude-sess.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Claude Code prompt long enough"}}) + "\n",
        encoding="utf-8",
    )
    old = time.time() - 100
    for p in (scratch / "probe.py", scratch, scratch.parent, tmp_root / slug):
        os.utime(p, (old, old))

    t = int((time.time() - 3600) * 1000)
    with OpencodeDB(tmp_path / "oc.db") as db:
        db.add_session("oc-sess", proj_dir, time_busy=t - 1, time_idle=t, time_created=t, time_updated=t)
        db.add_message("oc-sess", "user", {"text": "please do the opencode thing now"}, time_updated=t)

    memories = tmp_path / "memories"
    args = cli.build_parser().parse_args(
        ["--tmp-root", str(tmp_root), "--claude-projects", str(projects),
         "--opencode-db", str(tmp_path / "oc.db"), "scan"]
    )
    miner = SessionMiner(
        tmp_root=tmp_root, claude_projects=projects, memories_root=memories,
        lock_file=tmp_path / "lock", sources=cli.build_sources(args, watch=False),
    )
    assert len(miner.scan_and_mine(debounce=False)) == 2
    MemoryDistiller(memories_root=memories).distill_all(llm_endpoint="http://127.0.0.1:9/v1")
    text = (memories / slug / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert text.count("## Session") == 2


def test_distill_without_endpoint_fails_and_writes_nothing(tmp_path, monkeypatch, caplog):
    monkeypatch.delenv("AGENTSIGNALS_LLM_ENDPOINT", raising=False)
    sess = tmp_path / "memories" / "-slug-a" / "abcdef12-3456"
    sess.mkdir(parents=True)
    (sess / "dossier.json").write_text(json.dumps({"slug": "-slug-a", "user_prompts": ["Fix the build please"]}), encoding="utf-8")
    args = _args(tmp_path, "distill", "--force")

    assert cli.handle_distill(args) == 2
    assert "No LLM endpoint set" in caplog.text
    assert not (sess / "memory.md").exists()


def test_watch_without_endpoint_does_not_distill(tmp_path, monkeypatch, caplog):
    monkeypatch.delenv("AGENTSIGNALS_LLM_ENDPOINT", raising=False)
    dossier = SimpleNamespace(slug="-slug-a", session_id="s1", tool_errors=[], scratchpad_files=[])
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([[dossier]]))
    calls = []
    monkeypatch.setattr(cli.MemoryDistiller, "distill_session", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(cli, "dispatch_wm_hook", lambda *a: None)

    def sleep(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.time, "sleep", sleep)
    args = _args(tmp_path, "watch")
    args.auto_distill = True

    assert cli.handle_watch(args) == 0
    assert calls == []
    assert "No LLM endpoint set" in caplog.text


def test_no_git_flag_disables_repo(tmp_path):
    root = str(tmp_path / "memories")
    parser = cli.build_parser()
    assert cli.build_repo(parser.parse_args(["--memories-root", root, "scan"])).enabled is True
    assert cli.build_repo(parser.parse_args(["--memories-root", root, "--no-git", "scan"])).enabled is False


def test_new_environment_variables_precede_legacy_aliases(monkeypatch):
    monkeypatch.setenv("AGENTSIGNALS_LLM_ENDPOINT", "https://new.example")
    monkeypatch.setenv("CLAUDALIZER_LLM_ENDPOINT", "https://old.example")
    monkeypatch.setenv("AGENTSIGNALS_LLM_MODEL", "new-model")
    monkeypatch.setenv("CLAUDALIZER_LLM_MODEL", "old-model")

    endpoint, model = cli.resolve_llm_settings(SimpleNamespace(llm_endpoint=None, llm_model="llama3"))
    assert endpoint == "https://new.example"
    assert model == "new-model"


def test_legacy_cli_entrypoint_uses_deprecation_program_name(monkeypatch):
    called = []
    monkeypatch.setattr(cli, "handle_scan", lambda args: called.append(args.command) or 0)

    assert cli.legacy_main(["scan"]) == 0
    assert called == ["scan"]


def test_watch_passes_repo_and_min_remine(tmp_path, monkeypatch):
    seen = {}

    class FakeMiner:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def scan_and_mine(self, **kwargs):
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "SessionMiner", FakeMiner)
    args = _args(tmp_path, "watch")
    args.source = ["claude"]
    assert cli.handle_watch(args) == 0

    assert seen["min_remine_seconds"] == 60.0
    assert seen["repo"].root == tmp_path / "memories"
    assert seen["repo"].enabled is True


def test_scan_then_distill_makes_scan_and_distill_commits(tmp_path, fake_llm):
    import os
    import subprocess
    import time

    tmp_root = tmp_path / "tmp_claude"
    projects = tmp_path / "projects"
    slug = "-home-andrew-AI-demo"
    scratch = tmp_root / slug / "cli-sess" / "scratchpad"
    scratch.mkdir(parents=True)
    (scratch / "probe.py").write_text("# probe", encoding="utf-8")
    (projects / slug).mkdir(parents=True)
    (projects / slug / "cli-sess.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "Distill this after the scan"}}) + "\n",
        encoding="utf-8",
    )
    old = time.time() - 100
    for p in (scratch / "probe.py", scratch, scratch.parent, tmp_root / slug, projects / slug / "cli-sess.jsonl"):
        os.utime(p, (old, old))

    args = _args(tmp_path, "scan", "--no-debounce", "--auto-distill",
                 "--llm-endpoint", "http://127.0.0.1:9/v1")
    args.source = ["claude"]
    args.auto_distill = True
    args.tmp_root = str(tmp_root)
    args.claude_projects = str(projects)
    assert cli.handle_scan(args) == 0

    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subjects = subprocess.run(
        ["git", "log", "--format=%s"], cwd=tmp_path / "memories", env=env,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert subjects == ["distill: 1 distilled", "scan: 1 mined", "baseline: existing memories"]
