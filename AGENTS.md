# AGENTS.md - claudalizer

## Quick Start

* **Install (editable, dev extras)**: `make install`
* **Install (user, no dev extras)**: `make install-user`
* **Test all**: `make test` (pytest over `tests/`)
* **Test with coverage**: `make test-cov`
* **Lint**: `make lint` (ruff over `claudalizer/` and `tests/`)
* **Check (lint + test)**: `make check`
* **On-demand scan**: `make scan` (runs `claudalizer scan --no-debounce`)
* **Distill memories**: `make distill`
* **Watch loop (foreground)**: `make watch` (interval from `WATCH_INTERVAL`, default 3.0 s)
* **Preview systemd units**: `make systemd-dry-run`
* **Install and enable systemd units**: `make systemd-install`
* **Status / remove systemd units**: `make systemd-status` / `make systemd-uninstall`
* **All targets**: `make help`

## Find Things

* `claudalizer/cli.py` - argparse entry point (`main`), subcommands `scan`, `distill`, `watch`, `install-systemd`
* `claudalizer/miner.py` - session discovery, settle/debounce rules, transcript parsing, scratchpad snapshots, dossiers
* `claudalizer/distiller.py` - turns dossiers into `memory.md` and per-project `PROJECT_MEMORY.md`
* `claudalizer/ipc.py` - desktop notifications (`notify-send`), Sway/Hyprland detection, Waybar signalling
* `tests/` - pytest suite; `test_miner.py` holds all current tests
* `systemd/` - unit templates (`claudalizer.path`, `claudalizer.service`, `claudalizer-watch.service`) and the tmpfiles config. `%h/.local/bin/claudalizer` is replaced at install time.
* `planning/` - goals and specs (`GOALS.md`, `SPEC.md`). Read `GOALS.md` for the current goal sequence.
* `README.md` - user-facing usage, Waybar example, test instructions

## Workflows

* **Change a module**: edit under `claudalizer/`, add or adjust tests in `tests/`, then `make check`.
* **Change a unit file**: edit the template under `systemd/`, run `make systemd-dry-run` to review the rendered output, then `make systemd-install` to apply it.
* **Add a CLI flag**: add it to the matching subparser in `build_parser()` in `cli.py`. Defaults there are the source of truth; `Makefile` targets pass explicit values where they differ.
* **Plan larger work**: record goals in `planning/GOALS.md`; use the plan-first or plan-wave skills to write execution plans.

## Infrastructure

* **Session source (volatile)**: `/tmp/claude-1000` (`DEFAULT_TMP_ROOT` in `miner.py`). Layout: `<slug>/<session-id>/scratchpad/`. Directories whose names don't start with `-` are skipped (see `scan_and_mine`).
* **Transcripts (durable)**: `~/.claude/projects/<slug>/<session-id>.jsonl`
* **Mined output (durable)**: `~/.claude-mined-memories/` (`DEFAULT_MEMORIES_ROOT`). Per session: `dossier.json`, `scratchpad/` copy, `memory.md` after distillation. Per project: `PROJECT_MEMORY.md`.
* **Lock file**: `/tmp/claudalizer.lock` (`DEFAULT_LOCK_FILE`). Mining takes an exclusive `flock` with a 10 s timeout.
* **Settle window**: 2 s (`SETTLE_DEBOUNCE_SECONDS`). Mining size cap per scratchpad file: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`).
* **Installed user units**: `~/.config/systemd/user/claudalizer.service`, `claudalizer.path`, `claudalizer-watch.service`
* **Installed tmpfiles config**: `~/.config/user-tmpfiles.d/claudalizer.conf`
* **Entry point**: `claudalizer` console script, installed to `~/.local/bin/claudalizer` in the user install.
* **Dependencies**: none at runtime (stdlib only, per `pyproject.toml` and the README). Dev: pytest, pytest-cov, ruff, mypy.
* **Python**: 3.10 or newer.

## Non-Obvious System Behaviors

* `systemd.path` (`PathModified=/tmp/claude-1000`) does not fire on writes inside session subdirectories. The watch service is the path that catches nested scratchpad writes.
* A session with an existing `dossier.json` is re-mined only when a file under its scratchpad is newer than that dossier. Otherwise it is skipped.
* Sessions with no user prompts, no tool errors, and no scratchpad files produce no dossier.
* `make lint` ends with `|| echo`, so it never fails the build. Read its output for ruff findings.
* `watch` defaults `--notify` and `--auto-distill` to on, and `store_true` with `default=True` means they cannot be turned off from the CLI.

## System Boundaries & Operational Rules

### Always
* Run `make test` after changing `claudalizer/` or `tests/`.
* Use `make systemd-dry-run` before installing unit changes.

### Ask First
* Running `make systemd-install` or `make systemd-uninstall` (changes the user's systemd state).
* Running `claudalizer watch` or `make watch` against live `/tmp/claude-1000` for long periods (it notifies and distills every real session).
* Changing the settle window, size cap, or lock timeout.

### Never
* Delete or modify contents under `/tmp/claude-1000` or `~/.claude-mined-memories/` directly; use the CLI.
* Add runtime dependencies (the project is stdlib-only).

## Secondary Documentation Index
* `README.md` - usage, Waybar config, and test instructions.
* `planning/SPEC.md` - engineering specification.
* `planning/GOALS.md` - goal graph and current focus.
