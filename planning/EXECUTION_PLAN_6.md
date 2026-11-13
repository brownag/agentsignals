# Execution Plan 6: G18 PROJECT_MEMORY.md is rebuilt from session files (`planning/EXECUTION_PLAN_6.md`)

Orchestration: 6
Source goal: `planning/GOALS.md` [G18] (circled; focus: PROJECT_MEMORY.md quality)
Status: Draft for user approval (revised 2026-11-12: full rebuild, per user). Not started.
Starts after: orchestration 5 executed (`e51e29d`, `eb8e5da`, `44a51d3`, `feedafb`, `109beba`).
Base branch: `g5-g6-g7-g9` (HEAD after the draft commit). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (decision D3 carried from orchestrations 1–5). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** PROJECT_MEMORY.md is rebuilt from the session files, so it never holds duplicate sections, whether a session is distilled once or re-distilled with `--force`.

**Exit criteria (from GOALS.md G18).** Distilling the same session twice with `--force` leaves one `## Session <id8> Distillation` section for it. The strict xfail `test_force_redistill_does_not_duplicate_project_section` passes, and its marker is removed. `make test` passes.

**In scope**
- `claudalizer/distiller.py`: after each session's `memory.md` is written, PROJECT_MEMORY.md is regenerated from every session's `memory.md` under that project (decision D1). The write is atomic.
- `tests/test_distiller.py`: remove the `xfail` marker from the G18 test; add tests for the rebuild.
- `planning/SPEC.md` §3.2: state the rebuild rule as current behaviour, and remove the `(target, G18)` markers.

