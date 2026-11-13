# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: STATE_2.md (orchestration 2 done: G5, G6, G7, G9 closed)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- None active. Orchestration 2 (G5, G6, G7, G9) is done on `g5-g6-g7-g9`. The next candidates are below.
  - Next: **G4** (needs the user's live G3 timing check, then G4 can start) or **G11** (independent cleanup).

## Done (recent)

- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Status: Done (`72d3ff6`, `efa23c8`, `ff66a16`; `make check` exit 0). Oversized and binary files are stubs; skipped-only sessions get a dossier; SPEC §4.1 `test_filter_oversized_scratchpad` passes.
  - Size policy: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`), a default that can change without a redesign.
- **[G5]** Compositor detection picks Sway only when a Sway socket exists.
  - Status: Done (`f547fe8`; `tests/test_ipc.py`, 5 passed).
- **[G6]** systemd path unit triggers only on a non-empty scan directory.
  - Status: Done (`21c8fad`; `DirectoryNotEmpty=/tmp/claude-1000`; `make systemd-dry-run` exit 0; not installed, which is user-run).
- **[G7]** Failed tool results are kept; successful git and Edit/Write results are filtered; exit code 0 is not a failure; README matches.
  - Status: Done (`2c0a311`, `0c7354f`).
- **[G9]** SPEC §4.1 and §4.3 tests exist and pass.
  - Status: Done (`test_slug_decoding`, `test_filter_oversized_scratchpad`, `test_jsonl_corrupt_recovery`, `test_git_state_filtering`; `test_sway_dispatch_when_swaysock_present`, `test_hyprland_dispatch`, `test_headless_environment_no_crash`). SPEC §4.2 (distiller) is not covered.

## Sequenced Goals (Dependency DAG)

- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G3 (implemented, live timing check pending, user-run), G5 (done)

## Independent Backlog

- **[G11]** Duplicate setup code and dead fields are removed (`cli.py:36-66`, `cli.py:94-117`, `ipc.py:140-151`).
  - Depends on: none

## Deferred

- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Trigger: a local LLM endpoint is in use.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.

## Done

- **[G2]** Dossier writes are atomic, so a crash never leaves a half-written index.
  - Status: Done (commit `80f5ba4`; crash and temp-file tests pass).
- **[G8]** Size policy for scratchpad files.
  - Status: Decided: 250 KiB, no larger than necessary. Oversized files are recorded as stubs (see G1).

## Blocked / Pruned

- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Status: Implemented (commits `70a82e2`, `420971f`); awaiting the live timing check, which is user-run.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
