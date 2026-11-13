# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-12
Source State: magic-wand re-rank after G14 closed (focus: PROJECT_MEMORY.md quality). Prior: STATE_4.md.

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included. Current focus: the mined per-project memory (`~/.claude-mined-memories/<slug>/PROJECT_MEMORY.md`) is correct, derived, and worth reading.

Definition of "good" for the focus (working criteria, to be confirmed by the user):
1. One section per session, no duplicates after any number of re-runs, including `--force`.
2. Every section is derived from that session. No boilerplate directives.
3. Tool-friction lines name the failing command and its real error text.
4. Blind-alleys lists real work, not the claudalizer's own test runs.
5. The format is written down in `planning/SPEC.md` §4.2, so tests can check it.

Evidence (2026-11-12, `~/.claude-mined-memories`): 8 project files, 22 sections; 17 of 22 sections carry the generic "Maintain strict idempotency..." fallback; most tool-friction entries are "None detected" or bare exit codes; blind-alleys lists claudalizer's own `g3-accept` and `rewrite-check` scratch. Code read: `_append_to_project_memory` appends on every distill, including `--force` (not yet reproduced).

## Circled Goal (Active)

- **[G15]** SPEC §4.2 (distiller) is specified and tested, including the PROJECT_MEMORY.md format.
  - Why now: every fix to the project memory changes `claudalizer/distiller.py`. Without tests that pin the current behaviour and the target behaviour, the fixes can't be checked. This goal unblocks G18–G21.
  - Exit criteria: SPEC §4.2 states the PROJECT_MEMORY.md format and the five criteria above. Each one has a test in `tests/test_distiller.py`. Tests that describe target behaviour that is not yet built (duplicates on `--force`, generic fallback) are marked `xfail` with the goal id. `make test` passes.
  - First action: add a PROJECT_MEMORY subsection to `planning/SPEC.md` §4.2, then write the tests against `synthesize_offline_memory_block` and `_append_to_project_memory` using `tmp_path`.
  - Depends on: none.
  - Files in scope: `planning/SPEC.md`, `tests/test_distiller.py` (new), `tests/conftest.py` only if a fixture is needed.

## Sequenced Goals (Dependency DAG)

- **[G18]** PROJECT_MEMORY.md is rebuilt from the session `memory.md` files, not appended to.
  - Why here: fixes the duplicate-on-`--force` risk and keeps the file in sync with the session files it summarises.
  - Exit criteria: distilling the same session twice with `--force` leaves one section for it. The G15 duplicate test turns from `xfail` to pass. `make test` passes.
  - Depends on: G15 (test for the duplicate case must exist first).
  - Files in scope: `claudalizer/distiller.py` (`_append_to_project_memory`, `distill_session`), `tests/test_distiller.py`.

- **[G19]** Directives come from the session only. The generic fallback is removed.
  - Why here: 17 of 22 sections carry the same line. It is noise, and it hides the sections that do have content.
  - Exit criteria: with no matching error, the section reads "None detected", not the fallback line. The G15 fallback test turns from `xfail` to pass.
  - Depends on: G18 (same function; do after it, not in parallel).
  - Files in scope: `claudalizer/distiller.py` (`synthesize_offline_memory_block`, the directives block), `tests/test_distiller.py`.

- **[G20]** Blind-alleys excludes the claudalizer's own test scratch and lists only real work.
  - Why here: the current list is mostly test-run files from the claudalizer's own suite and `g3-accept` runs.
  - Exit criteria: a session whose scratchpad holds only test-run files (under a `g3-accept` / `rewrite-check` / `tmp_path`-style path) yields "No ephemeral scratchpads recorded." A test covers it.
  - Depends on: G15. Same file as G18–G19; serialise after G19.
  - Files in scope: `claudalizer/distiller.py` (scratchpad listing), `claudalizer/miner.py` only if the filter belongs there, `tests/test_distiller.py`.

- **[G21]** Tool-friction lines show the failing command and its real error text, not a bare exit code and first line.
  - Why here: most entries are "Exit code 2" with a first line that says nothing about the failure.
  - Exit criteria: a test with a failing `pytest` call shows the error line from its output. Entries with no error text are dropped, not printed as "Exit code N".
  - Depends on: G19 (same section of the generator).
  - Files in scope: `claudalizer/distiller.py` (friction section), `tests/test_distiller.py`.

