# Orchestration 6 State (`planning/STATE_6.md`)

Plan: `planning/EXECUTION_PLAN_6.md` (G18: PROJECT_MEMORY.md is rebuilt from session files)
Status: Done. Waves 1 and 2 complete (full rebuild, per user).
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 5 executed (`e51e29d`, `eb8e5da`, `44a51d3`, `feedafb`, `109beba`)
- [x] Recon: `_append_to_project_memory` appends on every distill; G18 xfail fails with `assert 2 == 1` (EXECUTION_PLAN_6 recon log)
- [x] Decision D1 (revised): full rebuild from session files (user, 2026-11-12)
- [x] User approved `EXECUTION_PLAN_6.md` (2026-11-12, with the full-rebuild revision and the D3/D2 consequences accepted)
- [x] Approved planning files committed before wave 1: `057d0c0`, `b630131`
- [x] Planning tracking: tracked
- [x] Record baseline: `make test` 48 passed, 4 xfailed
- [x] Record baseline: `make lint` 12 findings, pre-existing

### Baseline records

- Tests: `make test` 48 passed, 4 xfailed.
- Lint: `make lint` 12 findings (pre-existing).

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T6.1.1 Rebuild PROJECT_MEMORY.md from session files; remove G18 xfail; add tests | done | `c5162a6` | 54 passed, 3 xfailed |
| 2 | T6.2.1 Update SPEC §3.2 and §4.2 to the rebuild rule | done | none (planning only) | |

Wave 2 starts only after wave 1 is all `done`.

## Task reports

## T6.1.1

Status: done (`c5162a6`).
Files changed: `claudalizer/distiller.py` (`_append_to_project_memory` rebuilt from session `memory.md` files; `import tempfile`). `tests/test_distiller.py` (G18 xfail marker removed; 5 new rebuild tests).
Results: `pytest tests/test_distiller.py` = 14 passed, 3 xfailed. `make test` = 54 passed, 3 xfailed. `make lint` = 11 findings (was 12: `os` is now used; the remaining `dataclass` finding is pre-existing).
Deviations: (a) the plan's expected counts (13 and 53) were one short, because the plan named four new tests and the revised list has five. (b) The plan asked to replace a `test_hand_edited_file_without_session_heading_is_appended_to` test. That test was never written, so it was not replaced; the discard test was added instead. (c) A first version of `test_rebuild_changes_only_the_redistilled_session_text` wrote `NEW A` into `memory.md` and then redistilled with `force`; `force` regenerates `memory.md` from the dossier, so the test changed the dossier instead. Both are test-only fixes.

## T6.2.1

Status: done (planning only, separate commit).
SPEC §3.2 "Outputs per session" and "PROJECT_MEMORY.md format" now state the rebuild rule. §4.2 G18 target bullet is now five characterisation bullets. Acceptance: `(target, G18)` count 0; G19–G21 markers 3; `scan_timestamp` count 3.
