# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-24
Source State: STATE_10.md (G23 complete). Re-ranked 2026-11-24 with Magic Wand. G16, G_dead-notify and G17 are done, and so is the live check (G_live: G4, G6-followup, G3). Only the real-data LLM run is left open. G_opencode added to the backlog 2026-11-24.

Intent: durable indexing of Claude session history from volatile `/tmp/claude-1000` before deletion, on Sway/Wayland, with systemd and Waybar included. Current focus: the installed system works live; what remains is confirming LLM distillation on real data.

## Circled Goal (Active)

- **[G_llm-live]** `CLAUDALIZER_LLM_ENDPOINT=http://localhost:8090/v1/chat/completions claudalizer distill --force` writes memory blocks with a title and an Objective line from real data.
  - Why now: it is the only open goal left that the code is waiting on. The code is done under G_memlab, G_memlab-open and G10.
  - Exit criteria: after the run, the `memory.md` files under `~/.claude-mined-memories/` have LLM-written blocks, each with a title and an `Objective:` line.
  - First action: start the local LLM endpoint, then you run the command above.
  - Status: User-run.

## Sequenced Goals (Dependency DAG)

_(none.)_

## Independent Backlog

- **[G_opencode]** `claudalizer scan` and `watch` mine finished opencode sessions into dossiers and memory, alongside Claude Code sessions.
  - Why: opencode sessions hold the same kind of history (prompts, tool errors, touched files), but claudalizer only reads Claude Code. Research: `planning/research/OPENCODE_SESSIONS.md` (opencode v2.4.1, commit `6f05140`).
  - Source: the SQLite database `~/.local/share/opencode/opencode.db` (`OPENCODE_DB` overrides it), tables `session_v2`, `session_message`, `session_part`. Read-only via stdlib `sqlite3`. `/tmp/opencode` holds worktrees, not session data, and is not mined.
  - Exit criteria:
    - An opencode source module sits beside the Claude Code one in the miner; the distiller is unchanged.
    - A session is mined only when idle (`time_idle >= time_busy`) and changed since its dossier, judged by message and part `time_updated`, not only `session_v2.time_updated`.
    - Dossiers record user prompts, tool errors (`state.status="error"`), failed shell commands (non-zero `state.metadata.exit`; text `Exit code: N`), and touched files from `data.snapshot.files`. Assistant text is read from both inline message data and `session_part` rows.
    - The project slug comes from `session_v2.directory`, so opencode and Claude Code sessions in one repo share a `PROJECT_MEMORY.md`.
    - Every session is mined, subagents included: each subagent session's prompts, errors and touched files are folded into its parent's dossier (decided 2026-11-24: mine all of it).
    - An unknown schema migration skips the opencode source with a warning; the watch loop does not crash.
    - Tests use a fixture database built in `tmp_path`; `make check` passes.
  - Risks: the v2 schema changed about 90 times in 2026; the HTTP API and export are experimental, so they are not used.
  - First action: write SPEC sections for the opencode source, including how a subagent session is linked to its parent.
  - Depends on: none.

## Deferred

- **[G22]** Hand-written notes survive rebuilds and reach Claude through a standard injection format.
  - Trigger: you need to write notes by hand that must persist. Today a rebuild discards hand edits (G18, by design). The likely shape is a separate durable file that the distiller reads, not an edit to PROJECT_MEMORY.md.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.
- **[G_churn]** A session that writes in bursts is re-mined once it settles, not on every watch tick.
  - Observed 2026-11-24: the 2 s settle window is shorter than the 3 s watch interval, so an active session (a background task writing output) is re-mined about every 3 s, never shows as Active, and pushes up Waybar's total-mined count. Harmless; changing the settle window is ask-first.
  - Trigger: the total-mined count or the CPU and I/O from re-mining become a problem.

## Done

- **[G_live]** After `make systemd-install`, the installed units and Waybar module work on this machine.
  - Status: Done (2026-11-24). Units installed at 17:31 and Waybar restarted.
- **[G4]** Waybar shows current capture state and refreshes after each scan.
  - Status: Done (2026-11-24). The user confirmed the module updates after `claudalizer scan`. `/tmp/claudalizer_status.json` was rewritten as soon as the scan finished (17:32:32).
- **[G6-followup]** `claudalizer.service` no longer hits `start-limit-hit`.
  - Status: Done (2026-11-24). Inactive since the install, with no `start-limit-hit` in the journal.
- **[G3]** Every write under `/tmp/claude-1000` triggers a scan within 10 s.
  - Status: Done (2026-11-24). `claudalizer-watch.service` mined writes inside nested session folders about every 3 s (journal, `hyd-rs` session task output).

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
  - Status: Done (2026-11-24); see Done.
- **[G12]** Injection into `.claude/CLAUDE.md`.
  - Status: Pruned
  - Reason: outside durable indexing, and it adds a second write target.
