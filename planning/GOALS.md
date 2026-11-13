# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: STATE_3.md (orchestration 3 executed: G4 implemented, live check pending); magic-wand re-rank (G14 circled)

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included.

## Circled Goal (Active)

- **[G14]** The Waybar refresh signal is confirmed not to terminate Waybar on this machine, before the G4 code is installed.
  - Why now: G4's code sends `pkill -RTMIN+8 waybar` after every status write. The plan assumed this is a no-op when no module sets `"signal": 8`. If Waybar has no handler for that signal, it terminates, and every scan would kill the bar. Answering this unblocks G4's install and live check, and decides whether G4 keeps this mechanism.
  - Exit criteria: a probe on a renamed copy of the Waybar binary, with no `signal` config, shows the process survives `kill -RTMIN+8 <pid>`. If it doesn't, G4 switches to another mechanism, and that change is recorded in `EXECUTION_PLAN_3.md`.
  - First action: copy `/usr/bin/waybar` to a scratch name (e.g. `waybar-probe`, not `waybar`), start it with a throwaway config, and send `kill -RTMIN+8` to its PID. Do not use `pkill`, which also matches the real Waybar.
  - Depends on: none
  - Risk: R1 in `planning/EXECUTION_PLAN_3.md`. Do not run `make install-user` until this is answered.

## Sequenced Goals (Dependency DAG)

- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Why now: the user-visible goal. Code is in place (commits `a2eefa3`, `5ab4552`, `b651913`); mocked tests and `make check` pass.
  - Exit criteria: after a scan writes a dossier, the Waybar module re-reads the status within a few seconds, verified by a test that checks the refresh call is made. `make check` passes. Live refresh check is user-run.
  - First action: after G14 passes, run the live check (add the module per README, run `claudalizer scan`, confirm the update).
  - Depends on: G14 (install gate), G3 live timing check (user-run; needed only to verify timing).
  - Status: implemented; live refresh check pending (user-run).

- **[G16]** `--notify` and `--auto-distill` can be turned off from the CLI.
  - Why here: a real defect (`store_true` with `default=True` cannot be disabled). Small, and it touches `cli.py`, so it goes before G11.
  - Exit criteria: a test shows `--no-notify` and `--no-auto-distill` (or equivalent) disable each feature, and the defaults stay on.
  - Depends on: none

- **[G15]** SPEC §4.2 (distiller) behavior has passing tests.
  - Why here: the distiller is the least-tested part (G9 note). Independent of the Waybar path.
  - Exit criteria: each SPEC §4.2 requirement has a test, and `make test` passes.
  - Depends on: none

- **[G11]** Duplicate setup code and dead fields are removed (`cli.py:36-66`, `cli.py:94-117`, `ipc.py:140-151`).
  - Why here: low system-wide leverage. The `cli.py` setup is duplicated in `handle_scan` and `handle_watch`. The "dead fields" claim is not yet verified.
  - Depends on: G16 (same file; do after it)

## Independent Backlog

_(none)_

## Deferred

- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Trigger: a local LLM endpoint is in use.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.
- **[G17]** `make lint` reports zero ruff findings and fails the build on findings. 12 pre-existing findings; `make lint` ends with `|| echo` so it never fails.
  - Trigger: before lint is wired into CI or a release.

## Done

- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Status: Done (`72d3ff6`, `efa23c8`, `ff66a16`; `make check` exit 0). Oversized and binary files are stubs; skipped-only sessions get a dossier; SPEC §4.1 `test_filter_oversized_scratchpad` passes.
  - Size policy: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`), a default that can change without a redesign.
- **[G2]** Dossier writes are atomic, so a crash never leaves a half-written index.
  - Status: Done (commit `80f5ba4`; crash and temp-file tests pass).
- **[G5]** Compositor detection picks Sway only when a Sway socket exists.
  - Status: Done (`f547fe8`; `tests/test_ipc.py`, 5 passed).
- **[G6]** systemd path unit triggers only on a non-empty scan directory.
  - Status: Done (`21c8fad`; `DirectoryNotEmpty=/tmp/claude-1000`; `make systemd-dry-run` exit 0; not installed, which is user-run).
- **[G7]** Failed tool results are kept; successful git and Edit/Write results are filtered; exit code 0 is not a failure; README matches.
  - Status: Done (`2c0a311`, `0c7354f`).
- **[G8]** Size policy for scratchpad files.
  - Status: Decided: 250 KiB, no larger than necessary. Oversized files are recorded as stubs (see G1).
- **[G9]** SPEC §4.1 and §4.3 tests exist and pass.
  - Status: Done (`test_slug_decoding`, `test_filter_oversized_scratchpad`, `test_jsonl_corrupt_recovery`, `test_git_state_filtering`; `test_sway_dispatch_when_swaysock_present`, `test_hyprland_dispatch`, `test_headless_environment_no_crash`). SPEC §4.2 (distiller) is not covered; see G15.

## Blocked / Pruned

- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Status: Blocked / External Watch. Implemented (commits `70a82e2`, `420971f`); awaiting the live timing check, which is user-run (`/tmp/claude-1000`, per AGENTS.md ask-first). G4's timing verification needs it.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
