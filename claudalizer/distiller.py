"""Distillation pipeline for converting raw session dossiers into actionable memory blocks."""

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MEMORIES_ROOT = Path.home() / ".claude-mined-memories"

DISTILLATION_SYSTEM_PROMPT = """You are a software engineering memory synthesizer.
Your task is to analyze raw debugging sessions, tool friction, command failures, discarded spikes, and scratchpad scripts from an AI coding agent.
Synthesize actionable, durable memory rules formatted for future agent sessions.

Focus strictly on:
1. Tool / Skill Friction: Specific flag mismatches, command failures, unexpected CLI quirks, missing environment flags.
2. Blind Alleys & Discarded Spikes: Techniques or hypotheses tested and why they failed or were rejected.
3. Directives: Compact, imperative rules for future runs (compatible with project .claude/CLAUDE.md).

Omit standard git noise, minor typos, or self-evident information. Be concise and concrete.
"""


def build_synthesis_prompt(dossier_data: Dict[str, Any]) -> str:
    """Build structured markdown prompt summarizing session evidence."""
    slug = dossier_data.get("slug", "unknown")
    decoded_path = dossier_data.get("decoded_path", "unknown")
    prompts = dossier_data.get("user_prompts", [])
    errors = dossier_data.get("tool_errors", [])
    scratchpads = dossier_data.get("scratchpad_files", [])

    prompt_lines = [
        f"# Session Context for Project: `{slug}`",
        f"**Decoded Workspace Path:** `{decoded_path}`",
        "",
        "## User Intent & Objectives:",
    ]

    if prompts:
        for p in prompts[:10]:
            prompt_lines.append(f"- {p}")
    else:
        prompt_lines.append("_No explicit user prompt captured._")

    prompt_lines.extend(["", "## Tool / Command Failures & Behavioral Friction:"])
    if errors:
        for err in errors[:25]:
            tool = err.get("tool_name") or "unknown"
            cmd = err.get("command_or_input") or ""
            code = err.get("exit_code")
            out = (err.get("error_output") or "").strip()
            # Truncate output
            if len(out) > 300:
                out = out[:300] + "... [truncated]"
            code_str = f" (Exit {code})" if code is not None else ""
            prompt_lines.append(f"### Tool `{tool}`{code_str}")
            if cmd:
                prompt_lines.append(f"Command/Input: `{cmd}`")
            prompt_lines.append("```")
            prompt_lines.append(out)
            prompt_lines.append("```")
    else:
        prompt_lines.append("_No tool errors recorded._")

    prompt_lines.extend(["", "## Ephemeral Scratchpad Files Created:"])
    if scratchpads:
        for s in scratchpads:
            prompt_lines.append(f"- `{s}`")
    else:
        prompt_lines.append("_No scratchpad files captured._")

    prompt_lines.extend([
        "",
        "## Distillation Instructions:",
        "Generate a memory block in Markdown with exactly these three sections:",
        "### 1. Tool / Skill Friction",
        "### 2. Blind Alleys & Discarded Spikes",
        "### 3. Directives for CLAUDE.md",
    ])

    return "\n".join(prompt_lines)


