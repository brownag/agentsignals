"""Session source types shared by the miner core and the per-source adapters."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Protocol

if TYPE_CHECKING:
    from agentsignals.miner import ToolErrorEvent


@dataclass(frozen=True)
class SessionRef:
    source: str  # "claude_code" | "opencode"
    slug: str  # memories-root folder name
    session_id: str
    decoded_path: Optional[str]
    changed_at: float  # epoch seconds of the newest change to the session
    settled: bool  # the adapter's own "finished" test passed


@dataclass
class Extraction:
    user_prompts: List[str]
    tool_errors: List["ToolErrorEvent"]
    scratchpad_dir: Optional[Path]  # None when the source has no scratchpad
    touched_files: List[str]
    transcript_found: bool
    source_meta: Dict[str, Any]


class SessionSource(Protocol):
    name: str

    def iter_sessions(self, target_slug: Optional[str]) -> Iterator[SessionRef]: ...

    def extract(self, ref: SessionRef) -> Extraction: ...
