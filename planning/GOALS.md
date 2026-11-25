# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-24
Source State: STATE_10.md (G23 complete). Re-ranked 2026-11-24 with Magic Wand: G16, G_dead-notify and G17 done; the remaining open goals are user-run checks.

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included. Current focus: confirm the installed system works live.

## Circled Goal (Active)

- **[G_live]** After one `make systemd-install`, the installed units and Waybar module are confirmed working on this machine.
  - Why now: no agent-doable goal is open. This one user-run step settles three goals: G4, G6-followup and G3.
  - Exit criteria: (1) Waybar updates within a few seconds after `claudalizer scan` (G4); (2) `systemctl --user status claudalizer.service` shows no `start-limit-hit` after install (G6-followup); (3) a write under `/tmp/claude-1000` produces a scan within 10 s (G3). Results recorded in `planning/STATE_4.md` or a new STATE file.
  - First action: you run `make systemd-dry-run`, then `make systemd-install` (ask-first per AGENTS.md), then restart Waybar.
  - Status: User-run.

## Sequenced Goals (Dependency DAG)

- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Depends on: G_live. Code done (`922db54`, G23 commits); styling in `~/.config/waybar/style.css` (outside the repo).
- **[G6-followup]** `claudalizer.service` no longer hits `start-limit-hit`.
  - Depends on: G_live. Last failure 2026-11-12 23:11; the path unit that caused repeated starts was removed.
- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Depends on: G_live. Implemented (`70a82e2`, `420971f`).

## Independent Backlog

- **[G_llm-live]** `CLAUDALIZER_LLM_ENDPOINT=http://localhost:8090/v1/chat/completions claudalizer distill --force` writes memory blocks with a title and an Objective line from real data.
  - Status: User-run (needs the local LLM endpoint). Code done under G_memlab, G_memlab-open and G10.

## Deferred

- **[G22]** Hand-written notes survive rebuilds and reach Claude through a standard injection format.
  - Trigger: you need to write notes by hand that must persist. Today a rebuild discards hand edits (G18, by design). The likely shape is a separate durable file that the distiller reads, not an edit to PROJECT_MEMORY.md.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.

## Done

- **[G16]** `watch --auto-distill` can be turned off from the CLI.
  - Status: Done (2026-11-24). `argparse.BooleanOptionalAction` with `default=True`; `--no-auto-distill` disables it. `test_watch_auto_distill_can_be_turned_off`; SPEC §3.4, README and AGENTS.md updated.
- **[G_dead-notify]** Uncalled `notify_extraction` removed from `claudalizer/ipc.py`.
  - Status: Done (2026-11-24). Function and its test call removed.
- **[G17]** `make lint` reports zero ruff findings and fails the build on findings.
  - Status: Done (2026-11-24). 9 findings auto-fixed (unused imports, one placeholder-less f-string). `make lint` now exits non-zero on findings (verified with a probe file). `make check` 96 passed.
- **[G10]** Distillation LLM client matches the spec (auth, temperature, endpoint, retry).
  - Status: Done (2026-11-17). The spec was silent on temperature, auth and retry; it now states temperature 0.2, no auth (local endpoint), and one attempt with offline fallback. Two tests pin these. `make test` 95 passed. The real-data run is user-run.
- **[G_memlab-open]** LLM-written memory blocks get a title and Objective line.
  - Status: Done (2026-11-17). Commit `0f73863` (`frame_llm_block`). Covered by `tests/test_distiller.py`; SPEC §3.2 documents it.

- **[G23]** Waybar presents persistent latest-scan details and cumulative totals/history; desktop notifications are opt-in, one per mining batch, and no compositor popup.
  - Status: Done (2026-11-17). `3d1047f` (persistent scan history), `f6dd869` (opt-in notify, scan recording), `0eb1ee9` (docs), `00c836f` (headline). `make test` 93 passed. Dead `notify_extraction` in `claudalizer/ipc.py` remains uncalled (see Independent Backlog). Live Waybar check is user-run (G4).

- **[G_memlab]** Memory blocks say what each session was for, and the LLM path works without extra flags.
  - Status: Done in code (orchestration 9, `planning/STATE_9.md`): `d3ebd6f` (endpoint from `CLAUDALIZER_LLM_ENDPOINT`; thinking off; 1024 tokens; 300 s timeout; empty reply warns), `fd42669` (Objective line in the offline block), `3a33a05` (SPEC). `make test` 73 passed. Real-data run pending (user): `CLAUDALIZER_LLM_ENDPOINT=http://localhost:8090/v1/chat/completions claudalizer distill --force`.
  - Resolved: LLM-written blocks now get the title and Objective line (`0f73863`, see G_memlab-open).
- **[G_scan]** `claudalizer scan` mines sessions whose transcript changed, and says what it skipped.
  - Status: Done (`b515b9e`). Before: a transcript-only change was never re-mined (23 sessions in the real data), and skipped sessions were silent, so scan printed `Mined 0`. Now the skip check also compares the transcript mtime, and scan prints `Skipped: N active, N already up to date, N with no content`, naming the active sessions. Tests in `tests/test_scan_report.py`. `make test` 65 passed.
- **[G20]** The blind-alleys list excludes the claudalizer's own test scratch.
  - Status: Done (orchestration 8, `planning/STATE_8.md`). `5d0cef0` drops scratch under `g3-accept` and `rewrite-check`. `make test` 60 passed.
- **[G21]** Tool-friction lines show the failing command and its real error line.
  - Status: Done (orchestration 8). `1c4a6d6` shows the first line with an error marker; entries with none are dropped. SPEC `bcaac5d`.
- **[G19]** Directives come from the session only. The generic fallback is removed.
  - Status: Done (orchestration 7, `planning/STATE_7.md`). `579b758` writes `- None detected.` when no error matches a pattern or there are no errors. SPEC `planning` commit follows. `make test` 56 passed, 2 xfailed. Real PROJECT_MEMORY.md files show the old fallback until the next distill.
- **[G18]** PROJECT_MEMORY.md is rebuilt from the session `memory.md` files, not appended to.
  - Status: Done (orchestration 6, `planning/STATE_6.md`). `c5162a6` rebuilds the file after each distill, ordered by `scan_timestamp`, written atomically. `make test` 54 passed, 3 xfailed. The G18 duplicate test is no longer xfail. Hand edits to PROJECT_MEMORY.md are overwritten by design (user accepted).
- **[G15]** SPEC §4.2 (distiller) is specified and tested, including the PROJECT_MEMORY.md format.
  - Why now: every fix to the project memory changes `claudalizer/distiller.py`. Without tests that pin the current behaviour and the target behaviour, the fixes can't be checked. This goal unblocks G18–G21.
  - Status: Done (orchestration 5: `e51e29d` SPEC §3.2/§4.2; `eb8e5da` `tests/test_distiller.py`, 8 passed and 4 strict xfail for G18–G21; `make test` 48 passed, 4 xfailed).
  - Original exit criteria: SPEC §4.2 states the PROJECT_MEMORY.md format and the five criteria above. Each one has a test in `tests/test_distiller.py`. Tests that describe target behaviour that is not yet built (duplicates on `--force`, generic fallback) are marked `xfail` with the goal id. `make test` passes.
  - First action: add a PROJECT_MEMORY subsection to `planning/SPEC.md` §4.2, then write the tests against `synthesize_offline_memory_block` and `_append_to_project_memory` using `tmp_path`.
  - Depends on: none.
  - Files in scope: `planning/SPEC.md`, `tests/test_distiller.py` (new), `tests/conftest.py` only if a fixture is needed.

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
  - Status: Moved to Sequenced Goals under G_live.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
