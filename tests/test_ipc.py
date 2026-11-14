import json
import subprocess
from pathlib import Path

import pytest

import claudalizer.ipc as ipc


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("WAYLAND_DISPLAY", "SWAYSOCK", "HYPRLAND_INSTANCE_SIGNATURE"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _fake_which(found):
    def which(name):
        return found.get(name)
    return which


def test_sway_dispatch_when_swaysock_present(clean_env, monkeypatch):
    clean_env.setenv("WAYLAND_DISPLAY", "wayland-1")
    clean_env.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.1000.1.sock")
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"swaymsg": "/usr/bin/swaymsg"}))
    monkeypatch.setattr(ipc, "emit_waybar_signal", lambda **kwargs: None)
    calls = []
    monkeypatch.setattr(ipc.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    assert ipc.dispatch_wm_hook("idle", {"message": "done"}) is True
    assert calls == [["swaymsg", "-q", "--", "nop claudalizer idle"]]


def test_hyprland_dispatch(clean_env, monkeypatch):
    clean_env.setenv("WAYLAND_DISPLAY", "wayland-1")
    clean_env.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123")
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"hyprctl": "/usr/bin/hyprctl"}))
    monkeypatch.setattr(ipc, "emit_waybar_signal", lambda **kwargs: None)
    calls = []
    monkeypatch.setattr(ipc.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    assert ipc.dispatch_wm_hook("extracted", {"message": "hi"}) is True
    assert calls == []


def test_headless_environment_no_crash(clean_env, monkeypatch, tmp_path):
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({}))
    status_file = tmp_path / "status.json"

    assert ipc.detect_compositor() is None
    assert ipc.send_notification("title", "body") is False
    ipc.emit_waybar_signal(status_file=status_file, status="idle", message="x", mined_count=0)
    assert status_file.exists()
    assert ipc.dispatch_wm_hook("idle", {"message": "x"}) is False
    ipc.notify_extraction("-home-user-proj", "abcdef12-3456", 1, 0)


def test_sway_glob_fallback_requires_socket(clean_env, monkeypatch, tmp_path):
    clean_env.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"swaymsg": "/usr/bin/swaymsg"}))
    # The fallback builds Path(f"/run/user/<uid>"); point that at tmp_path.
    monkeypatch.setattr(ipc, "Path", lambda _p: tmp_path)

    assert ipc.detect_compositor() != "sway"


def test_sway_glob_fallback_with_socket(clean_env, monkeypatch, tmp_path):
    clean_env.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"swaymsg": "/usr/bin/swaymsg"}))
    monkeypatch.setattr(ipc, "Path", lambda _p: tmp_path)
    (tmp_path / "sway-ipc.0.sock").touch()

    assert ipc.detect_compositor() == "sway"


_real_signal_waybar = ipc._signal_waybar


def test_waybar_refresh_signal_sent(monkeypatch, tmp_path):
    monkeypatch.setattr(ipc, "_signal_waybar", _real_signal_waybar)
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"pkill": "/usr/bin/pkill"}))
    calls = []
    monkeypatch.setattr(ipc.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))

    ipc.emit_waybar_signal(status_file=tmp_path / "s.json", status="idle")

    assert calls == [["pkill", "-RTMIN+8", "waybar"]]


def test_waybar_refresh_skipped_without_pkill(monkeypatch, tmp_path):
    monkeypatch.setattr(ipc, "_signal_waybar", _real_signal_waybar)
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({}))
    calls = []
    monkeypatch.setattr(ipc.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))
    status_file = tmp_path / "s.json"

    ipc.emit_waybar_signal(status_file=status_file, status="idle")

    assert calls == []
    assert status_file.exists()


def test_waybar_refresh_failure_is_silent(monkeypatch, tmp_path):
    monkeypatch.setattr(ipc, "_signal_waybar", _real_signal_waybar)
    monkeypatch.setattr(ipc.shutil, "which", _fake_which({"pkill": "/usr/bin/pkill"}))

    def boom(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 2)

    monkeypatch.setattr(ipc.subprocess, "run", boom)
    status_file = tmp_path / "s.json"

    ipc.emit_waybar_signal(status_file=status_file, status="idle")

    assert status_file.exists()


def test_default_status_file_is_redirected_in_tests():
    # The autouse fixture points the default at tmp_path, never at /tmp/claudalizer_status.json.
    assert ipc.DEFAULT_STATUS_FILE != Path("/tmp/claudalizer_status.json")


def test_scan_history_totals_reload_and_retention(tmp_path):
    first = ipc.record_scan(tmp_path, 2, 3, "project one", history_limit=2)
    assert first["total_scans"] == 1
    assert first["total_mined"] == 2
    assert first["latest"]["mined"] == 2
    assert first["latest"]["active"] == 3
    assert first["latest"]["summary"] == "project one"
    assert first["latest"]["timestamp"]
    assert ipc.load_scan_state(tmp_path) == first

    ipc.record_scan(tmp_path, 1, 0, history_limit=2)
    third = ipc.record_scan(tmp_path, 0, 4, history_limit=2)
    assert (third["total_scans"], third["total_mined"]) == (3, 3)
    assert [scan["mined"] for scan in third["history"]] == [1, 0]
    assert ipc.load_scan_state(tmp_path) == third

    fourth = ipc.record_scan(tmp_path, 3, 1, history_limit=0)
    assert fourth["history"] == []
    assert fourth["latest"]["mined"] == 3
    assert (fourth["total_scans"], fourth["total_mined"]) == (4, 6)
    assert ipc.load_scan_state(tmp_path) == fourth


