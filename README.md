# agentsignals

A background daemon and CLI that watches `/tmp/claude-1000/` and related session folders. agentsignals saves Claude Code scratchpads and transcripts before they are wiped. It separates Git-tracked state from behavioral signals, then distills memory rules for future agent runs.

---

## Key Features

1. **Ephemeral vs. Persistent Separation:**
   - Scans `/tmp/claude-1000/` for active and abandoned session workspaces.
   - Cross-references with persistent JSONL transcripts in `~/.claude/projects/<slug>/<session-id>.jsonl`.
   - **Filters out noise Git already tracks:** Drops successful `git diff`, `git status`, and `git log` calls, and successful Edit/Write results. Clean test passes are kept.
   - **Keeps behavioral signals:** Failed tool results (including failed git commands), non-zero exit codes (exit 0 is not a failure), recurring error loops, aborted scratchpad scripts, transient API debug logs, and the prompts that state user intent.

2. **Dossiers & Distillation:**
   - Generates structured session dossiers in `~/.claude-mined-memories/<project-slug>/<session-id>/dossier.json`.
   - Distills memory into `memory.md` and appends to `PROJECT_MEMORY.md`:
     - **Tool / Skill Friction:** Specific flag mismatches, command failures, or CLI quirks.
     - **Blind Alleys & Discarded Spikes:** Techniques tested and why they failed.
     - **Directives:** Short imperative rules for future runs. They work in `.claude/CLAUDE.md`.
   - Needs a local OpenAI-compatible LLM endpoint (Ollama, `llama.cpp`). There is no offline fallback: without an endpoint, or when the LLM returns nothing, no memory is written and existing memory files are left alone. `agentsignals distill` exits with code 2 when no endpoint is set.

3. **IPC & Window Manager Integration:**
   - Desktop notifications via `notify-send`.
   - Wayland compositor hooks refresh Waybar without an extra desktop popup.
   - Waybar custom JSON status module output at `/tmp/agentsignals_status.json` (kept for compatibility).

4. **No Runtime Dependencies:**
   - Uses only the Python 3 standard library: `json`, `urllib`, `pathlib`, `fcntl`, `subprocess`.

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
agentsignals scan

# Opt in to a desktop notification when sessions are mined
agentsignals scan --notify

# Retain the most recent 100 scans
agentsignals scan --history-limit 100

# Scan with automatic memory distillation
agentsignals scan --auto-distill
```

### 2. Distill Memories
```bash
# Distill unparsed dossiers into Markdown memory blocks
agentsignals distill

# Distill with local Ollama / llama.cpp OpenAI-compatible endpoint
agentsignals distill --llm-endpoint http://localhost:11434/v1/chat/completions --llm-model llama3
```

### 3. Continuous Watch Daemon
```bash
# Run continuous polling / file debounce loop without desktop notifications
agentsignals watch --interval 5.0

# Opt in to notifications and disable individual history records
agentsignals watch --interval 5.0 --notify --history-limit 0
```

Notifications are off by default for both `scan` and `watch`. With `--notify`, each scan that mines at least one session sends one aggregate desktop notification; scans that mine nothing send none. Watch automatically distills mined sessions when an LLM endpoint is set (`--llm-endpoint`, or `AGENTSIGNALS_LLM_ENDPOINT`); without one it logs a warning and only mines. Pass `--no-auto-distill` to turn distillation off. The supplied systemd watch unit runs `agentsignals watch` without `--notify`.

Both commands accept a non-negative `--history-limit`, defaulting to 50 recent scans. A limit of 0 removes individual history records while retaining the latest scan and cumulative totals. To use a different memories root, put the global option before the command, for example `agentsignals --memories-root /path/to/memories scan --history-limit 100`.

### 4. Systemd Service & Watch Unit Installation
```bash
# Dry run to inspect generated unit files
agentsignals install-systemd --dry-run

# Install user systemd units (~/.config/systemd/user/)
agentsignals install-systemd

