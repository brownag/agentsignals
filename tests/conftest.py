import pytest

import claudalizer.ipc as ipc


@pytest.fixture(autouse=True)
def _no_real_waybar_signal(monkeypatch, tmp_path):
    """Keep every test from signalling a running Waybar or writing the real Waybar status file."""
    monkeypatch.setattr(ipc, "_signal_waybar", lambda: None)
    monkeypatch.setattr(ipc, "DEFAULT_STATUS_FILE", tmp_path / "claudalizer_status.json")


@pytest.fixture(autouse=True)
def _no_real_opencode_db(monkeypatch, tmp_path):
    """Point opencode lookups at paths that do not exist so tests never read the live database."""
    monkeypatch.setenv("OPENCODE_DB", str(tmp_path / "no-opencode" / "opencode.db"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
