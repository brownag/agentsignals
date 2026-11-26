"""Claude Code session source: walks the tmp root and reads ~/.claude transcripts."""

from pathlib import Path
from typing import Iterator, Optional

from agentsignals.miner import (
    SETTLE_DEBOUNCE_SECONDS,
    decode_slug,
    is_file_settled,
    newest_mtime,
    parse_transcript_events,
)
from agentsignals.sources import Extraction, SessionRef


class ClaudeCodeSource:
    name = "claude_code"

    def __init__(self, tmp_root: Path, claude_projects: Path) -> None:
        self.tmp_root = tmp_root
        self.claude_projects = claude_projects

    def _transcript(self, slug: str, session_id: str) -> Path:
        return self.claude_projects / slug / f"{session_id}.jsonl"

    def iter_sessions(self, target_slug: Optional[str]) -> Iterator[SessionRef]:
        if not self.tmp_root.exists():
            return
        for slug_entry in self.tmp_root.iterdir():
            if not slug_entry.is_dir() or slug_entry.name.startswith("."):
                continue
            slug = slug_entry.name
            if not slug.startswith("-"):
                continue
            if target_slug and slug != target_slug:
                continue
            decoded = decode_slug(slug)
            for session_dir in slug_entry.iterdir():
                if not session_dir.is_dir() or session_dir.name.startswith("."):
                    continue
                sid = session_dir.name
                yield SessionRef(
                    source=self.name,
                    slug=slug,
                    session_id=sid,
                    decoded_path=decoded,
                    changed_at=self._changed_at(session_dir / "scratchpad", self._transcript(slug, sid)),
                    settled=is_file_settled(session_dir, SETTLE_DEBOUNCE_SECONDS),
                )

    @staticmethod
    def _changed_at(scratchpad: Path, transcript: Path) -> float:
        terms = [0.0, 0.0]
        try:
            if scratchpad.is_dir():
                terms[0] = newest_mtime(scratchpad)
        except OSError:
            pass
        try:
            if transcript.exists():
                terms[1] = transcript.stat().st_mtime
        except OSError:
            pass
        return max(terms)

    def extract(self, ref: SessionRef) -> Extraction:
        transcript = self._transcript(ref.slug, ref.session_id)
        prompts, errors = parse_transcript_events(transcript)
        return Extraction(
            user_prompts=prompts,
            tool_errors=errors,
            scratchpad_dir=self.tmp_root / ref.slug / ref.session_id / "scratchpad",
            touched_files=[],
            transcript_found=transcript.exists(),
            source_meta={},
        )
