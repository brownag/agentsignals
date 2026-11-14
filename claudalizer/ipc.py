"""Desktop notification and Wayland compositor IPC hooks for claudalizer."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

WAYBAR_SIGNAL = 8


def send_notification(
    title: str,
    body: str,
    urgency: str = "normal",
    app_name: str = "claudalizer",
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


DEFAULT_STATUS_FILE = Path("/tmp/claudalizer_status.json")


def emit_waybar_signal(
    status_file: Optional[Path] = None,
    status: str = "idle",
    message: str = "",
    mined_count: int = 0,
) -> None:
    """Write status JSON for custom Waybar / status bar modules.

    status_file defaults to DEFAULT_STATUS_FILE, read at call time, so tests can redirect it.

    Waybar custom module can consume this via:
      "exec": "cat /tmp/claudalizer_status.json"
      "return-type": "json"
    """
    payload: Dict[str, Any] = {
        "text": f"🧠 {mined_count}" if mined_count > 0 else "🧠",
        "alt": status,
        "tooltip": f"Claudalizer: {status}\n{message}" if message else f"Claudalizer: {status}",
        "class": status,
        "count": mined_count,
    }
    if status_file is None:
        status_file = DEFAULT_STATUS_FILE
    try:
        status_file.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write via temp file
        temp_file = status_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        temp_file.replace(status_file)
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
        # We can run swaymsg -q -- nop "claudalizer: <event>"
        try:
            subprocess.run(
                [cmd[0], "-q", "--", f"nop claudalizer {event}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            return True
        except (subprocess.SubprocessError, OSError):
            return False

    elif compositor == "hyprland":
        # hyprctl dispatch can be used to send a notification or custom event
        try:
            # hyprctl notify: [icon] [time_ms] [color] [message]
            color = "rgb(88c0d0)" if event == "idle" else "rgb(ebcb8b)"
            time_ms = 3000
            msg = f"claudalizer: {message}"
            subprocess.run(
                ["hyprctl", "notify", "0", str(time_ms), color, msg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                check=False,
            )
            return True
        except (subprocess.SubprocessError, OSError):
            return False

    return False


def notify_extraction(slug: str, session_id: str, scratchpad_files: int, error_count: int) -> None:
    """Convenience helper to dispatch notifications and WM hooks when a session is mined."""
    title = f"Claudalizer Mined: {slug}"
    body = f"Session {session_id[:8]}... captured:\n• {scratchpad_files} scratchpad files\n• {error_count} behavioral signals"
    send_notification(title, body)
    dispatch_wm_hook("extracted", {
        "slug": slug,
        "session_id": session_id,
        "scratchpad_files": scratchpad_files,
        "error_count": error_count,
        "message": f"Mined {slug} ({error_count} errors)",
    })
