# Orchestration 1 State (`planning/STATE_1.md`)

Plan: `planning/EXECUTION_PLAN_1.md` (G1 durable capture)
Status: Draft, awaiting approval. No implementation started.
Last Updated: 2026-11-12

## Pre-wave-1 checklist

- [x] User approved EXECUTION_PLAN_1.md
- [x] Create branch `g1-durable-capture` from `g3-watch` (commit 41da110)
- [x] Record baseline: `make test` (14 passed)
- [x] Record baseline: `make lint` ruff findings (14 total)
- [ ] Confirm `distiller.py` dossier read path (T1.2.1 step 6)

### Baseline records

- `make test` (branch g1-durable-capture, 2026-11-12): 14 passed.
- `make lint` (ruff): 14 findings, all pre-existing. 13 × F401 unused-import, 1 × F541 f-string-missing-placeholders. Note: `make lint` prints "ruff not found" after the findings, but ruff is installed at `~/.local/bin/ruff` and runs fine.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T1.1.1 Snapshot reports skipped files | done | 72d3ff6 | 15 targeted tests pass; lint 14 -> 12 (two unused test imports now used) |
| 1 | T1.1.2 Spec and goal docs | done | 9d93cdf | acceptance greps pass (no 256 in SPEC, no L783 in GOALS, skipped_files present) |
| 2 | T1.2.1 Skipped files in dossier | done | efa23c8 | `make check` passes (16 tests); lint still 12 pre-existing |

Wave 2 starts only after wave 1 is all `done`.

End-of-wave-2 gate (orchestrator, serial): `make check` exits 0; lint output reviewed; G1 exit criteria in GOALS.md checked.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._

## 1.1.1

- Status: done (wave 1). Plan approved after review; micro-TODO at `planning/tasks/1.1.1.todo.md`.
- Code commit: 72d3ff6 `feat(miner): report skipped scratchpad files`.
- Files: `claudalizer/miner.py` (snapshot_scratchpad returns `(copied, skipped)`; excluded-dir check moved before stat; caller unpacks); `tests/test_miner.py` (tuple unpack; new `test_snapshot_reports_skipped_files`).
- Tests: `pytest tests/test_miner.py -q -k "snapshot or mine"` → 15 passed.
- Lint (ruff, claudalizer + tests): 14 → 12. Drop is from two test imports (`shutil`, `Path`) now used by the new test. No new findings.
- Deviations: none.
- Gotcha for T1.2.1: `snapshot_scratchpad` now returns a tuple; `_mine_session` discards the skipped list (`copied_files, _ = ...`) until T1.2.1 wires it through.

## 1.1.2

- Status: done (wave 1). Plan approved with two answers (fix stale 256 KB in SPEC; update GOALS line 14).
- Doc commit: 9d93cdf `docs(planning): record stub policy for skipped scratchpad files`.
- Files: `planning/SPEC.md` (§3.1 skipped_files and skipped_count; §4.1 bullet; 256 KB → 250 KiB at line 73 and the test block); `planning/GOALS.md` (L783-786 → §4.1/§3.1 at G1 and G9).
- Acceptance: `grep 256 planning/SPEC.md` empty; `grep L783 planning/GOALS.md` empty; `grep skipped_files planning/SPEC.md` 3 matches.
- Deviations: none.

## 1.2.1

- Status: done (wave 2). Plan approved; micro-TODO at `planning/tasks/1.2.1.todo.md`. distiller.py check: no strict `dossier_data[...]` lookups, so distiller.py was not edited.
- Code commit: efa23c8 `feat(miner): keep skipped scratchpad files in dossier`.
- Files: `claudalizer/miner.py` (`SessionDossier.skipped_files`; `_mine_session` keeps skipped-only sessions; `stats.skipped_count`); `tests/test_miner.py` (new `test_session_with_only_skipped_file_gets_dossier`).
- Tests: `pytest tests/test_miner.py -q` → 16 passed. Wave-end `make check` → exit 0, 16 passed.
- Lint: 12 findings, all pre-existing (no new).
- Deviations: none.
- Note for G1 closeout: SPEC §4.1 names `test_filter_oversized_scratchpad`, but no test has that name. The behavior is covered by `test_snapshot_reports_skipped_files` (T1.1.1) and `test_session_with_only_skipped_file_gets_dossier` (T1.2.1).
