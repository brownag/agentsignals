# Orchestration 2 State (`planning/STATE_2.md`)

Plan: `planning/EXECUTION_PLAN_2.md` (G5, G6, G7, G9)
Status: Draft, awaiting user approval. No implementation started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [ ] Orchestration 1 closed (T1.3.1 done; G1 closed in GOALS.md)
- [ ] User approved EXECUTION_PLAN_2.md
- [ ] Create branch `g5-g6-g7-g9` from `g1-durable-capture`
- [ ] Record baseline: `make test` (count, expected to rise from 16 after orchestration 1 closes)
- [ ] Record baseline: `make lint` ruff findings (expected: 12 pre-existing, adjusted after orchestration 1)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T2.1.1 Sway detection requires a socket; SPEC §4.3 IPC tests | pending | | |
| 1 | T2.1.2 Path unit DirectoryNotEmpty | pending | | |
| 2 | T2.2.1 Failed git results kept; exit code 0 not a failure; README | pending | | |
| 3 | T2.3.1 SPEC §4.1 slug and corrupt-transcript tests | pending | | |

Wave 2 starts only after wave 1 is all `done`. Wave 3 starts only after wave 2 is all `done`.

End-of-wave-3 gate (orchestrator, serial): see "Verification at end of wave 3" in EXECUTION_PLAN_2.md.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
