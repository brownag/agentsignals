"""Command-line interface for claudalizer."""

import argparse
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from claudalizer.distiller import MemoryDistiller
from claudalizer.ipc import dispatch_wm_hook, emit_waybar_signal, notify_extraction, send_notification
from claudalizer.waybar_config import find_waybar_config, manual_snippet, patch_waybar_config
from claudalizer.miner import (
    DEFAULT_CLAUDE_PROJECTS,
    DEFAULT_LOCK_FILE,
    DEFAULT_MEMORIES_ROOT,
    DEFAULT_TMP_ROOT,
    SessionMiner,
    file_lock,
)

logger = logging.getLogger("claudalizer")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _write_mined_status(dossiers) -> None:
    """Show the mined result, then settle back to idle so the status never sticks."""
    now = datetime.now().strftime("%H:%M")
    if not dossiers:
        emit_waybar_signal(status="idle", message="No new sessions", mined_count=0)
        return
    slug = dossiers[-1].slug
    emit_waybar_signal(status="extracted", message=f"Mined {slug} at {now}", mined_count=len(dossiers))
    emit_waybar_signal(status="idle", message=f"Last mined {slug} at {now}", mined_count=0)


def resolve_llm_settings(args: argparse.Namespace) -> Tuple[Optional[str], str]:
    """Endpoint and model for distillation. The flag wins; otherwise the environment (read at call time).

    --llm-model defaults to "llama3". That default counts as not given, so CLAUDALIZER_LLM_MODEL
    (default "local") applies.
    """
    endpoint = getattr(args, "llm_endpoint", None) or os.environ.get("CLAUDALIZER_LLM_ENDPOINT") or None
    model = getattr(args, "llm_model", None) or "llama3"
    if model == "llama3":
        model = os.environ.get("CLAUDALIZER_LLM_MODEL", "local")
    return endpoint, model


def format_skip_summary(skipped: dict) -> str:
    """One-line account of sessions a scan did not mine, plus the still-active ones by name."""
    active = skipped.get("active", [])
    lines = [
        f"Skipped: {len(active)} active (still changing; picked up on a later scan), "
        f"{skipped.get('up_to_date', 0)} already up to date, "
        f"{skipped.get('no_content', 0)} with no content."
    ]
    for name in active:
        lines.append(f"  • still active: {name}")
    return "\n".join(lines)


def handle_scan(args: argparse.Namespace) -> int:
    miner = SessionMiner(
        tmp_root=Path(args.tmp_root),
        claude_projects=Path(args.claude_projects),
        memories_root=Path(args.memories_root),
        lock_file=Path(args.lock_file),
    )

    logger.info(f"Scanning {args.tmp_root}...")
    dossiers = miner.scan_and_mine(
        debounce=not args.no_debounce,
        force=args.force,
        target_slug=args.project,
    )

    logger.info(f"Scan complete. Mined {len(dossiers)} session(s).")
    for d in dossiers:
        print(f"• Mined {d.slug}/{d.session_id} -> {len(d.tool_errors)} error(s), {len(d.scratchpad_files)} scratchpad file(s)")
        if args.notify:
            notify_extraction(d.slug, d.session_id, len(d.scratchpad_files), len(d.tool_errors))
    print(format_skip_summary(miner.skipped))
    _write_mined_status(dossiers)

    if args.auto_distill and dossiers:
        logger.info("Running automatic distillation on mined sessions...")
        distiller = MemoryDistiller(memories_root=Path(args.memories_root))
        for d in dossiers:
            distiller.distill_session(
                d.slug,
                d.session_id,
                llm_endpoint=resolve_llm_settings(args)[0],
                llm_model=resolve_llm_settings(args)[1],
                force=args.force,
            )

    return 0


def handle_distill(args: argparse.Namespace) -> int:
    distiller = MemoryDistiller(memories_root=Path(args.memories_root))
    logger.info(f"Distilling sessions from {args.memories_root}...")

    distilled = distiller.distill_all(
        target_slug=args.project,
        llm_endpoint=resolve_llm_settings(args)[0],
        llm_model=resolve_llm_settings(args)[1],
        force=args.force,
    )

    logger.info(f"Distillation complete. Processed {len(distilled)} session memory block(s).")
    for path in distilled:
        print(f"• Generated: {path}")

    return 0


