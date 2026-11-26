# Orchestration 12 State (`planning/STATE_12.md`)

Plan: `planning/EXECUTION_PLAN_12.md` (git history for mined memories)
Status: Executed. All six tasks done on `feat/memory-git`. `make check`: ruff clean, 176 passed.
Last Updated: 2026-11-25

## Pre-wave checklist
- [x] Git repository; current branch `feat/opencode-source` at `c7aca83`, clean.
- [x] Branch `feat/memory-git` created from `feat/opencode-source` (D1).
- [x] Planning artifacts tracked (D8).
- [x] User decisions recorded in `EXECUTION_PLAN_12.md` D1–D10.
- [x] Baseline: `make check`: ruff clean, 141 passed (Python 3.12.3).
- [x] User approves execution plan (2026-11-25).

## Wave board
| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T12.1.1 memory_git module and conftest guard | done | 6e35889 | inline (no worktree) |
| 1 | T12.1.2 Stable dossiers and re-mine interval | done | a767a56, e9a969c | e9a969c adjusts one opencode test (see report) |
| 1 | T12.1.3 Distiller lock and written log | done | 8bb34a0 | |
| 2 | T12.2.1 Miner commits each pass | done | d429122 | |
| 3 | T12.3.1 CLI flags and wiring | done | 2a1bde0, ba89952 | 2a1bde0 fixes the repo not being created on distill |
| 3 | T12.3.2 Docs (README, AGENTS, SPEC) | done | 76a5698 | |

## Task reports

### T12.1.1
- Status: done. `claudalizer/memory_git.py` (MemoryRepo), `tests/test_memory_git.py` (11 tests), conftest guard.
- Code commit: 6e35889. Deviation: none.

### T12.1.2
- Status: done. `miner.py`: `_tree_digest`, stable write (D9), `recent` skip, `pass_log`, `WATCH_MIN_REMINE_SECONDS`. `tests/test_remine.py` (7 tests).
- Deviation: `tests/test_opencode_source.py::test_part_update_triggers_remine` expected a timestamp-only part change to produce a dossier. D9 forbids that. Commit e9a969c changes it to expect no rewrite on a timestamp-only change, and a rewrite on a real prompt edit. The plan did not list that file, so the gap is in the plan.

### T12.1.3
- Status: done. `distiller.py`: `repo`, `lock_file`, `pass_log`, `commit_pass`, external commit once per pass. 6 new tests in `tests/test_distiller.py`.

### T12.2.1
- Status: done. `scan_and_mine` ensures the repo, commits externals and the scan pass under the existing lock. `last_commit` is set. 7 tests in `tests/test_miner_git.py`.

### T12.3.1
- Status: done. `--no-git`, `build_repo`, watch `min_remine_seconds`, distiller wiring, `recent` summary. 3 CLI tests and 1 summary test.
- Deviation: the distiller did not call `ensure()`, so a repo first created by `distill` was never committed. Fixed in 2a1bde0 with a test-double update.

### T12.3.2
- Status: done. README "Memory history", AGENTS.md entries, SPEC "Memory history (G_mem-git)" with D2–D6, D9, D10.

### Execution notes
- Ran inline on `feat/memory-git`, not in worktrees with workers. Tasks were serial and small, so worktrees added cost without parallel gain.
- Not done (ask-first, G_mem-live): restart `claudalizer-watch`, create the real repo, verify no-change ticks add no commits.
