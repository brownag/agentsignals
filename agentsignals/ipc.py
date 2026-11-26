"""Desktop notification and Wayland compositor IPC hooks for agentsignals."""

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

WAYBAR_SIGNAL = 8


def send_notification(
    title: str,
    body: str,
    urgency: str = "normal",
    app_name: str = "AgentSignals",
    icon: Optional[str] = None,
) -> bool:
    """Send a desktop notification via notify-send if available."""
    notify_send = shutil.which("notify-send")
    if not notify_send:
        return False

    cmd = [notify_send, "-a", app_name, "-u", urgency, title, body]
    if icon:
        cmd.extend(["-i", icon])

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def detect_compositor() -> Optional[str]:
    """Detect whether Sway or Hyprland is currently active under Wayland."""
    if not os.environ.get("WAYLAND_DISPLAY"):
        return None

    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
        return "hyprland"

    if os.environ.get("SWAYSOCK") and shutil.which("swaymsg"):
        return "sway"

    # Fallback checks by binary availability if socket might be set elsewhere
    if shutil.which("swaymsg") and (os.environ.get("SWAYSOCK") or any(Path(f"/run/user/{os.getuid()}").glob("sway-ipc.*.sock"))):
        return "sway"
    if shutil.which("hyprctl") and os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"

    return None


DEFAULT_STATUS_FILE = Path("/tmp/agentsignals_status.json")
SCAN_STATE_FILENAME = "scan_status.json"


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    """Replace a JSON file atomically, using a unique temporary file beside it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
            name = f.name
            json.dump(payload, f)
        os.replace(name, path)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)


def _valid_scan(scan: Any) -> bool:
    return (
        isinstance(scan, dict)
        and isinstance(scan.get("timestamp"), str)
        and all(type(scan.get(key)) is int and scan[key] >= 0 for key in ("mined", "active"))
        and isinstance(scan.get("summary", ""), str)
    )


def load_scan_state(memories_root: Path) -> Dict[str, Any]:
    """Read scan state, returning an empty state if it is missing or corrupt."""
    empty: Dict[str, Any] = {"total_scans": 0, "total_mined": 0, "latest": None, "history": []}
    try:
        with (memories_root / SCAN_STATE_FILENAME).open(encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            return empty
        if not all(type(state.get(k)) is int and state[k] >= 0 for k in ("total_scans", "total_mined")):
            return empty
        if state.get("latest") is not None and not _valid_scan(state["latest"]):
            return empty
        if not isinstance(state.get("history"), list) or not all(_valid_scan(s) for s in state["history"]):
            return empty
        return state
    except (OSError, ValueError, UnicodeError):
        return empty


def record_scan(
    memories_root: Path,
    mined_count: int,
    active_count: int,
    summary: str = "",
    history_limit: int = 50,
) -> Dict[str, Any]:
    """Record one scan and return its state even if persistence is unavailable."""
    if history_limit < 0 or mined_count < 0 or active_count < 0:
        raise ValueError("scan counts and history limit must be non-negative")
    state = load_scan_state(memories_root)
    scan = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mined": mined_count,
        "active": active_count,
        "summary": summary,
    }
    state["total_scans"] += 1
    state["total_mined"] += mined_count
    state["latest"] = scan
    state["history"] = (state["history"] + [scan])[-history_limit:] if history_limit else []
    try:
        _atomic_json_write(memories_root / SCAN_STATE_FILENAME, state)
    except OSError:
        pass
    return state


def emit_waybar_signal(
    status_file: Optional[Path] = None,
    status: str = "idle",
    message: str = "",
    mined_count: int = 0,
    scan_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Write status JSON for custom Waybar / status bar modules.

    status_file defaults to DEFAULT_STATUS_FILE, read at call time, so tests can redirect it.

    Waybar custom module can consume this via:
      "exec": "cat /tmp/agentsignals_status.json"
      "return-type": "json"
    """
    payload: Dict[str, Any] = {
        "text": f"🧠 {mined_count}" if mined_count > 0 else "🧠",
        "alt": status,
        "tooltip": f"AgentSignals: {status}\n{message}" if message else f"AgentSignals: {status}",
        "class": status,
        "count": mined_count,
    }
    if scan_state and scan_state.get("latest"):
        latest = scan_state["latest"]
        active = latest["active"]
        payload["text"] = f"🧠 {active} | {scan_state['total_mined']}"
        lines = [
            f"Last scan: {latest['timestamp']}",
            f"Mined: {latest['mined']} | Active: {active}",
        ]
        summary = latest.get("summary", "").removeprefix("Last project: ")
        if summary:
            lines.append(f"Last project: {summary}")
        lines.append(
            f"Total scans: {scan_state['total_scans']} | Total mined: {scan_state['total_mined']}",
        )
        history = [scan for scan in scan_state["history"] if scan["mined"] > 0][-3:]
        if history:
            lines.append("Recent mined scans:")
            lines.extend(
                f"{scan['timestamp']}: {scan['mined']} mined"
                + (f", {scan['active']} active" if scan["active"] else "")
                + (f" — {scan['summary'].removeprefix('Last project: ')}" if scan.get("summary") else "")
                for scan in reversed(history)
            )
        payload["tooltip"] = "\n".join(lines)
        payload["count"] = latest["mined"]
    if status_file is None:
        status_file = DEFAULT_STATUS_FILE
    try:
        _atomic_json_write(status_file, payload)
    except OSError:
        return
    _signal_waybar()


def _signal_waybar() -> None:
    """Ask Waybar to re-read custom modules that set "signal": WAYBAR_SIGNAL."""
    if not shutil.which("pkill"):
        return
    try:
        subprocess.run(
            ["pkill", f"-RTMIN+{WAYBAR_SIGNAL}", "waybar"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return


def dispatch_wm_hook(
    event: str,
    details: Optional[Dict[str, Any]] = None,
) -> bool:
    """Dispatch status hooks to running Wayland compositor (swaymsg or hyprctl)."""
    compositor = detect_compositor()
    details = details or {}

    mined_count = details.get("mined_count", 0)
    message = details.get("message", event)
    emit_waybar_signal(status=event, message=message, mined_count=mined_count)

    if compositor == "sway":
        cmd = ["swaymsg"]
        # Mode or bar signal or user message
        # swaymsg doesn't have an arbitrary broadcast command, but we can send a custom command or nop
        # We can run swaymsg -q -- nop "agentsignals: <event>"
        try:
            subprocess.run(
                [cmd[0], "-q", "--", f"nop AgentSignals {event}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            return True
        except (subprocess.SubprocessError, OSError):
            return False

    elif compositor == "hyprland":
        return True

    return False
