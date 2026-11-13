# Orchestration 4 State (`planning/STATE_4.md`)

Plan: `planning/EXECUTION_PLAN_4.md` (G14 Waybar refresh signal is safe)
Status: Draft. Awaiting user approval. Not started.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 3 executed (`a2eefa3`, `5ab4552`, `b651913`, `d5eb235`)
- [x] Recon: Waybar 0.9.24 present; Sway 1.9 present
- [ ] User approved `EXECUTION_PLAN_4.md`
- [ ] Commit the approved planning files before wave 1 (`docs(planning):`): `planning/GOALS.md` (G14 circled), `EXECUTION_PLAN_4.md`, `PROMPT_TEMPLATE_4.md`, `STATE_4.md`
- [x] Planning tracking: tracked (separate `docs(planning)` commits)
- [ ] Record baseline: `make test` (expected 29 passed on this branch)
- [ ] Record baseline: `make lint` (expected 12 findings, all pre-existing)
- [ ] Record baseline: `pgrep -a waybar` (real Waybar PID noted before the probe)

### Baseline records

- Pending. Fill in before wave 1.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T4.1.1 Headless probe of RTMIN+8 and SIGUSR2 | pending | | probe artifacts in `/tmp/g14-probe/` only |
| 2 | T4.2.1 Survives path: close R1 and G14 | pending | | runs only if `path=survives` |
| 2 | T4.2.2 Kill path: refresh with SIGUSR2 | pending | | runs only if `path=kills` |

Wave 2 starts only after wave 1 is all `done`. Exactly one wave-2 task runs; the other is marked `skipped (probe result)`.

Live check (user-run, not a gate): G4 refresh timing with the module added per README. Record the result here when the user reports it.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._
