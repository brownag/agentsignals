# claudalizer

Lightweight, zero-maintenance background daemon and CLI toolkit designed to monitor `/tmp/claude-1000/` (and related ephemeral session folders), intercept volatile Claude Code scratchpads and conversation transcripts before they are wiped, separate Git-discernable state from behavioral signals, and distill actionable memory rules for future agent workflows.

---

## Key Features

1. **Ephemeral vs. Persistent Separation:**
   - Scans `/tmp/claude-1000/` for active and abandoned session workspaces.
   - Cross-references with persistent JSONL transcripts in `~/.claude/projects/<slug>/<session-id>.jsonl`.
   - **Filters out Git-discernable noise:** Ignores successful `git diff`, `git status`, and `git log` calls, and successful Edit/Write results, because Git history already tracks them. Clean test passes are not filtered.
   - **Preserves behavioral signals:** Captures failed tool results (including failed git commands), non-zero command exit codes (exit code 0 is not kept as a failure), recurring error loops, aborted scratchpad scripts, transient API debug logs, and prompt objectives defining user intent.

2. **Dossiers & Distillation:**
   - Generates structured session dossiers in `~/.claude-mined-memories/<project-slug>/<session-id>/dossier.json`.
   - Distills actionable memory blocks in `memory.md` and appends to `PROJECT_MEMORY.md`:
     - **Tool / Skill Friction:** Specific flag mismatches, command failures, or CLI quirks.
     - **Blind Alleys & Discarded Spikes:** Techniques tested and why they failed.
     - **Directives:** Compact, imperative rules for future runs (compatible with `.claude/CLAUDE.md`).
   - Supports local OpenAI-compatible LLM endpoints (Ollama, `llama.cpp`) with automatic offline deterministic fallback synthesis.

3. **IPC & Window Manager Integration:**
   - Desktop notifications via `notify-send`.
   - Wayland compositor hooks refresh Waybar without an extra desktop popup.
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

# Opt in to a desktop notification when sessions are mined
claudalizer scan --notify

# Retain the most recent 100 scans
claudalizer scan --history-limit 100

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
# Run continuous polling / file debounce loop without desktop notifications
claudalizer watch --interval 5.0

# Opt in to notifications and disable individual history records
claudalizer watch --interval 5.0 --notify --history-limit 0
```

Notifications are off by default for both `scan` and `watch`. With `--notify`, each scan that mines at least one session sends one aggregate desktop notification; scans that mine nothing send none. Watch automatically distills mined sessions. The supplied systemd watch unit runs `claudalizer watch` without `--notify`.

Both commands accept a non-negative `--history-limit`, defaulting to 50 recent scans. A limit of 0 removes individual history records while retaining the latest scan and cumulative totals. To use a different memories root, put the global option before the command, for example `claudalizer --memories-root /path/to/memories scan --history-limit 100`.

### 4. Systemd Service & Watch Unit Installation
```bash
# Dry run to inspect generated unit files
claudalizer install-systemd --dry-run

# Install user systemd units (~/.config/systemd/user/)
claudalizer install-systemd

# Enable and start the watch daemon
systemctl --user daemon-reload
systemctl --user enable --now claudalizer-watch.service
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
    "signal": 8,
    "tooltip": true
}
```

Claudalizer sends `pkill -RTMIN+8 waybar` after each status write, so the module refreshes immediately. Polling every `interval` seconds remains the fallback.

The module text shows the latest mined count, adding the active count only when there are active sessions; when nothing was mined and no sessions are active, it shows only the brain icon. Hover for the latest scan time and counts, the last project (when available), and cumulative totals. The tooltip ends with up to three recent scans that mined sessions; empty scans are omitted. Active sessions are those skipped because they were still changing.

Scan state is stored separately from the temporary Waybar payload in `<memories-root>/scan_status.json` (by default `~/.claude-mined-memories/scan_status.json`). It is atomically written after each completed scan, including scans that mine nothing, and is available across process restarts. Missing or corrupt state starts fresh; if writing fails, mining can continue without persistence. Compositor hooks refresh Waybar without creating an additional desktop popup.

---

## Running Tests

```bash
pytest tests/ -v
```
