# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: none (initial magic-wand pass)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within a few seconds, with no missed events.
  - Why now: gates G4 and G6, and bounds the loss window for G1.
  - Exit criteria: a test writes a file in a session dir and sees a scan start within N seconds on a running user systemd, including rewrites of existing files.
  - First action: hand to plan-wave to confirm whether `PathModified=` on a directory fires on file rewrites inside it, before changing any unit.

## Sequenced Goals (Dependency DAG)

- **[G2]** Dossier writes are atomic, so a crash never leaves a half-written index.
  - Depends on: none
- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Depends on: G2, G8
- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G3, G5
- **[G6]** systemd units install and run: `DirectoryNotEmpty=` set, `daemon-reload` run, `watch` runnable as a user service.
  - Depends on: G3
- **[G9]** The four spec tests (SPEC.md L783-786) exist and pass for G1 and G2.
  - Depends on: G1, G2
- **[G7]** Failed tool results are kept in the index, and the noise filter matches the README.
  - Depends on: G1

## Independent Backlog

- **[G5]** Compositor detection picks Sway when Sway is running, and the glob check works (`ipc.py:42-58`).
- **[G11]** Duplicate setup code and dead fields are removed (`cli.py:36-66`, `cli.py:94-117`, `ipc.py:140-151`).

## Deferred

- **[G8]** The size policy is decided: 250 KiB or 256 KiB, and oversized files are recorded as stubs rather than dropped.
  - Trigger: owner picks 250 KiB or 256 KiB. Blocks G1.
- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Trigger: a local LLM endpoint is in use.

## Blocked / Pruned

- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
