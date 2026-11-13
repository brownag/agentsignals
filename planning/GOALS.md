# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: STATE_1.md (G1 closed at ff66a16; orchestration 2 drafted, awaiting approval)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- **[G5]** Compositor detection picks Sway only when Sway is running (`ipc.py:57` glob result is a generator, always truthy). It is the first task of `planning/EXECUTION_PLAN_2.md` (T2.1.1), and it gates G4.
  - Why now: G1 is closed. Orchestration 2 (G5, G6, G7, G9) is drafted and waits for user approval.

## Done (recent)

- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Status: Done (commits `72d3ff6`, `efa23c8`, `ff66a16`; `make check` exit 0). Oversized and binary files are stubs; skipped-only sessions get a dossier; SPEC §4.1 `test_filter_oversized_scratchpad` passes.
  - Size policy: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`), a default that can change without a redesign.

## Sequenced Goals (Dependency DAG)

- **[G9]** The four spec tests (SPEC.md §4.1) exist and pass for G1 and G2.
  - Depends on: G1, G2 (G2 done)
- **[G7]** Failed tool results are kept in the index, and the noise filter matches the README.
  - Depends on: G1
- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G3 (implemented, live timing check pending), G5

## Independent Backlog

- **[G6]** systemd units are correct on install: `DirectoryNotEmpty=` is set on `claudalizer.path`. (`daemon-reload` and the watch unit are already in place.) Verified missing in `systemd/claudalizer.path`.
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
