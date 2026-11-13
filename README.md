# claudalizer

Lightweight, zero-maintenance background daemon and CLI toolkit designed to monitor `/tmp/claude-1000/` (and related ephemeral session folders), intercept volatile Claude Code scratchpads and conversation transcripts before they are wiped, separate Git-discernable state from behavioral signals, and distill actionable memory rules for future agent workflows.

---

## Key Features

1. **Ephemeral vs. Persistent Separation:**
   - Scans `/tmp/claude-1000/` for active and abandoned session workspaces.
   - Cross-references with persistent JSONL transcripts in `~/.claude/projects/<slug>/<session-id>.jsonl`.
   - **Filters out Git-discernable noise:** Ignores code modifications, checked-in commits, file diffs, and standard clean test passes already captured by Git history.
   - **Preserves behavioral signals:** Captures tool failures, command exit codes, recurring error loops, aborted scratchpad scripts, transient API debug logs, and prompt objectives defining user intent.

2. **Dossiers & Distillation:**
   - Generates structured session dossiers in `~/.claude-mined-memories/<project-slug>/<session-id>/dossier.json`.
   - Distills actionable memory blocks in `memory.md` and appends to `PROJECT_MEMORY.md`:
     - **Tool / Skill Friction:** Specific flag mismatches, command failures, or CLI quirks.
     - **Blind Alleys & Discarded Spikes:** Techniques tested and why they failed.
     - **Directives:** Compact, imperative rules for future runs (compatible with `.claude/CLAUDE.md`).
   - Supports local OpenAI-compatible LLM endpoints (Ollama, `llama.cpp`) with automatic offline deterministic fallback synthesis.

3. **IPC & Window Manager Integration:**
   - Desktop notifications via `notify-send`.
   - Wayland compositor hooks for Sway (`swaymsg`) and Hyprland (`hyprctl`).
   - Waybar custom JSON status module output at `/tmp/claudalizer_status.json`.

4. **Zero Heavyweight Dependencies:**
   - Implemented using Python 3 standard library (`json`, `urllib`, `pathlib`, `fcntl`, `subprocess`).

---

## Installation

```bash
# In editable user mode
pip install -e . --no-deps --user
```

---

## CLI Usage

### 1. On-Demand Scan
```bash
# Scan all ephemeral sessions and extract dossiers
claudalizer scan

# Scan and send desktop notification & WM signals
claudalizer scan --notify

# Scan with automatic memory distillation
claudalizer scan --auto-distill
```

### 2. Distill Memories
```bash
# Distill unparsed dossiers into Markdown memory blocks
claudalizer distill

# Distill with local Ollama / llama.cpp OpenAI-compatible endpoint
claudalizer distill --llm-endpoint http://localhost:11434/v1/chat/completions --llm-model llama3
```

### 3. Continuous Watch Daemon
```bash
# Run continuous polling / file debounce loop
claudalizer watch --interval 5.0 --notify --auto-distill
```

### 4. Systemd Service & Path Unit Installation
```bash
# Dry run to inspect generated unit files
claudalizer install-systemd --dry-run

# Install user systemd units (~/.config/systemd/user/)
claudalizer install-systemd

# Enable and start the systemd path monitor
systemctl --user daemon-reload
systemctl --user enable --now claudalizer.path
```

---

## Waybar Configuration Example

Add a custom module in `~/.config/waybar/config`:
```json
"custom/claudalizer": {
    "format": "{}",
    "return-type": "json",
    "exec": "cat /tmp/claudalizer_status.json 2>/dev/null || echo '{\"text\":\"🧠\"}'",
    "interval": 3,
    "tooltip": true
}
```

---

## Running Tests

```bash
pytest tests/ -v
```
