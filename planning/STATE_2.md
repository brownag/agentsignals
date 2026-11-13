# Orchestration 2 State (`planning/STATE_2.md`)

Plan: `planning/EXECUTION_PLAN_2.md` (G5, G6, G7, G9)
Status: Complete. Waves 1-3 done on `g5-g6-g7-g9`. G5, G6, G7, G9 closed in GOALS.md.
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
| 2 | T2.2.1 Failed git results kept; exit code 0 not a failure; README | done | 2c0a311, 0c7354f | `make test` 18 passed after wave 2 |
| 3 | T2.3.1 SPEC §4.1 slug and corrupt-transcript tests | done | 7b891bc | no change to miner.py needed; corrupt-recovery passed as written |

Wave 2 starts only after wave 1 is all `done`. Wave 3 starts only after wave 2 is all `done`.

End-of-wave-3 gate (orchestrator, serial): done.

- `make check` exit 0: 24 passed (test_ipc + test_miner), lint 12 findings, all pre-existing (no new).
- `make systemd-dry-run` exit 0; rendered path unit contains `DirectoryNotEmpty=/tmp/claude-1000`.
- SPEC §4.1 and §4.3 tests present and passing: test_slug_decoding, test_filter_oversized_scratchpad, test_jsonl_corrupt_recovery, test_git_state_filtering, test_sway_dispatch_when_swaysock_present, test_hyprland_dispatch, test_headless_environment_no_crash.
- Commit log `master..g5-g6-g7-g9` shows one commit per task plus docs(planning) commits; no mixed commits.

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

## 2.2.1

- Status: done (wave 2, inline).
- Code commit: 2c0a311 `fix(miner): keep failed git commands and ignore exit code 0`. Docs commit: 0c7354f `docs(readme): describe the actual noise filter`.
- Files: `claudalizer/miner.py` (`import re`; `has_nonzero_exit_code`; `is_git_discernable` git clause needs empty output; `has_exit_err` uses the helper); `tests/test_miner.py` (`test_git_state_filtering`); `README.md` lines 12-13.
- Tests: `pytest tests/test_miner.py -q -k "git or transcript"` 3 passed; full file 17 passed.
- Lint: 12 (no new). Deviations: none. D5 judgment (exit 0 not a failure) implemented as a regex over `Exit code (\d+)`.

## 2.3.1

- Status: done (wave 3, inline).
- Code commit: 7b891bc `test(miner): add slug decoding and corrupt-transcript spec tests`.
- Files: `tests/test_miner.py` (`test_decode_slug` renamed to `test_slug_decoding`, with real-path cases under tmp_path; new `test_jsonl_corrupt_recovery`). `miner.py` not changed.
- Tests: `pytest tests/test_miner.py -q -k "slug or corrupt"` 2 passed.
- Deviations: the spec example `-home-user-work-src-my-pkg` does not exist on disk, and `decode_slug` resolves against the filesystem, so the cases build real paths under tmp_path instead.

## Branch note

- `test_filter_oversized_scratchpad` (ff66a16, from orchestration 1) was cherry-picked onto this branch as `8e89750`, because G9 requires it and the branch base (`g1-durable-capture`) lacked it.
- Branch `g5-g6-g7-g9` is based on `g1-durable-capture` (5bf8361) with planning carried over in `3185174` and the G1 test in `8e89750`. It is not yet merged to `master`. Merge or rebase onto `master` needs the user's instruction.

