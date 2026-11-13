"""Core scanning, snapshotting, and extraction engine for claudalizer."""

import fcntl
import hashlib
import json
import logging
import os
import shutil
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

DEFAULT_TMP_ROOT = Path("/tmp/claude-1000")
DEFAULT_CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
DEFAULT_MEMORIES_ROOT = Path.home() / ".claude-mined-memories"
DEFAULT_LOCK_FILE = Path("/tmp/claudalizer.lock")

MAX_SCRATCHPAD_FILE_BYTES = 250 * 1024  # 250 KB
MIN_PROMPT_LENGTH = 15
SETTLE_DEBOUNCE_SECONDS = 2.0


@dataclass
class ToolErrorEvent:
    tool_use_id: Optional[str]
    tool_name: Optional[str]
    command_or_input: Optional[str]
    error_output: str
    exit_code: Optional[int] = None
    timestamp: Optional[str] = None


@dataclass
class SessionDossier:
    slug: str
    session_id: str
    decoded_path: Optional[str]
    transcript_found: bool
    scan_timestamp: float
    user_prompts: List[str] = field(default_factory=list)
    tool_errors: List[Dict[str, Any]] = field(default_factory=list)
    scratchpad_files: List[str] = field(default_factory=list)
    skipped_files: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@contextmanager
