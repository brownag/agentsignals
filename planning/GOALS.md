# Project Goals (`planning/GOALS.md`)

Last Updated: 2026-11-25
Source State: STATE_11.md (orchestration 11, opencode source, complete). Re-ranked 2026-11-25 with Magic Wand after 312 `memory.md` files were overwritten with offline-template output by an instant `distill --force` (20:41). The offline fallback is gone (`2625fdc`). The new focus is keeping a history of the mined memories so that no write can silently destroy one.

Intent: durable indexing of Claude Code and opencode session history from volatile sources before deletion, on Sway/Wayland, with systemd and Waybar included. Current focus: git history for `~/.claude-mined-memories` (G_memgit set).

## Circled Goal (Active)

The plan-wave set is G_dossier-stable, G_churn, G_mem-git and G_mem-baseline. G_dossier-stable and G_churn are roots and do not depend on each other, so they can run in parallel in the first wave. User decisions (2026-11-25): history is on by default, with one commit per scan pass or distill run that changed files, and forced re-distills are committed too.

- **[G_dossier-stable]** Re-mining a session whose content has not changed leaves `dossier.json` byte-identical. A changed scan time is not a content change.
  - Why now: every re-mine rewrites `dossier.json` because `scan_timestamp` changes, so git would see a change on every tick.
  - Exit criteria: mining an unchanged session twice gives the same bytes and the same mtime. `distiller.py` still orders `PROJECT_MEMORY.md` sections by scan time (keep the first-mined time, or record the time only on a content change). `make check` passes.
  - First action: in `_mine_ref`, compare the new dossier without `scan_timestamp` against the existing one and skip the write when they are equal.
- **[G_churn]** A session that writes in bursts is re-mined once it settles, not on every 3 s watch tick.
  - Why now: on 2026-11-25 the watcher re-mined 177 dossiers in one hour, mostly the same live sessions. Without this, G_mem-git records a commit every few seconds for each live session.
  - Exit criteria: a test session written every 1 s for 10 s is mined at most once after it goes quiet. The settle window and watch interval are not changed without asking (AGENTS.md *Ask First*).
  - First action: confirm from the journal and the settle code why a 2 s settle window with a 3 s interval re-mines active sessions, and propose a rule (for example, the scratchpad and transcript must both be quiet).
  - Was Deferred (observed 2026-11-24); promoted because G_mem-git depends on it.