@pytest.mark.parametrize("content", ["{", "null", '[]', '{"total_scans": "bad"}',
                                      '{"total_scans": 1, "total_mined": 1, "history": [null]}'])
def test_scan_state_recovers_from_corruption(tmp_path, content):
    (tmp_path / ipc.SCAN_STATE_FILENAME).write_text(content, encoding="utf-8")
    state = ipc.record_scan(tmp_path, 1, 2)
    assert state["total_scans"] == 1
    assert state["total_mined"] == 1
    assert ipc.load_scan_state(tmp_path) == state


def test_scan_state_and_waybar_are_atomic_and_independent(monkeypatch, tmp_path):
    root = tmp_path / "memories"
    status = tmp_path / "waybar.json"
    replacements = []
    original_replace = ipc.os.replace

    def replace(source, target):
        replacements.append((Path(source), Path(target)))
        assert Path(source).parent == Path(target).parent
        assert json.loads(Path(source).read_text(encoding="utf-8"))
        original_replace(source, target)

    monkeypatch.setattr(ipc.os, "replace", replace)
    state = ipc.record_scan(root, 2, 3, "project")
    ipc.emit_waybar_signal(status_file=status, status="extracted", scan_state=state)
    payload = json.loads(status.read_text(encoding="utf-8"))
    assert "2" in payload["text"] and "3" in payload["text"]
    assert state["latest"]["timestamp"] in payload["tooltip"]
    assert "Last project: project" in payload["tooltip"]
    assert "Total scans: 1 | Total mined: 2" in payload["tooltip"]
    assert "Recent mined scans:" in payload["tooltip"] and "project" in payload["tooltip"]
    assert ipc.load_scan_state(root) == state
    assert [target for _, target in replacements] == [root / ipc.SCAN_STATE_FILENAME, status]
    assert all(not source.exists() for source, _ in replacements)


@pytest.mark.parametrize(
    "active, expected_text",
    [(0, "🧠 0 | 3"), (2, "🧠 2 | 3")],
)
def test_waybar_text_uses_cumulative_mined_and_latest_active(tmp_path, active, expected_text):
    ipc.record_scan(tmp_path, 3, 0)
    state = ipc.record_scan(tmp_path, 0, active)
    status_file = tmp_path / "waybar.json"

    ipc.emit_waybar_signal(status_file=status_file, scan_state=state)

    payload = json.loads(status_file.read_text(encoding="utf-8"))
    assert payload["text"] == expected_text
    assert payload["count"] == 0


def test_waybar_tooltip_orders_latest_project_before_totals_and_limits_useful_history(tmp_path):
    state = ipc.record_scan(tmp_path, 0, 0)
    state["latest"].update(timestamp="current", summary="current-project")
    state["history"] = [
        {"timestamp": f"scan-{i}", "mined": 1 if i % 2 else 0, "active": 0, "summary": f"project-{i}"}
        for i in range(10)
    ]
    status_file = tmp_path / "waybar.json"

    ipc.emit_waybar_signal(status_file=status_file, scan_state=state)

    tooltip = json.loads(status_file.read_text(encoding="utf-8"))["tooltip"]
    assert tooltip.index("Last project: current-project") < tooltip.index("Total scans:")
    history_lines = [line for line in tooltip.splitlines() if line.startswith("scan-")]
    assert len(history_lines) == 3
    assert all("0 mined" not in line for line in history_lines)
    assert [line.split(":", 1)[0] for line in history_lines] == ["scan-9", "scan-7", "scan-5"]
    assert "scan-8" not in tooltip and "scan-6" not in tooltip and "scan-4" not in tooltip


def test_scan_write_failure_preserves_previous_state(monkeypatch, tmp_path):
    previous = ipc.record_scan(tmp_path, 1, 0)

    def fail_replace(source, target):
        raise OSError("write failed")

    monkeypatch.setattr(ipc.os, "replace", fail_replace)
    result = ipc.record_scan(tmp_path, 2, 1)
    assert result["total_scans"] == 2
    assert ipc.load_scan_state(tmp_path) == previous
    assert list(tmp_path.iterdir()) == [tmp_path / ipc.SCAN_STATE_FILENAME]
    ipc.emit_waybar_signal(status_file=tmp_path / "waybar.json", scan_state=result)
    assert not (tmp_path / "waybar.json").exists()


def test_negative_scan_inputs_rejected(tmp_path):
    for kwargs in ({"mined_count": -1, "active_count": 0},
                   {"mined_count": 0, "active_count": -1},
                   {"mined_count": 0, "active_count": 0, "history_limit": -1}):
        with pytest.raises(ValueError):
            ipc.record_scan(tmp_path, **kwargs)