def file_lock(lock_path: Path = DEFAULT_LOCK_FILE, timeout: float = 10.0) -> Iterator[bool]:
    """Acquire an exclusive advisory lock using flock with timeout."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    start = time.time()
    acquired = False
    try:
        while True:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (BlockingIOError, OSError):
                if time.time() - start >= timeout:
                    raise TimeoutError(f"Timed out waiting for lock on {lock_path}")
                time.sleep(0.1)
        yield acquired
    finally:
        if acquired:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        f.close()


def decode_slug(slug: str) -> Optional[str]:
    """Decode Claude Code directory slug into a filesystem path.

    Claude Code replaces '/' with '-' and prefix with '-' (e.g. -home-user-projects-app).
    Because actual directory names may contain hyphens, we resolve greedily against existing filesystem paths.
    """
    if not slug.startswith("-"):
        candidate = slug.replace("-", "/")
        return candidate if os.path.exists(candidate) else None

    # Strip leading '-'
    parts = slug[1:].split("-")

    # Greedy search against root filesystem
    def match_path(current_path: Path, remaining_parts: List[str]) -> Optional[Path]:
        if not remaining_parts:
            return current_path if current_path.exists() else None

        # Try grouping as many tokens as possible into one directory name
        for i in range(len(remaining_parts), 0, -1):
            segment = "-".join(remaining_parts[:i])
            test_path = current_path / segment
            if test_path.exists():
                res = match_path(test_path, remaining_parts[i:])
                if res:
                    return res
        return None

    resolved = match_path(Path("/"), parts)
    if resolved:
        return str(resolved)

    # Fallback heuristic: simply replace '-' with '/'
    fallback = "/" + "/".join(parts)
    return fallback


def newest_mtime(path: Path) -> float:
    """Return the newest mtime of path, or of any file beneath it if path is a directory."""
    newest = path.stat().st_mtime
    if path.is_dir():
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    newest = max(newest, (Path(root) / name).stat().st_mtime)
                except OSError:
                    continue  # file removed mid-walk
    return newest


def scratchpad_changed_since(scratchpad_dir: Path, reference: Path) -> bool:
    """True if any file under scratchpad_dir is newer than the reference file."""
    if not scratchpad_dir.is_dir():
        return False
    try:
        return newest_mtime(scratchpad_dir) > reference.stat().st_mtime
    except OSError:
        return False


def is_file_settled(file_path: Path, min_age_seconds: float = SETTLE_DEBOUNCE_SECONDS) -> bool:
    """Check if a file, or everything under a directory, has been quiet for at least min_age_seconds."""
    try:
        return (time.time() - newest_mtime(file_path)) >= min_age_seconds
    except OSError:
        return False


def is_git_discernable(tool_name: Optional[str], command_or_input: Optional[str], error_output: str) -> bool:
    """Filter out Git-discernable noise.

    Returns True if the event is a standard successful Git diff, commit, or clean test pass
    that is already tracked in Git history.
    """
    if not tool_name:
        tool_name = ""
    cmd = (command_or_input or "").strip()
    out = (error_output or "").strip()

    # If it was an edit/write tool and didn't fail, git diff already tracks it
    if tool_name in ("Edit", "Write") and not out:
        return True

    # If git commit/status/diff succeeded without error
    if cmd.startswith("git diff") or cmd.startswith("git status") or cmd.startswith("git log"):
        # Informational inspection
        return True

    return False


def parse_transcript_events(
    transcript_path: Path,
) -> Tuple[List[str], List[ToolErrorEvent]]:
    """Parse JSONL transcript to extract meaningful user prompts and tool failure signals."""
    user_prompts: List[str] = []
    tool_errors: List[ToolErrorEvent] = []
    tool_uses: Dict[str, Dict[str, Any]] = {}

    if not transcript_path.exists() or not transcript_path.is_file():
        return user_prompts, tool_errors

    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    # Gracefully skip malformed JSON line
                    continue

                rec_type = record.get("type")

                # Assistant messages containing tool_use blocks
                if rec_type == "assistant":
                    msg = record.get("message", {})
                    content = msg.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                t_id = block.get("id")
                                if t_id:
                                    tool_uses[t_id] = {
                                        "name": block.get("name"),
                                        "input": block.get("input", {}),
                                    }

                # User messages containing text prompts or tool_result blocks
                elif rec_type == "user":
                    msg = record.get("message", {})
                    content = msg.get("content")

                    # Direct string user prompt
                    if isinstance(content, str):
                        clean_prompt = content.strip()
                        # Ignore system/command notifications (e.g. <local-command-caveat>)
                        if len(clean_prompt) >= MIN_PROMPT_LENGTH and not clean_prompt.startswith("<local-command"):
                            user_prompts.append(clean_prompt)

                    elif isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            b_type = block.get("type")
                            if b_type == "text":
                                txt = block.get("text", "").strip()
                                if len(txt) >= MIN_PROMPT_LENGTH and not txt.startswith("<local-command"):
                                    user_prompts.append(txt)
                            elif b_type == "tool_result":
                                is_err = block.get("is_error", False)
                                res_content = block.get("content")
                                text_out = ""
                                if isinstance(res_content, str):
                                    text_out = res_content
                                elif isinstance(res_content, list):
                                    text_out = "\n".join(
                                        c.get("text", "") for c in res_content if isinstance(c, dict)
                                    )

                                # Check exit code or error markers in text
                                has_exit_err = "Exit code" in text_out or "command not found" in text_out or "Error:" in text_out
                                if is_err or has_exit_err:
                                    t_id = block.get("tool_use_id")
                                    t_info = tool_uses.get(t_id, {}) if t_id else {}
                                    t_name = t_info.get("name")
                                    t_input = t_info.get("input")
                                    cmd_repr = ""
                                    if isinstance(t_input, dict):
                                        cmd_repr = t_input.get("command") or t_input.get("file_path") or str(t_input)
                                    else:
                                        cmd_repr = str(t_input or "")

                                    if not is_git_discernable(t_name, cmd_repr, text_out):
                                        # Extract exit code if present
                                        exit_code = None
                                        if "Exit code " in text_out:
                                            try:
                                                part = text_out.split("Exit code ")[1].split()[0]
                                                exit_code = int(part)
                                            except (IndexError, ValueError):
                                                pass

                                        tool_errors.append(
                                            ToolErrorEvent(
                                                tool_use_id=t_id,
                                                tool_name=t_name,
                                                command_or_input=cmd_repr[:500] if cmd_repr else None,
                                                error_output=text_out[:4000],  # Bound error payload
                                                exit_code=exit_code,
                                                timestamp=record.get("timestamp"),
                                            )
                                        )
    except Exception as e:
        logger.warning(f"Failed to parse transcript {transcript_path}: {e}")

    return user_prompts, tool_errors


def snapshot_scratchpad(
    src_scratchpad_dir: Path,
    dest_scratchpad_dir: Path,
    max_file_size: int = MAX_SCRATCHPAD_FILE_BYTES,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Snapshot non-binary, bounded ephemeral files from scratchpad directory.

    Returns (copied, skipped). Each skipped entry has path, size_bytes and a reason of
    "oversized", "binary" or "unreadable". Symlinks and excluded directories are silent.
    """
    copied_files: List[str] = []
    skipped: List[Dict[str, Any]] = []
    if not src_scratchpad_dir.exists() or not src_scratchpad_dir.is_dir():
        return copied_files, skipped

    dest_scratchpad_dir.mkdir(parents=True, exist_ok=True)

    for item in src_scratchpad_dir.rglob("*"):
        if not item.is_file() or item.is_symlink():
            continue

        rel_path = item.relative_to(src_scratchpad_dir)
        # Skip python venvs, git repos, or node_modules nested in scratchpads
        if any(p in ("venv", ".venv", "node_modules", ".git", "__pycache__") for p in rel_path.parts):
            continue

        rel = rel_path.as_posix()
        sz: Optional[int] = None
        try:
            sz = item.stat().st_size
            if sz > max_file_size:
                skipped.append({"path": rel, "size_bytes": sz, "reason": "oversized"})
                continue

            # Read first 1024 bytes to check for null bytes (binary check)
            with open(item, "rb") as f_check:
                chunk = f_check.read(1024)
                if b"\x00" in chunk:
                    skipped.append({"path": rel, "size_bytes": sz, "reason": "binary"})
                    continue

            target_file = dest_scratchpad_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target_file)
            copied_files.append(str(rel_path))
        except (OSError, PermissionError):
            skipped.append({"path": rel, "size_bytes": sz, "reason": "unreadable"})

    return copied_files, skipped


