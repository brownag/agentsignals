# AGENTS.md - agentsignals

## Quick Start

* **Install (editable, dev extras)**: `make install`
* **Install (user, no dev extras)**: `make install-user`
* **Test all**: `make test` (pytest over `tests/`)
* **Test with coverage**: `make test-cov`
* **Lint**: `make lint` (ruff over `agentsignals/` and `tests/`)
* **Check (lint + test)**: `make check`
* **On-demand scan**: `make scan` (runs `agentsignals scan --no-debounce`)
* **Distill memories**: `make distill`
* **Watch loop (foreground)**: `make watch` (interval from `WATCH_INTERVAL`, default 3.0 s)
* **Preview systemd units**: `make systemd-dry-run`
* **Install and enable systemd units**: `make systemd-install`
* **Status / remove systemd units**: `make systemd-status` / `make systemd-uninstall`
* **All targets**: `make help`

## Find Things

* `agentsignals/cli.py` - argparse entry point (`main`), subcommands `scan`, `distill`, `watch`, `install-systemd`
* `agentsignals/miner.py` - core scan loop, settle/debounce rules, transcript parsing, scratchpad snapshots, dossiers. It runs each enabled source in turn.
* `agentsignals/sources/` - session adapters: `claude_code.py` (Claude Code), `opencode.py` (opencode SQLite reader), `opencode_schema.py` (schema guard and read-only open)
* `agentsignals/distiller.py` - turns dossiers into `memory.md` and per-project `PROJECT_MEMORY.md`
* `agentsignals/memory_git.py` - git history for the memories root (`MemoryRepo`: baseline, external and pass commits)
* `agentsignals/ipc.py` - desktop notifications (`notify-send`), Sway/Hyprland detection, Waybar signalling
* `tests/` - pytest suite. `test_miner.py` (Claude Code), `test_source_core.py` (core loop), `test_opencode_fixture.py`, `test_opencode_source.py`, `test_opencode_schema.py`. `opencode_fixture.py` builds test databases. `conftest.py` points `OPENCODE_DB` and `XDG_DATA_HOME` at missing paths so tests never read the live database.
* `systemd/` - unit templates (`agentsignals.service`, `agentsignals-watch.service`) and tmpfiles config. Their executable is `agentsignals`.
* `planning/` - goals and specs (`GOALS.md`, `SPEC.md`). Read `GOALS.md` for the current goal sequence.
* `README.md` - user-facing usage, Waybar example, test instructions

## Workflows

* **Change a module**: edit under `agentsignals/`, add or adjust tests in `tests/`, then `make check`.
* **Change a unit file**: edit the template under `systemd/`, run `make systemd-dry-run` to review the rendered output, then `make systemd-install` to apply it.
* **Add a CLI flag**: add it to the matching subparser in `build_parser()` in `cli.py`. Defaults there are the source of truth; `Makefile` targets pass explicit values where they differ.
* **Plan larger work**: record goals in `planning/GOALS.md`; use the plan-first or plan-wave skills to write execution plans.

## Infrastructure

* **Session source (volatile)**: `/tmp/claude-1000` (`DEFAULT_TMP_ROOT` in `miner.py`). Layout: `<slug>/<session-id>/scratchpad/`. Directories whose names don't start with `-` are skipped (see `scan_and_mine`).
* **opencode database (read-only)**: `--opencode-db`, else `$OPENCODE_DB`, else `$XDG_DATA_HOME/opencode/opencode.db` (default `~/.local/share/opencode/opencode.db`). Opened read-only; agentsignals never writes to it.
* **Transcripts (durable)**: `~/.claude/projects/<slug>/<session-id>.jsonl`
* **Memories root is a git repo**: `~/.claude-mined-memories/` has its own `.git`, created by the first pass. The path is unchanged by the rename. `--no-git` turns this off.
* **Mined output (durable)**: `~/.claude-mined-memories/` (`DEFAULT_MEMORIES_ROOT`). Per session: `dossier.json`, `scratchpad/` copy, `memory.md` after distillation. Per project: `PROJECT_MEMORY.md`.
* **Lock file**: `/tmp/agentsignals.lock` (`DEFAULT_LOCK_FILE`). Mining takes an exclusive `flock` with a 10 s timeout.
* **Settle window**: 2 s (`SETTLE_DEBOUNCE_SECONDS`). Mining size cap per scratchpad file: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`).
* **Installed user units**: `~/.config/systemd/user/agentsignals.service`, `agentsignals-watch.service` (no path unit)
* **Installed tmpfiles config**: `~/.config/user-tmpfiles.d/agentsignals.conf`
* **Entry point**: `agentsignals` console script.
* **Dependencies**: none at runtime (stdlib only, per `pyproject.toml` and the README). Dev: pytest, pytest-cov, ruff, mypy.
* **Python**: 3.10 or newer.

## Non-Obvious System Behaviors

* `systemd.path` (`PathModified=/tmp/claude-1000`) does not fire on writes inside session subdirectories. The watch service is the path that catches nested scratchpad writes.
* A session with an existing `dossier.json` is re-mined only when a file under its scratchpad is newer than that dossier. Otherwise it is skipped.
* Sessions with no user prompts, no tool errors, and no scratchpad files produce no dossier.
* `make lint` fails on ruff findings. It only skips, printing "ruff not found, skipping.", when ruff is not installed.
* An opencode session family is mined when it is idle, or after 600 s with no change (`OPENCODE_QUIET_SECONDS`).
* `watch` skips the opencode queries on a tick only when the database and `-wal` mtimes are unchanged and the previous pass found no unsettled family.
* An unchanged re-mine does not rewrite `dossier.json`: the new dossier must equal the stored one (ignoring `scan_timestamp`) and the scratchpad copies must be byte-identical. Otherwise its mtime is bumped with `os.utime`.
* `watch` skips a session whose `dossier.json` is younger than 60 s (`WATCH_MIN_REMINE_SECONDS`). `scan` is not throttled.
* `file_lock` is never nested. The miner commits inside the lock it already holds. The distiller takes the lock only for its writes and its pass commit, never around the LLM call.
* `--notify` is off by default for `scan` and `watch`. `watch` distills by default; `--no-auto-distill` turns it off.

## System Boundaries & Operational Rules

### Always
* Run `make test` after changing `agentsignals/` or `tests/`.
* Use `make systemd-dry-run` before installing unit changes.

### Ask First
* Running `make systemd-install` or `make systemd-uninstall` (changes the user's systemd state).
* Running `agentsignals watch` or `make watch` against live `/tmp/claude-1000` for long periods (it notifies and distills every real session).
* Changing the settle window, size cap, or lock timeout.

### Never
* Delete or modify contents under `/tmp/claude-1000` or `~/.claude-mined-memories/` directly; use the CLI.
* Write to `opencode.db`.
* Run git commands that rewrite history in `~/.claude-mined-memories`.
* Add runtime dependencies (the project is stdlib-only).

## Secondary Documentation Index
* `README.md` - usage, Waybar config, and test instructions.
* `planning/SPEC.md` - engineering specification.
* `planning/GOALS.md` - goal graph and current focus.
