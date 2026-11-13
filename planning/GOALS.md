# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: none (magic-wand re-rank after G2 verified done; G8 decided)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Why now: unblocks G7 and G9, and it is the core durability goal. Its only open prerequisite (G8) is now decided.
  - Exit criteria: files over the 250 KiB cap are recorded as stubs (name, size, reason) rather than dropped; the SPEC.md L783-786 tests for G1 exist and pass; `make check` passes.
  - Size policy (decided): 250 KiB, the existing `MAX_SCRATCHPAD_FILE_BYTES`. Keep it no larger than necessary. Treat it as a default, not a hard rule, so it can be lowered or raised later without a redesign.
  - First action: read `planning/SPEC.md` L783-786 and the scratchpad snapshot code in `claudalizer/miner.py`, then write the failing test for an oversized-file stub in `tests/test_miner.py`.

## Sequenced Goals (Dependency DAG)

- **[G9]** The four spec tests (SPEC.md L783-786) exist and pass for G1 and G2.
  - Depends on: G1, G2 (G2 done)
- **[G7]** Failed tool results are kept in the index, and the noise filter matches the README.
  - Depends on: G1
- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G3 (implemented, live timing check pending), G5

## Independent Backlog

- **[G5]** Compositor detection picks Sway when Sway is running, and the glob check works (`ipc.py:42-58`).
  - Depends on: none
- **[G6]** systemd units are correct on install: `DirectoryNotEmpty=` is set on `claudalizer.path`. (`daemon-reload` and the watch unit are already in place.)
  - Depends on: none
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
