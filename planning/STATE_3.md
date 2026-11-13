# Orchestration 3 State (`planning/STATE_3.md`)

Plan: `planning/EXECUTION_PLAN_3.md` (G4 Waybar state and refresh)
Status: Approved by user (2026-11-12). Not started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 2 closed (G5, G6, G7, G9 done; `planning/GOALS.md` re-ranked at `6756b5c`)
- [x] User approved `EXECUTION_PLAN_3.md` (2026-11-12)
- [x] Branch: work on `g5-g6-g7-g9` (no new branch; confirm with user at approval)
- [ ] Record baseline: `make test` (expected 22 passed on this branch)
- [ ] Record baseline: `make lint` (expected 12 findings, all pre-existing)
- [x] Planning tracking: tracked (separate `docs(planning)` commits)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T3.1.1 Status write sends Waybar refresh signal (ipc.py, tests/test_ipc.py) | pending | | |
| 1 | T3.1.2 README Waybar snippet with `"signal": 8` | pending | | |
| 2 | T3.2.1 Status returns to idle; plain scan writes status (cli.py, tests/test_cli.py) | pending | | depends on T3.1.1 |

Wave 2 starts only after wave 1 is all `done`.

End-of-wave-2 gate (orchestrator, serial): see "Verification at end of wave 2" in `EXECUTION_PLAN_3.md`.

Live check (user-run, not a gate): Waybar refresh timing with the module added per README. Record the result here when the user reports it.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
