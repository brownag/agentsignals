# Orchestration 2 State (`planning/STATE_2.md`)

Plan: `planning/EXECUTION_PLAN_2.md` (G5, G6, G7, G9)
Status: Approved by user (run 'next plan', branch choice: from g1-durable-capture). Wave 1 done.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 1 closed (T1.3.1 done at ff66a16 on master; G1 closed in GOALS.md at c004d58)
- [x] User approved EXECUTION_PLAN_2.md (2026-11-12)
- [x] Create branch `g5-g6-g7-g9` from `g1-durable-capture` (at 5bf8361; planning files carried over in 3185174). Note: ff66a16 (T1.3.1 test) is NOT on this branch.
- [x] Record baseline: `make test` = 16 passed (branch base; 17 on master with ff66a16)
- [x] Record baseline: `make lint` = 12 findings, all pre-existing (11 F401, 1 F541)

### Baseline records

- `make test`: 16 passed. `make lint`: 12 findings (pre-existing).

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T2.1.1 Sway detection requires a socket; SPEC §4.3 IPC tests | done | f547fe8 | 5 passed in tests/test_ipc.py |
| 1 | T2.1.2 Path unit DirectoryNotEmpty | done | 21c8fad | make systemd-dry-run exit 0; line present |
| 2 | T2.2.1 Failed git results kept; exit code 0 not a failure; README | pending | | |
| 3 | T2.3.1 SPEC §4.1 slug and corrupt-transcript tests | pending | | |

Wave 2 starts only after wave 1 is all `done`. Wave 3 starts only after wave 2 is all `done`.

End-of-wave-3 gate (orchestrator, serial): see "Verification at end of wave 3" in EXECUTION_PLAN_2.md.

## Task reports

_Workers append here under `## <task id>` (15 lines max each)._

## 2.1.1

- Status: done (wave 1, inline by orchestrator; spec followed as written).
- Code commit: f547fe8 `fix(ipc): choose Sway only when a Sway socket exists`.
- Files: `claudalizer/ipc.py` (line 52: glob wrapped in `any(...)`); `tests/test_ipc.py` (new, 5 tests).
- Glob approach: `monkeypatch.setattr(ipc, "Path", lambda _p: tmp_path)` (the fallback builds `Path(f"/run/user/<uid>")`, so this redirects it).
- Tests: `pytest tests/test_ipc.py -q` 5 passed; `pytest tests/test_miner.py -q -k ipc` 1 passed.
- Lint: 12 (no new). Deviations: none.

## 2.1.2

- Status: done (wave 1, inline).
- Code commit: 21c8fad `fix(systemd): trigger the path unit only on a non-empty scan directory`.
- Files: `systemd/claudalizer.path` (`DirectoryNotEmpty=/tmp/claude-1000` in [Path]).
- Acceptance: `make systemd-dry-run` exit 0; grep count 1. No install run (H3).
- Deviations: none.

