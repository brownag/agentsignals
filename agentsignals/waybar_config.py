"""Add the agentsignals module to the user's Waybar config during install.

The config is JSONC (comments allowed), so this is a text edit, not a parse and rewrite.
Every edit is checked by re-parsing the result with `//` comment lines removed. If the
check fails, nothing is written.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

MODULE_NAME = "custom/agent-signals"
STATUS_FILE = "/tmp/claudalizer_status.json"

MODULE_BLOCK = f'''    "{MODULE_NAME}": {{
        "format": "{{}}",
        "return-type": "json",
        "exec": "cat {STATUS_FILE} 2>/dev/null || echo '{{\\"text\\":\\"🧠\\"}}'",
        "interval": 3,
        "signal": 8,
        "tooltip": true
    }}'''

CONFIG_CANDIDATES = (
    Path(".config") / "waybar" / "config.jsonc",
    Path(".config") / "waybar" / "config",
)

_MODULES_RIGHT_RE = re.compile(r'"modules-right"\s*:\s*\[')


def find_waybar_config(home: Optional[Path] = None) -> Optional[Path]:
    """Return the first existing Waybar config under the home directory, or None."""
    base = home or Path.home()
    for rel in CONFIG_CANDIDATES:
        path = base / rel
        if path.is_file():
            return path
    return None


def _strip_line_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


def _insert_module(text: str) -> Optional[str]:
    """Return the edited config text, or None if the file shape is not one this edit handles."""
    match = _MODULES_RIGHT_RE.search(text)
    if not match:
        return None

    # 1. Add the name to modules-right, right after the opening bracket.
    list_start = match.end()
    after = text[list_start:].lstrip()
    needs_comma = not after.startswith("]")
    name_entry = f'"{MODULE_NAME}"' + ("," if needs_comma else "")
    edited = text[:list_start] + "\n        " + name_entry + text[list_start:]

    # 2. Add the module definition before the final closing brace of the top-level object.
    close = edited.rfind("}")
    if close == -1:
        return None
    head = edited[:close].rstrip()
    if not head.endswith(("{", ",")):
        head += ","
    edited = head + "\n" + MODULE_BLOCK + "\n" + edited[close:]

    # 3. Validate: the result must still parse once line comments are removed.
    try:
        json.loads(_strip_line_comments(edited))
    except ValueError:
        return None
    return edited


def patch_waybar_config(config_path: Optional[Path], dry_run: bool = False) -> str:
    """Add the agentsignals module to a Waybar config.

    Returns one of:
      "missing"  no config file given or it does not exist
      "present"  the module is already in the config
      "added"    the module was written (a backup was saved next to it)
      "would-add" dry run: the module would be written
      "manual"   the config shape was not recognised or did not validate; nothing written
    """
    if config_path is None or not config_path.is_file():
        return "missing"

    text = config_path.read_text(encoding="utf-8")
    if f'"{MODULE_NAME}"' in text or '"custom/claudalizer"' in text:
        return "present"
    edited = _insert_module(text)
    if edited is None:
        return "manual"
    if dry_run:
        return "would-add"

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(config_path.name + f".agent-signals-bak-{stamp}")
    shutil.copy2(config_path, backup)
    config_path.write_text(edited, encoding="utf-8")
    return "added"


def manual_snippet() -> str:
    """The block to paste by hand, for the 'manual' and 'missing' cases."""
    return (
        f'Add "{MODULE_NAME}" to "modules-right", and this block at the top level:\n'
        + MODULE_BLOCK
    )