**Out of scope**
- G19 (directives), G20 (scratch filter), G21 (friction lines). Their xfail tests stay as they are.
- Removing or rewriting `memory.md` files, or changing `distill_session`'s skip-without-force behaviour.
- Preserving hand edits made to PROJECT_MEMORY.md. A rebuild overwrites them (decision D3; flagged below).
- G16, G11, G4 live check, G17. Not touched.
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G18 exit: "distilling the same session twice with `--force` leaves one section for it. The G15 duplicate test turns from `xfail` to pass. `make test` passes."
- User decision (2026-11-12): first "2" (replace the session's section in place), then changed to "actually we should completely rebuild". The full rebuild is the decision of record.
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." Stdlib only. Never touch `~/.claude-mined-memories` or `/tmp/claude-1000` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | After each session's `memory.md` is written, PROJECT_MEMORY.md is regenerated from the `memory.md` of every session directory under that project slug. Sections use today's heading and separator format | User chose a full rebuild. Makes the file a pure function of the session files | User (revised) |
| D2 | 2026-11-12 | Section order is by `scan_timestamp` from each session's `dossier.json`, then by session id as a tie-break. Sessions with no `dossier.json` or no `memory.md` are left out | `scan_timestamp` is written once at mining time, so the order is stable across re-runs. The current append order is also chronological by distill time, so this is close to today | Judgment, flagged for review |
| D3 | 2026-11-12 | A rebuild overwrites hand edits in PROJECT_MEMORY.md. Hand notes that are not in a session's `memory.md` are lost | This is the direct cost of a full rebuild. Flagged: the user must accept it | Judgment, flagged for review |
| D4 | 2026-11-12 | The file is written to a temp file in the same directory and then renamed with `os.replace`, so an interrupted run never leaves a half-written file (same approach as G2) | Keeps a crash from leaving a truncated PROJECT_MEMORY.md | Judgment, flagged for review |
| D5 | 2026-11-12 | Rebuild runs after each `memory.md` write in `distill_session`, not once at the end of `distill_all`. Cost is a read of each session's `memory.md` per write, which is small (tens of sessions per project) | Simplest correct behaviour. Keeps `distill_session` self-contained | Judgment, flagged for review |
| D6 | 2026-11-12 | Planning files tracked (D3 from orchestration 5). Workers run inline, one task at a time (D4 from orchestration 5). Acceptance bar: `make test` green, lint at the 12 pre-existing findings with none added | Same as orchestration 5 | Default |
| D7 | 2026-11-12 | The code change and its tests are one commit. The SPEC update is a separate `docs(planning)` commit | Logical unit: behaviour plus tests. SPEC is planning-only | Default |

## Recon Log (facts)

- `claudalizer/distiller.py`:
  - `MemoryDistiller.distill_session` (line 197): writes `memory.md` if missing or forced, then calls `self._append_to_project_memory(slug, content, session_id)`.
  - `_append_to_project_memory` (line 237): appends `"\n\n---\n## Session {session_id[:8]} Distillation\n" + block + "\n"` to `<root>/<slug>/PROJECT_MEMORY.md`. Append-only; this is the cause of the duplicate.
  - `distill_all` (line 247) calls `distill_session` once per session directory.
- Session directory layout: `<root>/<slug>/<session_id>/` holds `dossier.json` (keys include `scan_timestamp`, `session_id`, `slug`, `decoded_path`, `tool_errors`, `scratchpad_files`, `user_prompts`, `stats`) and, once distilled, `memory.md`.
- `tests/test_distiller.py`: the G18 test is `test_force_redistill_does_not_duplicate_project_section`, marked `@pytest.mark.xfail(strict=True, reason="G18: PROJECT_MEMORY rebuilt from session files, not appended")`. Today it fails with `assert 2 == 1`.
- Baseline: `make test` = 48 passed, 4 xfailed. `make lint` = 12 findings, pre-existing.
- Real files (2026-11-12): 8 `PROJECT_MEMORY.md` files, no duplicate headers. The `-home-andrew-AI-claudalizer` file has no hand-written content: every section is a distilled block.
- `planning/SPEC.md` §3.2 has three `(target, G18)` markers. §4.2 lists the G18 test as a target.

## Hazard Notes

- H1: Tests use `tmp_path` only. Never the real `~/.claude-mined-memories`.
- H2: Tests make no network calls. Mock `call_llm_completion` where an endpoint is passed.
- H3: The rebuild must read only `memory.md` files and `dossier.json`. It must not read or write anything outside the slug directory.
- H4: `distill_session`'s return value and skip-without-force behaviour do not change (`test_distiller_offline` and the characterisation tests depend on them).
- H5: Do not run `make install-user`, `make systemd-install`, or `claudalizer watch`.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T6.1.1 Rebuild PROJECT_MEMORY.md from session files; remove G18 xfail; add tests | claudalizer | `claudalizer/distiller.py`, `tests/test_distiller.py` | — | No |
| 2 | T6.2.1 Update SPEC §3.2 and §4.2 to the rebuild rule | claudalizer | `planning/SPEC.md` | T6.1.1 | No |

Serial (D6).

## Task Specs

### T6.1.1 — Rebuild PROJECT_MEMORY.md from session files; remove the G18 xfail

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/distiller.py` (`_append_to_project_memory` and at most one private helper placed next to it), `tests/test_distiller.py`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In `claudalizer/distiller.py`, change `_append_to_project_memory(self, slug, memory_block, session_id)` so that it rebuilds the file. Keep its name and signature, so the call in `distill_session` does not change. Its body does this:
     a. Collect sessions: for each directory `<root>/<slug>/<session_id>/` that contains both `dossier.json` and `memory.md`, read `memory.md` as text and `scan_timestamp` from `dossier.json` (use `""` if missing or unreadable).
     b. Sort by `(scan_timestamp, session_id)` (D2).
     c. For each session, build the section exactly as today: `"\n\n---\n## Session " + session_id[:8] + " Distillation\n" + memory_text + "\n"`. Concatenate the sections in sorted order.
     d. Write the full text to a temp file in `<root>/<slug>/` (`tempfile.NamedTemporaryFile(dir=..., delete=False, mode="w", encoding="utf-8")` or equivalent), then `os.replace` it onto `PROJECT_MEMORY.md` (D4). Create the slug directory first, as today.
     e. If there are no sessions at all, write an empty file.
  2. The `memory_block` argument is no longer used to build the file (the session's `memory.md` is already written by the caller before the rebuild). Keep it in the signature, and note in the docstring that it is unused, so the call site stays the same.
  3. Do not change `distill_session`, `distill_all`, `synthesize_offline_memory_block`, `build_synthesis_prompt`, or `call_llm_completion`.
  4. In `tests/test_distiller.py`:
     a. Remove the `@pytest.mark.xfail(...)` line above `test_force_redistill_does_not_duplicate_project_section`. The body stays as it is.
     b. Replace the test `test_hand_edited_file_without_session_heading_is_appended_to` (it is no longer true: D3) with `test_rebuild_discards_hand_edits_outside_session_files`: write `PROJECT_MEMORY.md` with the text `hand notes`, distill a session, assert `hand notes` is gone and the session section is present.
     c. Add these tests, all with `tmp_path`:
        - `test_rebuild_changes_only_the_redistilled_session_text` — sessions A and B distilled; change A's `memory.md` to contain `NEW A`, re-distill A with `force=True`; assert `NEW A` appears once, B's section text is unchanged, and A still comes before B.
        - `test_rebuild_orders_sessions_by_scan_timestamp` — two sessions whose `dossier.json` `scan_timestamp` values are `2026-01-02` (session `zzz`) and `2026-01-01` (session `aaa`); distill both; assert `aaa` section precedes `zzz`.
        - `test_rebuild_skips_session_without_memory_md` — a session directory with `dossier.json` but no `memory.md` does not appear in the file.
        - `test_rebuild_is_idempotent` — rebuild twice with no change in between; file bytes are identical.
  5. Do not change any other xfail marker (G19, G20, G21).
- **Anchors:** `claudalizer/distiller.py`: `def _append_to_project_memory` (search by name), `def distill_session` (search by name). `tests/test_distiller.py`: `def test_force_redistill_does_not_duplicate_project_section`, `def test_hand_edited_file_without_session_heading_is_appended_to`.
- **Reference implementation:** the current `_append_to_project_memory` (same file). Replace its body; keep the header and separator format.
- **Constraints (do not touch)**
  - No change to any function other than `_append_to_project_memory` and its one optional helper.
  - No file under `~/.claude-mined-memories`; the rebuild reads only the slug directory (H3).
  - No change to xfail markers for G19–G21.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q -rx` exits 0. Expected: 13 passed, 3 xfailed (the G19, G20, G21 tests).
  - `python -m pytest tests/test_distiller.py -q -k force_redistill` passes with no xfail marker.
  - `grep -c 'xfail' tests/test_distiller.py` prints 3.
  - `make test` exits 0. Expected: 53 passed, 3 xfailed.
  - `make lint` reports 12 findings, none new.
- **Commit:** `fix(distiller): rebuild PROJECT_MEMORY.md from session files` (code and tests together)

### T6.2.1 — Update SPEC §3.2 and §4.2 to the rebuild rule

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md` (§3.2 "Outputs per session" and "PROJECT_MEMORY.md format"; §4.2 G18 bullet only)
  - Can create: none
- **Depends on:** T6.1.1
- **Spec**
  1. "Outputs per session": replace the PROJECT_MEMORY.md target sentence with the current rule: the file is regenerated from every session's `memory.md` after each distill, in `scan_timestamp` order, written atomically. Remove `**(target, G18)**`.
  2. "PROJECT_MEMORY.md format": remove the `(target, G18)` marker. State that hand edits are overwritten on rebuild (D3), and that sessions without `memory.md` are omitted.
  3. §4.2: change the G18 target bullet to a characterisation bullet, and name the four tests added in T6.1.1 (`test_rebuild_changes_only_the_redistilled_session_text`, `test_rebuild_orders_sessions_by_scan_timestamp`, `test_rebuild_skips_session_without_memory_md`, `test_rebuild_is_idempotent`) plus `test_rebuild_discards_hand_edits_outside_session_files`. Remove the G18 entry from the target list.
  4. Do not change the G19, G20, or G21 target markers.
  5. Do not edit any other file.
- **Anchors:** `planning/SPEC.md`: `#### **Outputs per session**`, `#### **PROJECT\_MEMORY.md format**`, the §4.2 bullet beginning `test\_force\_redistill`.
- **Constraints (do not touch)**
  - Do not change §3.2 Synthesis, Offline block format, or Control flow, except where a sentence names G18.
- **Acceptance (mechanical)**
  - `grep -c 'target, G18' planning/SPEC.md` prints `0`.
  - `grep -c 'target, G19\|target, G20\|target, G21' planning/SPEC.md` prints at least `3`.
  - `grep -c 'scan_timestamp' planning/SPEC.md` prints at least `1`.
  - `make test` exits 0 with the count from T6.1.1 (53 passed, 3 xfailed).
- **Commit:** `docs(planning): describe PROJECT_MEMORY rebuild rule in SPEC` (planning-only)

## Verification at end of wave 2 (orchestrator, serial)

1. `make test`: 53 passed, 3 xfailed.
2. `make lint`: 12 findings, none new.
3. `git log --oneline` shows one `fix(distiller)` commit and one `docs(planning)` commit for the SPEC, after the planning commits.
4. Check on a scratch copy only: run a distill twice with `--force` in a `tmp_path` root and read the file. (The test covers this; the manual run shows real output.)
5. Report to the user: the change, the test counts, the D3 consequence (hand edits are overwritten), and that G19 is next.

## Escalation (from wave-orchestration)

1. A new test fails for a reason other than the code under test (fixture or spec error): stop and report. Fix the test only if the spec was wrong.
2. The G18 xfail passes before the change (XPASS): stop and report.
3. The rebuild changes a session's text beyond the redistilled one (test 4c first bullet fails): stop and report. Do not widen the change.
4. Acceptance fails after one retry: stop and report to the user. No third attempt (inline, D6).
5. An out-of-scope edit is needed (for example `claudalizer/miner.py` or a G19–G21 marker): stop and re-scope the spec in this file.