- **[G16]** `--notify` and `--auto-distill` can be turned off from the CLI.
  - Why here: a real defect (`store_true` with `default=True` cannot be disabled). Small, and it touches `cli.py`, so it goes before G11.
  - Exit criteria: a test shows `--no-notify` and `--no-auto-distill` (or equivalent) disable each feature, and the defaults stay on.
  - Depends on: none. Independent of the focus; can run in its own wave.

- **[G11]** Duplicate setup code and dead fields are removed (`cli.py:36-66`, `cli.py:94-117`, `ipc.py:140-151`).
  - Why here: low system-wide leverage. The `cli.py` setup is duplicated in `handle_scan` and `handle_watch`. The "dead fields" claim is not yet verified.
  - Depends on: G16 (same file; do after it)

## Independent Backlog

- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Why here: the user-visible goal, but its code is done. The live refresh check is user-run and does not block the focus.
  - Exit criteria: the user confirms, after `make systemd-install` and a Waybar restart, that the module updates within a few seconds after `claudalizer scan`. Recorded in `planning/STATE_4.md` when reported.
  - Depends on: none. The G3 timing check is user-run and needed only to verify timing.
  - Status: implemented; Waybar module installed by `install-systemd` (`922db54`). Styling added to `~/.config/waybar/style.css` (outside the repo). Live check pending.

## Deferred

- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Trigger: a local LLM endpoint is in use. Relevant to the focus: the LLM path is the one that writes most of the memory text, and it is not yet tested.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.
- **[G17]** `make lint` reports zero ruff findings and fails the build on findings. 12 pre-existing findings; `make lint` ends with `|| echo` so it never fails.
  - Trigger: before lint is wired into CI or a release.

## Done

- **[G14]** The Waybar refresh signal is confirmed not to terminate Waybar on this machine, before the G4 code is installed.
  - Status: Done (orchestration 4, `planning/STATE_4.md` `## T4.1.1`). Headless probe on a renamed Waybar 0.9.24 copy under Sway 1.9: `RESULT: survives-RTMIN8=yes`; positive control (`"signal": 8` module) `refresh-with-signal8=yes`; `path=survives`. No code change. G4 keeps `pkill -RTMIN+8 waybar`.
- **[G1]** Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops.
  - Status: Done (`72d3ff6`, `efa23c8`, `ff66a16`; `make check` exit 0). Oversized and binary files are stubs; skipped-only sessions get a dossier; SPEC §4.1 `test_filter_oversized_scratchpad` passes.
  - Size policy: 250 KiB (`MAX_SCRATCHPAD_FILE_BYTES`), a default that can change without a redesign.
- **[G2]** Dossier writes are atomic, so a crash never leaves a half-written index.
  - Status: Done (commit `80f5ba4`; crash and temp-file tests pass).
- **[G5]** Compositor detection picks Sway only when a Sway socket exists.
  - Status: Done (`f547fe8`; `tests/test_ipc.py`, 5 passed).
- **[G6]** systemd path unit triggers only on a non-empty scan directory.
  - Status: Done (`21c8fad`; `DirectoryNotEmpty=/tmp/claude-1000`; `make systemd-dry-run` exit 0; not installed, which is user-run).
  - Open: `claudalizer.service` hit `start-limit-hit` on 2026-11-12 at 23:11 (three runs in about a second). Cause not yet found. Tracked as a follow-up to G6, not part of the focus.
- **[G7]** Failed tool results are kept; successful git and Edit/Write results are filtered; exit code 0 is not a failure; README matches.
  - Status: Done (`2c0a311`, `0c7354f`).
- **[G8]** Size policy for scratchpad files.
  - Status: Decided: 250 KiB, no larger than necessary. Oversized files are recorded as stubs (see G1).
- **[G9]** SPEC §4.1 and §4.3 tests exist and pass.
  - Status: Done (`test_slug_decoding`, `test_filter_oversized_scratchpad`, `test_jsonl_corrupt_recovery`, `test_git_state_filtering`; `test_sway_dispatch_when_swaysock_present`, `test_hyprland_dispatch`, `test_headless_environment_no_crash`). SPEC §4.2 (distiller) is not covered; see G15.
- **[G_wbcfg]** `claudalizer install-systemd` adds the Waybar module to the user's config, idempotently, with a backup.
  - Status: Done (`922db54`; `claudalizer/waybar_config.py`, 10 tests; `make test` 40 passed). Applies on the next `make systemd-install`.

## Blocked / Pruned

- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Status: Blocked / External Watch. Implemented (commits `70a82e2`, `420971f`); awaiting the live timing check, which is user-run (`/tmp/claude-1000`, per AGENTS.md ask-first). G4's timing verification needs it.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
