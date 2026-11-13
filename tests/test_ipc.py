import subprocess

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
    assert calls == [
        ["hyprctl", "notify", "0", "3000", "rgb(ebcb8b)", "claudalizer: hi"],
    ]


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
