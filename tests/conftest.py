import pytest

import claudalizer.ipc as ipc


@pytest.fixture(autouse=True)
def _no_real_waybar_signal(monkeypatch):
    """Keep every test from sending a real signal to a running Waybar."""
    monkeypatch.setattr(ipc, "_signal_waybar", lambda: None)
