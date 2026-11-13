# Orchestration 8 State (`planning/STATE_8.md`)

Plan: `planning/EXECUTION_PLAN_8.md` (G20 blind-alleys filter; G21 friction error lines)
Status: Done. Waves 1–3 complete.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 7 executed (`579b758`, `b202eb3`, `f513a87`)
- [x] Recon: friction and blind-alleys lines in `synthesize_offline_memory_block` (EXECUTION_PLAN_8 recon log)
- [x] Decisions from the grill: D1 (G20 excludes `g3-accept`, `rewrite-check`) and D3 (G21 error-marker line; drop entries with none)
- [x] User approved `EXECUTION_PLAN_8.md` (2026-11-12)
- [x] Approved planning files committed before wave 1: `e7b8ad8`
- [x] Planning tracking: tracked
- [x] Record baseline: `make test` 56 passed, 2 xfailed
- [x] Record baseline: `make lint` 11 findings, pre-existing

### Baseline records

- Tests: `make test` 56 passed, 2 xfailed.
- Lint: `make lint` 11 findings (pre-existing).

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T8.1.1 Blind-alleys excludes g3-accept and rewrite-check scratch (G20) | done | `5d0cef0` | 58 passed, 1 xfailed |
| 2 | T8.2.1 Friction lines show the first error line; drop entries with none (G21) | done | `1c4a6d6` | 60 passed, 0 xfailed |
| 3 | T8.3.1 Update SPEC §3.2 and §4.2 for G20 and G21 | done | none (planning only: `bcaac5d`) | |

Wave 2 starts only after wave 1 is all `done`. Wave 3 starts only after wave 2 is all `done`.

## Task reports

## T8.1.1
Status: done (`5d0cef0`). `TEST_RUN_SCRATCH_ROOTS` constant; blind-alleys filters on the first path segment. Tests: `test_test_runner_scratch...` unmarked; `test_scratch_outside_test_runs_is_kept` added. `pytest tests/test_distiller.py` 18 passed, 1 xfailed; `make test` 58 passed, 1 xfailed; lint 11.

## T8.2.1
Status: done (`1c4a6d6`). `ERROR_MARKERS` constant; friction line is `- **tool** (cmd): <error line>`; entries without a marker line are dropped; empty -> `- None detected.`. Tests: `test_friction_line_shows_real_error_text` unmarked; `test_friction_entry_without_error_marker_is_dropped` added.
Deviations: (a) `test_rebuild_changes_only_the_redistilled_session_text` (from orchestration 6) used `Exit code 2` as its error output, which G21 now drops. Its input was changed to `Error: NEWA failed`. Test-only fix. (b) `import pytest` in `tests/test_distiller.py` became unused once no xfail markers were left, and was removed. (c) Plan acceptance `grep -c xfail` = 0 was replaced by `grep -c 'pytest.mark.xfail'` = 0, since the docstring mentions the word.
Results: `pytest tests/test_distiller.py` 20 passed; `make test` 60 passed; lint 11 (pre-existing only).

## T8.3.1
Status: done (`bcaac5d`, planning only). SPEC §3.2 friction and blind-alleys items, the two target-rule lines in the PROJECT_MEMORY section, and §4.2 G20/G21 bullets now describe current behaviour. `target, G20/G21` = 0; `First line` = 0.
Deviation: the plan's acceptance did not cover the two target-rule lines in the PROJECT_MEMORY section, so the first count was 2. Fixed in the same commit.
