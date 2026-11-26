"""Git history for the mined memories root.

Every pass that changes the memories root leaves one commit, so an earlier dossier,
memory file or project memory can be restored. Git failures never raise: they are logged
and the caller carries on. Callers must hold the mining lock around every call.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

GIT_IGNORE_LINES = ["scan_status.json", "*.tmp", ".PROJECT_MEMORY.*.tmp"]
BOT_NAME, BOT_EMAIL = "claudalizer", "claudalizer@localhost"

_GIT_TIMEOUT_SECONDS = 120
_git_missing_warned = False


def _reset_warnings() -> None:
    global _git_missing_warned
    _git_missing_warned = False


def _clean_env() -> dict:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class MemoryRepo:
    """Git repository in the memories root. Methods return None/False instead of raising."""

    def __init__(self, root: Path, enabled: bool = True) -> None:
        self.root = Path(root).expanduser()
        self.enabled = enabled
        self._active = False
        if os.environ.get("CLAUDALIZER_TESTING") and self.root.resolve() == (
            Path.home() / ".claude-mined-memories"
        ).resolve():
            raise RuntimeError("tests must not use the real memories root")

    @property
    def active(self) -> bool:
        return self._active

    def _git(self, *args: str, input_text: Optional[str] = None,
             ok_codes: tuple = (0,)) -> Optional[subprocess.CompletedProcess]:
        global _git_missing_warned
        cmd = [
            "git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
            "-c", "core.excludesFile=/dev/null", *args,
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=self.root, env=_clean_env(), input=input_text,
                capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECONDS,
            )
        except FileNotFoundError:
            if not _git_missing_warned:
                _git_missing_warned = True
                log.warning("git not found; memory history is off for this process")
            return None
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("git %s failed: %s", args[0] if args else "", exc)
            return None
        if proc.returncode not in ok_codes:
            log.warning("git %s exited %d: %s", args[0] if args else "", proc.returncode,
                        proc.stderr.strip())
            return None
        return proc

    def ensure(self) -> bool:
        global _git_missing_warned
        if not self.enabled:
            return False
        if self._active:
            return True
        if (self.root / ".git").exists():
            self._active = True
            return True
        if shutil.which("git") is None:
            if not _git_missing_warned:
                _git_missing_warned = True
                log.warning("git not found; memory history is off for this process")
            return False
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("cannot create memories root for git: %s", exc)
            return False
        if self._git("init", "-q", "-b", "main") is None:
            return False
        self._git("config", "user.name", BOT_NAME)
        self._git("config", "user.email", BOT_EMAIL)
        (self.root / ".gitignore").write_text("\n".join(GIT_IGNORE_LINES) + "\n", encoding="utf-8")
        if self._git("add", "-A") is None:
            return False
        if self._git("commit", "-q", "--allow-empty", "-m", "baseline: existing memories") is None:
            return False
        files = self._git("ls-files")
        count = len(files.stdout.splitlines()) if files else 0
        log.info("memory history: created repo in %s with %d files", self.root, count)
        self._active = True
        return True

    def commit_external(self, before: str) -> Optional[str]:
        if not self.enabled or not self.active:
            return None
        status = self._git("status", "--porcelain")
        if status is None or not status.stdout.strip():
            return None
        if self._git("add", "-A") is None:
            return None
        if self._git("commit", "-q", "-m", f"external: changes found before {before}") is None:
            return None
        return self._short_head()

    def commit_pass(self, title: str, lines: List[str]) -> Optional[str]:
        if not self.enabled or not self.active:
            return None
        if self._git("add", "-A") is None:
            return None
        # --quiet exits 0 when nothing is staged and 1 when something is.
        staged = self._git("diff", "--cached", "--quiet", ok_codes=(0, 1))
        if staged is None or staged.returncode == 0:
            return None
        message = title + "\n\n" + "\n".join(lines) + "\n"
        if self._git("commit", "-q", "-F", "-", input_text=message) is None:
            return None
        return self._short_head()

    def _short_head(self) -> Optional[str]:
        proc = self._git("rev-parse", "--short", "HEAD")
        return proc.stdout.strip() if proc else None