class SessionMiner:
    """Scans ephemeral session directories, correlates with transcripts, and builds dossiers."""

    def __init__(
        self,
        tmp_root: Path = DEFAULT_TMP_ROOT,
        claude_projects: Path = DEFAULT_CLAUDE_PROJECTS,
        memories_root: Path = DEFAULT_MEMORIES_ROOT,
        lock_file: Path = DEFAULT_LOCK_FILE,
    ):
        self.tmp_root = Path(tmp_root)
        self.claude_projects = Path(claude_projects)
        self.memories_root = Path(memories_root)
        self.lock_file = Path(lock_file)

    def scan_and_mine(
        self,
        debounce: bool = True,
        force: bool = False,
        target_slug: Optional[str] = None,
    ) -> List[SessionDossier]:
        """Scan tmp_root and extract all found sessions."""
        dossiers: List[SessionDossier] = []

        if not self.tmp_root.exists():
            logger.info(f"Tmp root {self.tmp_root} does not exist.")
            return dossiers

        with file_lock(self.lock_file):
            for slug_entry in self.tmp_root.iterdir():
                if not slug_entry.is_dir() or slug_entry.name.startswith("."):
                    continue

                slug = slug_entry.name
                if not slug.startswith("-home-") and not slug.startswith("-"):
                    # Not a project directory (e.g. bash-edit-diff or files)
                    continue

                if target_slug and slug != target_slug:
                    continue

                decoded = decode_slug(slug)

                # Iterate session UUID folders
                for session_dir in slug_entry.iterdir():
                    if not session_dir.is_dir() or session_dir.name.startswith("."):
                        continue

                    session_id = session_dir.name

                    # Debounce check on session directory and files
                    scratchpad_dir = session_dir / "scratchpad"
                    if debounce:
                        # Check if session dir is still active
                        if not is_file_settled(session_dir, SETTLE_DEBOUNCE_SECONDS):
                            logger.debug(f"Session {session_id} not settled yet. Skipping.")
                            continue

                    dossier = self._mine_session(slug, decoded, session_id, scratchpad_dir, force=force)
                    if dossier:
                        dossiers.append(dossier)

        return dossiers

    def _mine_session(
        self,
        slug: str,
        decoded_path: Optional[str],
        session_id: str,
        scratchpad_dir: Path,
        force: bool = False,
    ) -> Optional[SessionDossier]:
        """Extract a single session and save its dossier."""
        dossier_dir = self.memories_root / slug / session_id
        dossier_json = dossier_dir / "dossier.json"

        if dossier_json.exists() and not force:
            if not scratchpad_changed_since(scratchpad_dir, dossier_json):
                logger.debug(f"Dossier {dossier_json} already up to date. Skipping.")
                return None
            logger.info(f"Scratchpad for {slug}/{session_id} changed since last mine. Re-mining.")

        # Cross-reference with persistent JSONL transcript
        transcript_path = self.claude_projects / slug / f"{session_id}.jsonl"
        transcript_found = transcript_path.exists()

        user_prompts, tool_errors = parse_transcript_events(transcript_path)

        # Snapshot scratchpad files
        dest_scratchpad = dossier_dir / "scratchpad"
        copied_files, skipped_files = snapshot_scratchpad(scratchpad_dir, dest_scratchpad)

        # If nothing behavioral was found (no prompts, no errors, no scratchpad or skipped files), skip empty dossier
        if not user_prompts and not tool_errors and not copied_files and not skipped_files:
            return None

        dossier = SessionDossier(
            slug=slug,
            session_id=session_id,
            decoded_path=decoded_path,
            transcript_found=transcript_found,
            scan_timestamp=time.time(),
            user_prompts=user_prompts,
            tool_errors=[asdict(e) for e in tool_errors],
            scratchpad_files=copied_files,
            skipped_files=skipped_files,
            stats={
                "prompt_count": len(user_prompts),
                "error_count": len(tool_errors),
                "scratchpad_count": len(copied_files),
                "skipped_count": len(skipped_files),
            },
        )

        dossier_dir.mkdir(parents=True, exist_ok=True)
        # Write to a temp file, sync it, then rename over the old dossier so a crash
        # never leaves a half-written dossier.json.
        tmp_json = dossier_json.with_name(dossier_json.name + ".tmp")
        try:
            with open(tmp_json, "w", encoding="utf-8") as f:
                json.dump(dossier.to_dict(), f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_json, dossier_json)
        except BaseException:
            tmp_json.unlink(missing_ok=True)
            raise

        logger.info(f"Mined dossier for {slug}/{session_id}: {len(tool_errors)} errors, {len(copied_files)} files.")
        return dossier
