import pytest

import claudalizer.ipc as ipc


@pytest.fixture(autouse=True)
def _no_real_waybar_signal(monkeypatch, tmp_path):
    """Keep every test from signalling a running Waybar or writing the real Waybar status file."""
    monkeypatch.setattr(ipc, "_signal_waybar", lambda: None)
    monkeypatch.setattr(ipc, "DEFAULT_STATUS_FILE", tmp_path / "claudalizer_status.json")
