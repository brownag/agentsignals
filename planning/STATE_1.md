# Orchestration 1 State (`planning/STATE_1.md`)

Plan: `planning/EXECUTION_PLAN_1.md` (G1 durable capture)
Status: Draft, awaiting approval. No implementation started.
Last Updated: 2026-11-12

## Pre-wave-1 checklist

- [ ] User approved EXECUTION_PLAN_1.md
- [ ] Create branch `g1-durable-capture` from `g3-watch` (git switch -c g1-durable-capture g3-watch)
- [ ] Record baseline: `make test` (expected 14 passed at g3-watch HEAD)
- [ ] Record baseline: `make lint` ruff findings (paste count and rule codes below)
- [ ] Confirm `distiller.py` dossier read path (T1.2.1 step 6)

### Baseline records

- `make test`: _pending_
- `make lint` findings: _pending_

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T1.1.1 Snapshot reports skipped files | pending | — | |
| 1 | T1.1.2 Spec and goal docs | pending | — | docs-only, `docs(planning)` commit |
| 2 | T1.2.1 Skipped files in dossier | pending | — | depends on T1.1.1 |

Wave 2 starts only after wave 1 is all `done`.

End-of-wave-2 gate (orchestrator, serial): `make check` exits 0; lint output reviewed; G1 exit criteria in GOALS.md checked.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
