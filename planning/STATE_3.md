# Orchestration 3 State (`planning/STATE_3.md`)

Plan: `planning/EXECUTION_PLAN_3.md` (G4 Waybar state and refresh)
Status: Wave 1 and wave 2 complete. Code committed. Live Waybar check pending (user-run).
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 2 closed (G5, G6, G7, G9 done; `planning/GOALS.md` re-ranked at `6756b5c`)
- [x] User approved `EXECUTION_PLAN_3.md` (2026-11-12)
- [x] Branch: work on `g5-g6-g7-g9` (no new branch)
- [x] Record baseline: `make test` = 24 passed (plan note said 22; the real count at start was 24)
- [x] Record baseline: `make lint` = 12 findings, all pre-existing
- [x] Planning tracking: tracked (separate `docs(planning)` commits)

### Baseline records

- `make test` at `991db1d`: 24 passed.
- `make lint` at `991db1d`: 12 findings (ruff, `make lint` exits 0 by design).

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T3.1.1 Status write sends Waybar refresh signal (ipc.py, tests/test_ipc.py, tests/conftest.py) | done | `a2eefa3` | Amended: `tests/conftest.py` added (D10) |
| 1 | T3.1.2 README Waybar snippet with `"signal": 8` | done | `5ab4552` | JSON snippet verified |
| 2 | T3.2.1 Status returns to idle; plain scan writes status (cli.py, tests/test_cli.py) | done | `b651913` | depends on T3.1.1 |

Wave 2 started after wave 1 was all `done`.

End-of-wave-2 gate (orchestrator, serial):
- `make test`: 29 passed (24 baseline + 3 ipc + 2 cli).
- `make lint`: 12 findings, all pre-existing. The `cli.py` import finding moved from `13:66` to `14:86`, same unused `send_notification` import.
- `grep -c '"signal": 8' README.md` = 1.

Live check (user-run, not a gate): Waybar refresh timing with the module added per README. Record the result here when the user reports it.

**Open risk (must check before `make install-user`):** `pkill -RTMIN+8 waybar` terminates Waybar if Waybar does not handle that signal. Waybar's binary references `__libc_current_sigrtmin`, which suggests real-time handlers, but this was not confirmed. The running user install (`~/.local/bin/claudalizer`) does not change until `make install-user`, so the committed code is inert for now.

## Task reports

Workers ran inline (D8). Micro-TODOs: `planning/tasks/1.1.1.todo.md`, `planning/tasks/1.1.2.todo.md`, `planning/tasks/2.1.1.todo.md`.

## T3.1.1

- Status: done. Acceptance met: `tests/test_ipc.py` 8 passed; `tests/test_miner.py -k ipc` 1 passed.
- Files: `claudalizer/ipc.py` (+`WAYBAR_SIGNAL`, `_signal_waybar`, call in `emit_waybar_signal`); `tests/test_ipc.py` (+3 tests); `tests/conftest.py` (new, autouse stub of `_signal_waybar`).
- Code commit: `a2eefa3`.
- Tests: `python -m pytest tests/test_ipc.py -q` 8 passed; `make test` 27 passed at that point.
- Deviations: `tests/conftest.py` added. Without it, `tests/test_miner.py:515` and the dispatch tests would send a real `pkill -RTMIN+8 waybar` on every run (H6). Recorded as D10.
- Gotchas: `_signal_waybar` runs only after a successful status write.

## T3.1.2

- Status: done. Acceptance met: `"signal": 8` count 1; `RTMIN+8` count 1; snippet JSON parses.
- Files: `README.md` (+1 line in snippet, +2 sentences under it).
- Code commit: `5ab4552`.
- Deviations: none.

## T3.2.1

- Status: done. Acceptance met: `tests/test_cli.py` 2 passed; `tests/` 29 passed; lint has no new findings.
- Files: `claudalizer/cli.py` (+`datetime` import, +`emit_waybar_signal` import, +`_write_mined_status`, calls in `handle_scan` and `handle_watch`); `tests/test_cli.py` (new, 2 tests).
- Code commit: `b651913`.
- Deviations: the helper writes `extracted` and then `idle` in both scan and watch, not `extracted` only in scan. Without the `idle` write, the status sticks at `extracted` (D1 bug). Final state is always `idle`.
- Gotchas: `handle_watch` writes the mined status inside `if dossiers:` only. Idle on `KeyboardInterrupt` is unchanged.