- **[G_mem-git]** `~/.claude-mined-memories` is a git repository. Every scan pass or distill run that changes files makes exactly one commit, whose message names each session touched and why (mined, re-mined, distilled, `--force`). A pass that changes nothing makes no commit.
  - Why now: every later step that rewrites memory files (G_llm-live's 9.5 h `--force` run, G_memory-fresh) becomes reversible.
  - Exit criteria: on by default for `scan`, `distill` and `watch`; `--no-git` turns it off. Commits happen under `/tmp/claudalizer.lock` (`distill` takes no lock today, so it must start to). A missing `git` binary logs one warning and mining continues. A `--force` overwrite is undone with `git checkout <rev> -- <path>`. Tests use a repo in `tmp_path` only. Runtime stays stdlib-only (`subprocess` to `git`). `make check` passes.
  - Components: new `claudalizer/memory_git.py`; `miner.py`, `distiller.py` and `cli.py` call it once per pass.
  - Depends on: G_dossier-stable, G_churn.
- **[G_mem-baseline]** The existing tree (566 MB, 42,984 files, 3 over 1 MB on 2026-11-25) is committed once as the baseline, including the 312 template files, so every later change has a parent.
  - Exit criteria: a baseline commit exists. Repo size and `git add` time were measured on a copy first, and any `.gitignore` entries (for example large scratchpad copies) are recorded with the reason. Initialising the real root is ask-first.
  - First action: measure `git init` and `git add -A` on a copy of the tree in the scratchpad.
  - Depends on: G_mem-git.

## Sequenced Goals (Dependency DAG)

- **[G_distill-report]** `distill` reports sessions it wrote, skipped (memory already exists) and failed (LLM error) separately, and never lists a skipped file as "Generated".
  - Today `distill_session` returns the existing path when `memory.md` exists and `force` is off, and `handle_distill` prints it as generated.
  - Depends on: none.
- **[G_distill-offloop]** LLM distillation runs outside the watch loop, from a queue drained in the background, so mining is not blocked for about 108 s per session.
  - Depends on: none.
- **[G_memory-fresh]** A session's `memory.md` is re-distilled when its dossier content changes, instead of staying at its first version. Each version is kept in git.
  - Depends on: G_mem-git, G_distill-offloop, G_dossier-stable.
- **[G_llm-live]** All `memory.md` files under `~/.claude-mined-memories/` are LLM-written, with a title and an `Objective:` line, replacing the template output.
  - Measured 2026-11-25: about 108 s per session with `qwen3.8-flash` on `localhost:8090`, so about 9.5 h for 316 sessions. The watch unit's drop-in (`claudalizer-watch.service.d/llm.conf`) already sets the endpoint.
  - First action: after G_mem-baseline, run `CLAUDALIZER_LLM_ENDPOINT=http://localhost:8090/v1/chat/completions claudalizer distill --force` in the background (user-approved run).
  - Depends on: G_mem-baseline, G_distill-report.
- **[G_restore-cli]** `claudalizer history <slug>/<session>` lists a memory's versions, and `--restore <rev>` brings one back without raw git commands.
  - Depends on: G_mem-git.

## Independent Backlog

- **[G_mirror-filter]** Scratchpad snapshots do not copy nested memory roots or claudalizer test output into the memories root. On 2026-11-25 a scratchpad test copy (`memtest/`) and an earlier `verify/` run were mirrored as if they were memories.

## Deferred

- **[G22]** Hand-written notes survive rebuilds and reach Claude through a standard injection format.
  - Trigger: you need to write notes by hand that must persist. Today a rebuild discards hand edits (G18, by design). The likely shape is a separate durable file that the distiller reads, not an edit to PROJECT_MEMORY.md.
- **[G13]** Extract history from `/tmp/claude-1000/bash-edit-diff/` (bare git repositories whose objects hold earlier versions of edited files). Needs a new extractor; a slug-filter change alone captures nothing.
  - Trigger: you want that history mined.
- **[G_sanitize]** Distillation of opencode sessions uses `opencode session export --sanitize` output instead of raw rows.
  - Trigger: concern about what opencode content reaches the LLM. How its redaction works has not been read (research, Open questions).
- **[G_oc-worktree]** Sessions in opencode-managed worktrees (`~/.local/share/opencode/worktree/...`) are filed under their project's main checkout slug.
  - Trigger: worktree slugs fragment project memory. Today they get their own slug, as Claude Code worktrees do (SPEC §3.1).

## Done

- **[G_no-offline]** Distillation has no offline fallback. Without an endpoint, or when the LLM returns nothing, no memory file is written and existing ones are kept.
  - Status: Done (2026-11-25). `2625fdc`, SPEC `2f0f1e1`. `distill` exits 2 without an endpoint; `watch` and `scan` warn and only mine. `make check` 141 passed. The watch service was restarted on the new code at 20:57.
- **[G_oc-seam] [G_oc-fixture] [G_oc-read] [G_oc-guard] [G_oc-cli]** opencode session source.
  - Status: Done (2026-11-25, orchestration 11, `planning/STATE_11.md`). `make check` 144 passed at the end of the orchestration.
- **[G_oc-live]** opencode dossiers are mined from the live database and share `PROJECT_MEMORY.md` folders with Claude Code sessions.
  - Status: Done (2026-11-25). 128 opencode dossiers exist; for example `-home-andrew-AI-hyd-rs` has 9 opencode and 23 Claude Code sessions. The database mtime check was not recorded.

- **[G_oc-spec]** SPEC states the opencode source: the protocol, the settle and change marker, the field mapping, the subagent fold, the schema guard, and the tests.
  - Status: Done (2026-11-25). SPEC §3.1 *Session sources* and *opencode source*, §3.4 global flags, §4.1a test list. The rules were checked read-only against the live database: one level of subagent nesting and no orphans; the marker query took about 20 ms warm; edits go through the `patch` tool (`patchText`); `snapshot.files` holds relative paths.
- **[G_opencode]** (parent) Split into G_oc-spec, G_oc-seam, G_oc-fixture, G_oc-read, G_oc-guard, G_oc-cli and G_oc-live on 2026-11-25. Its original exit criteria are now in SPEC §3.1 and §4.1a.

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
