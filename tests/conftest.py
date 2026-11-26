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


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the LLM call with a canned three-section reply that echoes each failed command.

    Distillation has no offline fallback, so any test that expects a memory.md needs this
    fixture and an llm_endpoint. Returns the list of prompts the fake received.
    """
    import claudalizer.distiller as distiller

    prompts = []

    def _reply(prompt, **_kwargs):
        prompts.append(prompt)
        commands = [ln for ln in prompt.splitlines() if ln.startswith("Command/Input:")]
        return "\n".join(
            ["### 1. Tool / Skill Friction", *(f"- {c}" for c in commands or ["None."]), "",
             "### 2. Blind Alleys & Discarded Spikes", "- None.", "",
             "### 3. Directives for CLAUDE.md", "- None."]
        )

    monkeypatch.setattr(distiller, "call_llm_completion", _reply)
    return prompts
