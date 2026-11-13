import json

from claudalizer.waybar_config import (
    MODULE_NAME,
    find_waybar_config,
    manual_snippet,
    patch_waybar_config,
)

SAMPLE = """{
    // top-level comment with a URL https://example.com
    "layer": "top",
    "modules-left": ["sway/workspaces"],
    "modules-right": [
        "custom/help",
        "battery",
        "network"
    ],
    "battery": {
        "format": "{capacity}%"
    }
}
"""


def _parse(text):
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("//")]
    return json.loads("\n".join(lines))


def test_adds_module_to_modules_right_and_definition(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8")

    assert patch_waybar_config(cfg) == "added"

    data = _parse(cfg.read_text(encoding="utf-8"))
    assert MODULE_NAME in data["modules-right"]
    assert data["modules-right"][0] == MODULE_NAME
    assert data["custom/claudalizer"]["signal"] == 8
    assert data["custom/claudalizer"]["return-type"] == "json"
    assert data["battery"]["format"] == "{capacity}%"
    # The user's comment survives the edit.
    assert "top-level comment" in cfg.read_text(encoding="utf-8")


def test_backup_is_written_with_original_content(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8")

    patch_waybar_config(cfg)

    backups = list(tmp_path.glob("config.jsonc.claudalizer-bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == SAMPLE


def test_second_run_is_a_no_op(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8")
    patch_waybar_config(cfg)
    after_first = cfg.read_text(encoding="utf-8")

    assert patch_waybar_config(cfg) == "present"
    assert cfg.read_text(encoding="utf-8") == after_first
    assert len(list(tmp_path.glob("config.jsonc.claudalizer-bak-*"))) == 1


def test_dry_run_writes_nothing(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8")

    assert patch_waybar_config(cfg, dry_run=True) == "would-add"
    assert cfg.read_text(encoding="utf-8") == SAMPLE
    assert not list(tmp_path.glob("*.claudalizer-bak-*"))


def test_empty_modules_right_list(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text('{\n  "modules-right": []\n}\n', encoding="utf-8")

    assert patch_waybar_config(cfg) == "added"
    data = _parse(cfg.read_text(encoding="utf-8"))
    assert data["modules-right"] == [MODULE_NAME]


def test_trailing_comma_config_is_manual_and_untouched(tmp_path):
    cfg = tmp_path / "config.jsonc"
    body = '{\n  "modules-right": [\n    "battery",\n  ]\n}\n'
    cfg.write_text(body, encoding="utf-8")

    assert patch_waybar_config(cfg) == "manual"
    assert cfg.read_text(encoding="utf-8") == body


def test_no_modules_right_is_manual_and_untouched(tmp_path):
    cfg = tmp_path / "config.jsonc"
    body = '{\n  "modules-left": []\n}\n'
    cfg.write_text(body, encoding="utf-8")

    assert patch_waybar_config(cfg) == "manual"
    assert cfg.read_text(encoding="utf-8") == body
    assert not list(tmp_path.glob("*.claudalizer-bak-*"))


def test_missing_config(tmp_path):
    assert patch_waybar_config(tmp_path / "nope.jsonc") == "missing"
    assert patch_waybar_config(None) == "missing"


def test_find_prefers_jsonc_then_plain(tmp_path):
    waybar = tmp_path / ".config" / "waybar"
    waybar.mkdir(parents=True)
    (waybar / "config").write_text("{}", encoding="utf-8")
    assert find_waybar_config(tmp_path) == waybar / "config"

    (waybar / "config.jsonc").write_text("{}", encoding="utf-8")
    assert find_waybar_config(tmp_path) == waybar / "config.jsonc"
    assert find_waybar_config(tmp_path / "elsewhere") is None


def test_generated_exec_decodes_to_status_fallback(tmp_path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(SAMPLE, encoding="utf-8")
    patch_waybar_config(cfg)

    exec_cmd = _parse(cfg.read_text(encoding="utf-8"))["custom/claudalizer"]["exec"]
    assert exec_cmd.startswith("cat /tmp/claudalizer_status.json")
    assert "🧠" in exec_cmd
    assert '{"text":"🧠"}' in exec_cmd.replace("\\", "")


def test_manual_snippet_mentions_module():
    snippet = manual_snippet()
    assert MODULE_NAME in snippet
    assert '"signal": 8' in snippet