# Enable and start the watch daemon
systemctl --user daemon-reload
systemctl --user enable --now agentsignals-watch.service
```

---

## opencode Sessions

agentsignals also mines [opencode](https://opencode.ai) sessions from its SQLite database. It mines user prompts, tool errors, failed shell commands, failed turns and the paths of touched files. It does not keep file content.

The database path is resolved in this order: the `--opencode-db` flag, the `OPENCODE_DB` environment variable, then `$XDG_DATA_HOME/opencode/opencode.db` (default `~/.local/share/opencode/opencode.db`). Databases for other release channels (`opencode-<channel>.db`) are not found automatically. Pass them with `--opencode-db`.

Access is read-only. agentsignals never writes to the database.

Subagent sessions are folded into their parent session, so each session family produces one dossier.

opencode and Claude Code sessions for the same directory share one `PROJECT_MEMORY.md`.

```bash
# Default: mine both sources
agentsignals scan

# Mine only Claude Code sessions (the database is never opened)
agentsignals --source claude scan

# Use a database from another release channel
agentsignals --opencode-db ~/.local/share/opencode/opencode-dev.db scan
```

`--source` takes a comma-separated list from `claude,opencode`. The default is `claude,opencode`. Both flags are global options and go before the command.

---

## Waybar Configuration Example

Add a custom module in `~/.config/waybar/config`:
```json
"custom/agentsignals": {
    "format": "{}",
    "return-type": "json",
    "exec": "cat /tmp/agentsignals_status.json 2>/dev/null || echo '{\"text\":\"🧠\"}'",
    "interval": 3,
    "signal": 8,
    "tooltip": true
}
```

The watcher sends `pkill -RTMIN+8 waybar` after each status write, so the module refreshes immediately. Polling every `interval` seconds remains the fallback.

The module text uses a stable `🧠 active | total mined` layout (for example, `🧠 1 | 42`); the first number is sessions still changing, and the second is the cumulative number mined. Hover for labeled counts, the latest scan time, last project (when available), cumulative totals, and up to three recent scans that mined sessions. Empty scans are omitted from that history.

Scan state is stored separately from the temporary Waybar payload in `<memories-root>/scan_status.json` (by default `~/.claude-mined-memories/scan_status.json`). It is written atomically after every scan, including empty ones, and survives restarts. Missing or corrupt state starts fresh. If writing fails, mining continues without saving state. Compositor hooks refresh Waybar without creating an additional desktop popup.

---

## Memory history

Mined memories live in `~/.claude-mined-memories/`. That directory is a git repository, so every change to it can be undone. Git is on by default for `scan`, `distill` and `watch`.

- **Baseline.** The first pass that finds no `.git` creates the repository and commits the existing tree as `baseline: existing memories`.
- **One commit per pass.** A scan or distill run that writes files makes one commit. A run that changes nothing makes no commit:

  ```text
  $ git -C ~/.claude-mined-memories log --oneline | head -4
  3f2a91c distill: 2 distilled
  9b0c5e1 scan: 1 mined, 1 re-mined (--force)
  4d7e2a8 external: changes found before scan
  1a6f3b0 baseline: existing memories
  ```

- **External changes.** If the tree is dirty when a pass starts, for example after a hand edit, it is committed first as `external: changes found before <pass>`. Whatever the pass then overwrites stays recoverable.
- **Restore a file.** Find the revision, then check it out:

  ```bash
  git -C ~/.claude-mined-memories log --oneline -- <slug>/<session-id>/dossier.json
  git -C ~/.claude-mined-memories checkout <rev> -- <slug>/<session-id>/dossier.json
  ```

- **Ignored files.** `scan_status.json` and temporary files (`*.tmp`, `.PROJECT_MEMORY.*.tmp`) are not committed.
- **Turn it off.** Pass the global `--no-git` flag, for example `agentsignals --no-git scan`.
- **Commit identity.** Commits use `agentsignals <agentsignals@localhost>`, whatever your global git config says.

An unchanged re-mine does not rewrite `dossier.json`. `watch` re-mines a session at most once every 60 seconds. A re-mine skipped for that reason is counted as "re-mined less than 60 s ago" in the scan summary. `scan` is not throttled.

## Running Tests

```bash
pytest tests/ -v
```