def handle_watch(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    logger.info(f"Starting claudalizer watch loop on {args.tmp_root} (poll interval: {args.interval}s)...")
    dispatch_wm_hook("watching", {"message": "Watching for sessions"})

    miner = SessionMiner(
        tmp_root=Path(args.tmp_root),
        claude_projects=Path(args.claude_projects),
        memories_root=Path(args.memories_root),
        lock_file=Path(args.lock_file),
    )
    distiller = MemoryDistiller(memories_root=Path(args.memories_root)) if args.auto_distill else None

    try:
        while True:
            try:
                dossiers = miner.scan_and_mine(debounce=True, force=False, target_slug=args.project)
                if dossiers:
                    for d in dossiers:
                        logger.info(f"Mined {d.slug}/{d.session_id} ({len(d.tool_errors)} errors, {len(d.scratchpad_files)} files)")
                        if args.notify:
                            notify_extraction(d.slug, d.session_id, len(d.scratchpad_files), len(d.tool_errors))
                        if distiller:
                            distiller.distill_session(
                                d.slug,
                                d.session_id,
                                llm_endpoint=resolve_llm_settings(args)[0],
                                llm_model=resolve_llm_settings(args)[1],
                            )
                    _write_mined_status(dossiers)
            except Exception as e:
                logger.error(f"Error in watch cycle: {e}")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Watch stopped by user.")
        dispatch_wm_hook("idle", {"message": "Idle"})
        return 0


def handle_install_systemd(args: argparse.Namespace) -> int:
    # Resolve executable path
    which_bin = shutil.which("claudalizer")
    if not which_bin:
        # Fallback to sys.executable -m claudalizer.cli or user local bin
        which_bin = str(Path.home() / ".local" / "bin" / "claudalizer")

    systemd_src_dir = Path(__file__).resolve().parent.parent / "systemd"
    service_src = systemd_src_dir / "claudalizer.service"
    watch_src = systemd_src_dir / "claudalizer-watch.service"
    tmpfiles_src = systemd_src_dir / "claudalizer-tmpfiles.conf"

    # Destination directories
    user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    user_tmpfiles_dir = Path.home() / ".config" / "user-tmpfiles.d"

    # Prepare rendered unit contents
    service_content = service_src.read_text(encoding="utf-8")
    # Replace executable if needed
    service_content = service_content.replace("%h/.local/bin/claudalizer", which_bin)

    watch_content = watch_src.read_text(encoding="utf-8").replace("%h/.local/bin/claudalizer", which_bin)
    tmpfiles_content = tmpfiles_src.read_text(encoding="utf-8")

    if args.dry_run:
        print("=== DRY RUN: Systemd Unit Configurations ===")
        print(f"\n--- [{user_systemd_dir / 'claudalizer.service'}] ---")
        print(service_content.strip())
        print(f"\n--- [{user_systemd_dir / 'claudalizer-watch.service'}] ---")
        print(watch_content.strip())
        print(f"\n--- [{user_tmpfiles_dir / 'claudalizer.conf'}] ---")
        print(tmpfiles_content.strip())
        waybar_path = find_waybar_config()
        waybar_state = patch_waybar_config(waybar_path, dry_run=True)
        print(f"\n--- Waybar config: {waybar_path or '(not found)'} ---")
        print(f"status: {waybar_state}")
        print("\nDry-run complete. No files written.")
        return 0

    user_systemd_dir.mkdir(parents=True, exist_ok=True)
    user_tmpfiles_dir.mkdir(parents=True, exist_ok=True)

    dest_service = user_systemd_dir / "claudalizer.service"
    dest_watch = user_systemd_dir / "claudalizer-watch.service"
    dest_tmpfiles = user_tmpfiles_dir / "claudalizer.conf"

    dest_service.write_text(service_content, encoding="utf-8")
    dest_watch.write_text(watch_content, encoding="utf-8")
    dest_tmpfiles.write_text(tmpfiles_content, encoding="utf-8")

    print(f"Installed systemd units:")
    print(f"  • {dest_service}")
    print(f"  • {dest_watch}")
    print(f"  • {dest_tmpfiles}")
    print("\nTo activate now, run:")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user enable --now claudalizer-watch.service")

    waybar_path = find_waybar_config()
    waybar_state = patch_waybar_config(waybar_path)
    print(f"\nWaybar config: {waybar_path or '(not found)'}")
    if waybar_state == "added":
        print("  Added custom/claudalizer to modules-right (backup saved next to the config).")
        print("  Restart Waybar to load it.")
    elif waybar_state == "present":
        print("  custom/claudalizer already present; left unchanged.")
    else:
        print(f"  Not edited ({waybar_state}). Add it by hand:")
        print("  " + manual_snippet().replace("\n", "\n  "))

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claudalizer",
        description="Monitor ephemeral Claude Code sessions and distill behavioral memories.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--tmp-root", default=str(DEFAULT_TMP_ROOT), help="Root directory for ephemeral sessions")
    parser.add_argument("--claude-projects", default=str(DEFAULT_CLAUDE_PROJECTS), help="Claude projects storage directory")
    parser.add_argument("--memories-root", default=str(DEFAULT_MEMORIES_ROOT), help="Root directory for mined memories")
    parser.add_argument("--lock-file", default=str(DEFAULT_LOCK_FILE), help="File path for synchronization lock")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_p = subparsers.add_parser("scan", help="Run on-demand scan and extraction across ephemeral workspaces")
    scan_p.add_argument("--project", help="Filter by specific project slug")
    scan_p.add_argument("--force", action="store_true", help="Force re-extraction of already mined sessions")
    scan_p.add_argument("--no-debounce", action="store_true", help="Skip file-settle debouncing check")
    scan_p.add_argument("--notify", action="store_true", help="Send desktop notification and WM IPC hook")
    scan_p.add_argument("--auto-distill", action="store_true", help="Automatically distill memory blocks after mining")
    scan_p.add_argument("--llm-endpoint", help="OpenAI-compatible LLM endpoint (e.g. http://localhost:11434/v1/chat/completions)")
    scan_p.add_argument("--llm-model", default="llama3", help="LLM model name for distillation")

    # distill
    dist_p = subparsers.add_parser("distill", help="Distill unparsed dossiers into actionable memory blocks")
    dist_p.add_argument("--project", help="Filter by specific project slug")
    dist_p.add_argument("--force", action="store_true", help="Force re-distillation")
    dist_p.add_argument("--llm-endpoint", help="OpenAI-compatible LLM endpoint (e.g. http://localhost:11434/v1/chat/completions)")
    dist_p.add_argument("--llm-model", default="llama3", help="LLM model name for distillation")

    # watch
    watch_p = subparsers.add_parser("watch", help="Continuous monitoring loop with file debouncing")
    watch_p.add_argument("--interval", type=float, default=3.0, help="Polling interval in seconds")
    watch_p.add_argument("--project", help="Filter by specific project slug")
    watch_p.add_argument("--notify", action="store_true", default=True, help="Send notifications upon mining")
    watch_p.add_argument("--auto-distill", action="store_true", default=True, help="Auto distill mined sessions")
    watch_p.add_argument("--llm-endpoint", help="OpenAI-compatible LLM endpoint")
    watch_p.add_argument("--llm-model", default="llama3", help="LLM model name for distillation")

    # install-systemd
    inst_p = subparsers.add_parser("install-systemd", help="Install user-level systemd service and path units")
    inst_p.add_argument("--dry-run", action="store_true", help="Print unit contents without installing")

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    if args.command == "scan":
        return handle_scan(args)
    elif args.command == "distill":
        return handle_distill(args)
    elif args.command == "watch":
        return handle_watch(args)
    elif args.command == "install-systemd":
        return handle_install_systemd(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
