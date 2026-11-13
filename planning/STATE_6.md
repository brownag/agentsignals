# Orchestration 6 State (`planning/STATE_6.md`)

Plan: `planning/EXECUTION_PLAN_6.md` (G18: PROJECT_MEMORY.md is rebuilt from session files)
Status: Draft. Awaiting user approval. Not started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 5 executed (`e51e29d`, `eb8e5da`, `44a51d3`, `feedafb`, `109beba`)
- [x] Recon: `_append_to_project_memory` appends on every distill; G18 xfail fails with `assert 2 == 1` (EXECUTION_PLAN_6 recon log)
- [x] Decision D1 (revised): full rebuild from session files (user, 2026-11-12)
- [ ] User approved `EXECUTION_PLAN_6.md`
- [ ] Commit the approved planning files before wave 1 (`docs(planning):`): `planning/EXECUTION_PLAN_6.md`, `PROMPT_TEMPLATE_6.md`, `STATE_6.md`
- [x] Planning tracking: tracked
- [ ] Record baseline: `make test` (expected 48 passed, 4 xfailed)
- [ ] Record baseline: `make lint` (expected 12 findings, pre-existing)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T6.1.1 Replace session section in place; remove G18 xfail; add tests | pending | | expect 53 passed, 3 xfailed after |
| 2 | T6.2.1 Update SPEC §3.2 and §4.2 to the rebuild rule | pending | | planning only |

Wave 2 starts only after wave 1 is all `done`.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
