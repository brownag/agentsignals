from types import SimpleNamespace

import claudalizer.cli as cli


def _scan_args(tmp_path):
    args = cli.build_parser().parse_args(["scan"])
    args.tmp_root = str(tmp_path / "tmp_claude")
    args.claude_projects = str(tmp_path / "projects")
    args.memories_root = str(tmp_path / "memories")
    args.lock_file = str(tmp_path / "lock")
    args.auto_distill = False
    args.notify = False
    return args


def _fake_miner(dossiers):
    class FakeMiner:
        def __init__(self, **kwargs):
            pass

        def scan_and_mine(self, **kwargs):
            return dossiers

    return FakeMiner


def _dossier():
    return SimpleNamespace(
        slug="-home-andrew-AI-claudalizer",
        session_id="abc12345",
        tool_errors=[],
        scratchpad_files=["notes.md"],
    )


def test_scan_without_notify_writes_status(tmp_path, monkeypatch):
    calls = []
    notified = []
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([_dossier()]))
    monkeypatch.setattr(cli, "emit_waybar_signal", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(cli, "notify_extraction", lambda *a, **k: notified.append(a))

    assert cli.handle_scan(_scan_args(tmp_path)) == 0

    assert any(c.get("status") == "extracted" for c in calls)
    assert calls[-1].get("status") == "idle"
    assert notified == []


def test_scan_no_sessions_writes_idle(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "SessionMiner", _fake_miner([]))
    monkeypatch.setattr(cli, "emit_waybar_signal", lambda **kwargs: calls.append(kwargs))

    assert cli.handle_scan(_scan_args(tmp_path)) == 0

    assert [c.get("status") for c in calls] == ["idle"]
    assert calls[0]["message"] == "No new sessions"