def call_llm_completion(
    prompt: str,
    endpoint: str = "http://localhost:11434/v1/chat/completions",
    model: str = "llama3",
    timeout: float = 30.0,
) -> Optional[str]:
    """Call OpenAI-compatible LLM endpoint (Ollama, llama.cpp, etc.) using urllib."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": DISTILLATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            choices = res_json.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.warning(f"LLM call to {endpoint} failed: {e}")
        return None

    return None


def synthesize_offline_memory_block(dossier_data: Dict[str, Any]) -> str:
    """Generate structured markdown memory block deterministically offline without LLM."""
    errors = dossier_data.get("tool_errors", [])
    scratchpads = dossier_data.get("scratchpad_files", [])
    slug = dossier_data.get("slug", "unknown")
    decoded = dossier_data.get("decoded_path", slug)

    lines = [
        f"# Mined Behavioral Memory for `{slug}`",
        f"**Source Directory:** `{decoded}`",
        "",
        "### 1. Tool / Skill Friction",
    ]

    if errors:
        seen_cmds = set()
        for err in errors:
            cmd = (err.get("command_or_input") or "").strip()
            tool = err.get("tool_name") or "Tool"
            out = (err.get("error_output") or "").strip().split("\n")[0]
            exit_code = err.get("exit_code")

            key = (tool, cmd)
            if key in seen_cmds:
                continue
            seen_cmds.add(key)

            lines.append(f"- **{tool}** (`{cmd[:80]}`): Exit code {exit_code}. First line: `{out[:120]}`")
    else:
        lines.append("- None detected.")

    lines.extend(["", "### 2. Blind Alleys & Discarded Spikes"])
    if scratchpads:
        for s in scratchpads:
            lines.append(f"- Ephemeral scratchpad tested: `{s}`")
    else:
        lines.append("- No ephemeral scratchpads recorded.")

    lines.extend([
        "",
        "### 3. Directives for CLAUDE.md",
    ])

    # Infer directives from errors
    directives = []
    for err in errors:
        out = (err.get("error_output") or "")
        cmd = (err.get("command_or_input") or "")
        if "No such file or directory" in out and "python" in out:
            directives.append("Verify Python virtualenv or conda environment path before executing Python scripts.")
        elif "command not found" in out:
            directives.append(f"Ensure system binaries and build prerequisites are installed before invoking `{cmd.split()[0] if cmd else 'tools'}`.")
        elif "cargo" in cmd and "error" in out.lower():
            directives.append("Check Cargo build flags and crate dependencies before running tests.")

    if not directives:
        directives.append("Maintain strict idempotency and check environment variables before execution.")

    # Deduplicate directives
    for d in sorted(set(directives)):
        lines.append(f"- {d}")

    return "\n".join(lines)


class MemoryDistiller:
    """Ingests dossiers and distills actionable memory blocks."""

    def __init__(self, memories_root: Path = DEFAULT_MEMORIES_ROOT):
        self.memories_root = Path(memories_root)

    def distill_session(
        self,
        slug: str,
        session_id: str,
        llm_endpoint: Optional[str] = None,
        llm_model: str = "llama3",
        force: bool = False,
    ) -> Optional[Path]:
        """Distill a single session dossier into memory.md."""
        session_dir = self.memories_root / slug / session_id
        dossier_json = session_dir / "dossier.json"
        memory_md = session_dir / "memory.md"

        if not dossier_json.exists():
            return None

        if memory_md.exists() and not force:
            logger.debug(f"{memory_md} already exists. Skipping.")
            return memory_md

        with open(dossier_json, "r", encoding="utf-8") as f:
            dossier_data = json.load(f)

        content: Optional[str] = None
        if llm_endpoint:
            prompt = build_synthesis_prompt(dossier_data)
            content = call_llm_completion(prompt, endpoint=llm_endpoint, model=llm_model)

        if not content:
            # Fallback to offline deterministic synthesis
            content = synthesize_offline_memory_block(dossier_data)

        with open(memory_md, "w", encoding="utf-8") as f:
            f.write(content + "\n")

        # Also update / append to project-level aggregated memory
        self._append_to_project_memory(slug, content, session_id)

        return memory_md

    def _append_to_project_memory(self, slug: str, memory_block: str, session_id: str) -> None:
        """Append memory block to ~/.claude-mined-memories/<slug>/PROJECT_MEMORY.md."""
        proj_dir = self.memories_root / slug
        proj_dir.mkdir(parents=True, exist_ok=True)
        proj_memory_file = proj_dir / "PROJECT_MEMORY.md"

        header = f"\n\n---\n## Session {session_id[:8]} Distillation\n"
        with open(proj_memory_file, "a", encoding="utf-8") as f:
            f.write(header + memory_block + "\n")

    def distill_all(
        self,
        target_slug: Optional[str] = None,
        llm_endpoint: Optional[str] = None,
        llm_model: str = "llama3",
        force: bool = False,
    ) -> List[Path]:
        """Distill all unparsed or matching session dossiers."""
        distilled: List[Path] = []
        if not self.memories_root.exists():
            return distilled

        for slug_dir in self.memories_root.iterdir():
            if not slug_dir.is_dir() or slug_dir.name.startswith("."):
                continue

            slug = slug_dir.name
            if target_slug and slug != target_slug:
                continue

            for sess_dir in slug_dir.iterdir():
                if not sess_dir.is_dir() or sess_dir.name.startswith("."):
                    continue
                session_id = sess_dir.name
                res = self.distill_session(
                    slug,
                    session_id,
                    llm_endpoint=llm_endpoint,
                    llm_model=llm_model,
                    force=force,
                )
                if res:
                    distilled.append(res)

        return distilled
