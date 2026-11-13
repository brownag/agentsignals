# Orchestration 5 State (`planning/STATE_5.md`)

Plan: `planning/EXECUTION_PLAN_5.md` (G15: distiller spec and tests cover PROJECT_MEMORY.md)
Status: Done. Waves 1 and 2 complete.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 4 executed (`b3e4365`, `edb3cba`, `ba4f645`)
- [x] Recon: SPEC §3.2 / §4.2 describe a design the code no longer has (EXECUTION_PLAN_5 recon log)
- [x] Decisions D1–D4 recorded from the grill (EXECUTION_PLAN_5 decision log)
- [x] User approved `EXECUTION_PLAN_5.md` (2026-11-12)
- [x] Approved planning files committed before wave 1: `37c8e1f`
- [x] Planning tracking: tracked (separate `docs(planning)` commits)
- [x] Record baseline: `make test` 40 passed (before wave 1)
- [x] Record baseline: `make lint` 12 findings, all pre-existing

### Baseline records

- Tests: `make test` 40 passed.
- Lint: `make lint` 12 findings (pre-existing).
- Waybar PID 350930 (restarted by the user before the plan ran); Sway PID 106996.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T5.1.1 Rewrite SPEC §3.2 and §4.2 to the current distiller | done | none (planning only: `e51e29d`) | |
| 2 | T5.2.1 Create `tests/test_distiller.py` (characterisation + strict xfail) | done | `eb8e5da` | 8 passed, 4 xfailed |

Wave 2 starts only after wave 1 is all `done`.

Downstream (not in this orchestration): G18, G19, G20, G21 each remove one xfail marker when they land.

## Task reports

## T5.1.1

Status: done (`e51e29d`, planning only).
Files changed: `planning/SPEC.md`. §3.2 rewritten (outputs, synthesis, offline block, PROJECT_MEMORY.md format, control flow). §4.2 rewritten (8 characterisation tests, 4 target xfail tests). §1 diagram line and §2 layout line that named CLAUDE.md injection now name PROJECT_MEMORY.md. Old test skeleton (former `### **tests/test_distiller.py**` block) replaced by a pointer to §4.2.
Deviations: none from the approved spec.
Acceptance: 0 old function names; `PROJECT_MEMORY` count 7; target markers 5; `make test` 40 passed.
Remaining `CLAUDE.md` mentions: the directive heading the code still emits, and the note replacing the skeleton. Both intended.

## T5.2.1

Status: done (`eb8e5da`).
Files changed: `tests/test_distiller.py` (new, 12 tests).
Test results: `python -m pytest tests/test_distiller.py -q` = 8 passed, 4 xfailed. `make test` = 48 passed, 4 xfailed. `make lint` = 12 findings, none new.
Verification of xfails: `pytest --runxfail` shows each of the four fails on its target assertion (G18 count 2 != 1; G19 fallback line present; G20 scratch lines listed; G21 real error line absent).
Deviation (clarification of the spec): the G21 test input in EXECUTION_PLAN_5 used a first line of `FAILED ...`, which current code already prints, so the test would have XPASSed. The test uses `Exit code 2` as the first output line and the `FAILED ...` text on the second. This keeps the test failing on current code, which is what strict xfail needs.
Real `~/.claude-mined-memories` untouched (mtime unchanged).
