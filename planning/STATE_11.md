# Orchestration 11 State (`planning/STATE_11.md`)

Plan: `planning/EXECUTION_PLAN_11.md` (opencode session source)
Status: Wave 1 done. Wave 2 in progress.
Last Updated: 2026-11-25

## Pre-wave checklist
- [x] Git repository; branch `feat/opencode-source` created from `docs/opencode-goal` at `9b7d71d`; clean.
- [x] Planning artifacts tracked (D5).
- [x] User decisions recorded in `EXECUTION_PLAN_11.md` D1–D9.
- [x] Baseline: `make check`: ruff clean, 96 passed (Python 3.12.3). `make systemd-dry-run` exits 0.
- [x] User approves execution plan (2026-11-25).

## Wave board
| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T11.1.1 Source types and Claude Code adapter | done | c863214 | worktree |
| 1 | T11.1.2 Fixture builder and conftest guard | done | c3a2732 | worktree |
| 2 | T11.2.1 Core loop over sources | pending | | worktree |
| 2 | T11.2.2 opencode extraction functions | pending | | worktree |
| 2 | T11.2.3 Schema guard module | pending | | worktree |
| 3 | T11.3.1 OpencodeSource discovery and settle | pending | | |
| 4 | T11.4.1 Family extract, source_meta, pre-check | pending | | |
| 5 | T11.5.1 CLI flags and source wiring | pending | | worktree |
| 5 | T11.5.2 README and AGENTS docs | pending | | worktree |

## Task reports

## T11.1.1
- Status: done.
- Files: claudalizer/miner.py (SessionDossier +3 fields after stats; EXIT_CODE_PATTERN), claudalizer/sources/__init__.py (new), claudalizer/sources/claude_code.py (new), tests/test_source_core.py (new, 4 tests).
- Commit: `c863214` refactor(miner): add session source types and a Claude Code adapter.
- Tests: `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` -> 36 passed. `ruff check claudalizer tests/test_source_core.py` clean. Existing test files diff empty.
- Deviations: none (OSError guard on each changed_at term -> 0 as approved).
- Gotchas: tests must os.utime session dir/tree to old time for settled=True. ClaudeCodeSource yields refs even when changed_at==0.

## T11.1.2
- Status: done.
- Files: tests/conftest.py (+7, autouse `_no_real_opencode_db`), tests/opencode_fixture.py (new), tests/test_opencode_fixture.py (new, 3 tests).
- Commit: `c3a2732` (cherry-picked from wt/11.1.2 `755668f`) test: add an opencode database builder and keep tests off the live database.
- Tests: `python -m pytest tests/test_opencode_fixture.py -q` 3 passed; `make test` 99 passed; `ruff check tests` clean.
- Deviations: none.
- Gotchas: import as `from tests.opencode_fixture import OpencodeDB, tool_item, assistant_data`. Msg ids are `msg_<session>_<n>`. add_part sets time_created=time_updated. Columns: session_message(id, session_id, type, seq, time_created, time_updated, data); session_part(message_id, session_id, ordinal, type, call_id, time_created, time_updated, data). tool_item time.created=1000; assistant_data omits snapshot when None.

## Wave 1 gate (orchestrator)
- `make check`: ruff clean, 103 passed. `git diff --stat 9b7d71d -- tests/test_miner.py tests/test_scan_report.py tests/test_cli.py` empty.
- Process note: Agent-tool `isolation: worktree` auto-removes the worktree when the worker stops at the plan gate with no changes, and isolated workers cannot write to the main checkout. From W1 on, the orchestrator creates worktrees manually (`git worktree add -b wt/<id> .claude/worktrees/wt-<id>`) and spawns workers without isolation. Worktree branches are cherry-picked onto `feat/opencode-source` for linear history.
