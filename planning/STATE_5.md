# Orchestration 5 State (`planning/STATE_5.md`)

Plan: `planning/EXECUTION_PLAN_5.md` (G15: distiller spec and tests cover PROJECT_MEMORY.md)
Status: Draft. Awaiting user approval. Not started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 4 executed (`b3e4365`, `edb3cba`, `ba4f645`)
- [x] Recon: SPEC §3.2 / §4.2 describe a design the code no longer has (EXECUTION_PLAN_5 recon log)
- [x] Decisions D1–D4 recorded from the grill (EXECUTION_PLAN_5 decision log)
- [ ] User approved `EXECUTION_PLAN_5.md`
- [ ] Commit the approved planning files before wave 1 (`docs(planning):`): `planning/GOALS.md`, `EXECUTION_PLAN_5.md`, `PROMPT_TEMPLATE_5.md`, `STATE_5.md`
- [x] Planning tracking: tracked (separate `docs(planning)` commits)
- [ ] Record baseline: `make test` (expected 40 passed on this branch)
- [ ] Record baseline: `make lint` (expected 12 findings, all pre-existing)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T5.1.1 Rewrite SPEC §3.2 and §4.2 to the current distiller | pending | | planning only |
| 2 | T5.2.1 Create `tests/test_distiller.py` (characterisation + strict xfail) | pending | | depends on T5.1.1 |

Wave 2 starts only after wave 1 is all `done`.

Downstream (not in this orchestration): G18, G19, G20, G21 each remove one xfail marker when they land.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
