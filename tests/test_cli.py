import json
from types import SimpleNamespace

import pytest

import claudalizer.cli as cli
import claudalizer.ipc as ipc


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
    assert "active 2" in status["text"]
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
    assert "active 1" in json.loads(ipc.DEFAULT_STATUS_FILE.read_text())["text"]
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
    assert "active 1" in json.loads(ipc.DEFAULT_STATUS_FILE.read_text())["text"]
    assert len(notifications) == int(notify)
