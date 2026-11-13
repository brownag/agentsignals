# Orchestration 8 State (`planning/STATE_8.md`)

Plan: `planning/EXECUTION_PLAN_8.md` (G20 blind-alleys filter; G21 friction error lines)
Status: Draft. Awaiting user approval. Not started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 7 executed (`579b758`, `b202eb3`, `f513a87`)
- [x] Recon: friction and blind-alleys lines in `synthesize_offline_memory_block` (EXECUTION_PLAN_8 recon log)
- [x] Decisions from the grill: D1 (G20 excludes `g3-accept`, `rewrite-check`) and D3 (G21 error-marker line; drop entries with none)
- [ ] User approved `EXECUTION_PLAN_8.md`
- [ ] Commit the approved planning files before wave 1 (`docs(planning):`): `EXECUTION_PLAN_8.md`, `PROMPT_TEMPLATE_8.md`, `STATE_8.md`
- [x] Planning tracking: tracked
- [ ] Record baseline: `make test` (expected 56 passed, 2 xfailed)
- [ ] Record baseline: `make lint` (expected 11 findings, pre-existing)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T8.1.1 Blind-alleys excludes g3-accept and rewrite-check scratch (G20) | pending | | expect 58 passed, 1 xfailed after |
| 2 | T8.2.1 Friction lines show the first error line; drop entries with none (G21) | pending | | expect 60 passed, 0 xfailed after |
| 3 | T8.3.1 Update SPEC §3.2 and §4.2 for G20 and G21 | pending | | planning only |

Wave 2 starts only after wave 1 is all `done`. Wave 3 starts only after wave 2 is all `done`.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
