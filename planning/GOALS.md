# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: none (magic-wand re-rank after G3 implementation)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- **[G2]** Dossier writes are atomic, so a crash never leaves a half-written index.
  - Why now: small, completable within a day, and it unblocks G1 (durable capture) and G9 (spec tests). It touches only the dossier write path in `miner.py`.
  - Exit criteria: a test that simulates a failure during the dossier write leaves the previous `dossier.json` intact, and a successful write leaves no temp file behind.
  - First action: write the failing crash test in `tests/test_miner.py`, then change the write in `_mine_session` to write a temp file and `os.replace` it into place.

## Sequenced Goals (Dependency DAG)

- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Depends on: G2, G8 (G8 needs an owner decision)
- **[G9]** The four spec tests (SPEC.md L783-786) exist and pass for G1 and G2.
  - Depends on: G1, G2
- **[G7]** Failed tool results are kept in the index, and the noise filter matches the README.
  - Depends on: G1
- **[G5]** Compositor detection picks Sway when Sway is running, and the glob check works (`ipc.py:42-58`).
  - Depends on: none
- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G3 (implemented, verification pending), G5

## Independent Backlog

- **[G6]** systemd units are correct on install: `DirectoryNotEmpty=` is set on `claudalizer.path`. (`daemon-reload` and the watch unit are already in place.)
  - Depends on: none
- **[G11]** Duplicate setup code and dead fields are removed (`cli.py:36-66`, `cli.py:94-117`, `ipc.py:140-151`).
  - Depends on: none

## Deferred

- **[G8]** Size policy: 250 KiB or 256 KiB, and oversized files are recorded as stubs rather than dropped.
  - Trigger: owner picks 250 KiB or 256 KiB. Blocks G1.
- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Trigger: a local LLM endpoint is in use.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.

## Blocked / Pruned

- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Status: Implemented (commits `70a82e2`, `420971f`); awaiting the live timing check, which is user-run.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
