# Orchestration 11 State (`planning/STATE_11.md`)

Plan: `planning/EXECUTION_PLAN_11.md` (opencode session source)
Status: Waves 1-4 done. Wave 5 in progress.
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
| 2 | T11.2.1 Core loop over sources | done | 6236c26 | worktree |
| 2 | T11.2.2 opencode extraction functions | done | be05dc9 | worktree |
| 2 | T11.2.3 Schema guard module | done | 5971135 | worktree |
| 3 | T11.3.1 OpencodeSource discovery and settle | done | 636d531 | |
| 4 | T11.4.1 Family extract, source_meta, pre-check | done | ac06c88 | |
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

## T11.2.1
- Status: done.
- Files: claudalizer/miner.py (SessionMiner __init__ sources, scan_and_mine, _mine_session wrapper, new _mine_ref; replace import), tests/test_source_core.py (+4 tests, fake sources).
- Commit: `be663a7` refactor(miner): mine sessions through a list of session sources.
- Tests: `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` -> 40 passed. `ruff check claudalizer tests/test_source_core.py` clean. Existing test files diff empty.
- Deviations: none. "Tmp root does not exist" info log dropped (accepted).
- Gotchas: try/except wraps the whole per-source loop, so any iter/extract failure skips the rest of that source. _mine_session uses adapter._changed_at (private) and a shim with dataclasses.replace for scratchpad_dir.

## T11.2.3
- Status: done
- Files: claudalizer/sources/opencode_schema.py (1-86), tests/test_opencode_schema.py (1-94)
- Commit: a57b35e
- Tests: `python -m pytest tests/test_opencode_schema.py -q` -> 8 passed; `ruff check` on both files clean
- Deviations: one extra test (test_known_migration_is_quiet)
- API for T11.3.1: `resolve_db_path(flag)`, `open_readonly(path) -> (conn, migration_id) | None` (caller must close conn), `KNOWN_OPENCODE_MIGRATION`, `REQUIRED_COLUMNS`, `_reset_warnings()`.
- Gotchas: warn-once keys are "columns", "migration", "sqlite_error" (one per kind per process). Empty flag string counts as unset. Path is URL-quoted via quote(str(path)).

## T11.2.2
- Status: done.
- Files: claudalizer/sources/opencode.py (new, ~205 lines), tests/test_opencode_source.py (new, ~125 lines, 11 tests).
- Commit: `9312204` feat(sources): extract prompts, tool errors and touched files from opencode sessions.
- Tests: `python -m pytest tests/test_opencode_source.py -q` -> 11 passed. `ruff check claudalizer/sources tests/test_opencode_source.py` clean.
- Deviations: one extra test (test_bad_json_rows_skipped). Case (c) sets exit_code to first non-zero matched code (approved).
- Gotchas for T11.3.1: public API in claudalizer/sources/opencode.py: slug_for_directory(directory)->str; load_messages(conn,sid)->list[dict{id,type,seq,data}]; load_parts(conn,sid)->list[dict{message_id,ordinal,type,call_id,data}]; assistant_content(message_data, part_rows); user_prompts(messages); tool_error_events(content); failed_turn_events(messages); touched_files(messages, contents, directory); extract_session(conn,sid,directory)->(prompts, tool_errors, touched_files) for ONE session (family merge/ordering is the caller's job). Touched files are absolute (joined to directory), cap 500 per session. is_git_discernable only matches capitalised Edit/Write, so lowercase opencode edit/write errors are kept only because they have status=error.

## Wave 2 gate (orchestrator)
- Cherry-picked wt/11.2.1 `be663a7` -> `6236c26`, wt/11.2.2 `9312204` -> `be05dc9`, wt/11.2.3 `a57b35e` -> `5971135`.
- `make check`: ruff clean, 126 passed. Existing test files diff vs `9b7d71d` empty.
- Review notes: `scratchpad_changed_since` in miner.py is no longer called by the core (kept; out of scope to delete). Workers added two extra tests (`test_bad_json_rows_skipped`, `test_known_migration_is_quiet`).

## T11.3.1
- Status: done.
- Files: claudalizer/sources/opencode.py (imports; new tail: _MARKER_SQL, _now, _find_root, OpencodeSource), tests/test_opencode_source.py (+7 tests, helpers at end).
- Commit: see `git log -1 --grep="find settled opencode"`.
- Tests: `python -m pytest tests/test_opencode_source.py -q` 18 passed; `ruff check claudalizer tests` clean.
- Deviations: none. skipped["up_to_date"] is an int, skipped["active"] a list of "slug/id".
- Gotchas for T11.4.1: `self._families` is reset per iter_sessions: `{root_id: [{"id","directory","time_created"}, ...]}`, root first. Marker per member is not stored. extract() is a root-only stub reopening the DB via open_readonly; touched_files is filled from extract_session. skip_if_unchanged stored as `self.skip_if_unchanged`, unused. Exceptions in iter_sessions are swallowed by the core (logged warning).

## Wave 3 gate (orchestrator)
- `make check`: ruff clean, 133 passed. Existing test files diff vs `9b7d71d` empty.
- Review note: a parent loop (A->B->A) splits into two roots under the "stop at last row reached" rule; acceptable per SPEC, but each loop member becomes its own family.

## T11.4.1
- Status: done.
- Files: claudalizer/sources/opencode.py (OpencodeSource: __init__ state, _db_mtimes, iter_sessions pre-check + child sort, extract rewritten, ~272-375), tests/test_opencode_source.py (+8 tests and _family/_spy helpers appended at end).
- Commit: ac06c88 feat(sources): fold opencode subagents into their root and skip unchanged polls.
- Tests: python -m pytest tests/test_opencode_source.py tests/test_opencode_schema.py tests/test_source_core.py -q -> 42 passed. ruff check claudalizer tests clean.
- Deviations: none. Per orchestrator, mtimes + had_unsettled are committed to self only after the generator yields every ref (aborted pass stays stale). Unsettled families filtered out by target_slug do not count. open_readonly None inside iter_sessions returns without storing state.
- Gotchas for T11.5.1: constructor is OpencodeSource(db_path, skip_if_unchanged=False); source name "opencode"; extract raises RuntimeError if DB unavailable (core logs). Pre-check state is per instance, so build one OpencodeSource per watch process (not per tick). distill_all not exercised; distill_session works on opencode dossier offline.

## Wave 4 gate (orchestrator)
- `make check`: ruff clean, 141 passed. Existing test files diff vs `9b7d71d` empty.
- For T11.5.1: `handle_watch` builds `SessionMiner` once outside the loop, so the pre-check state on the one `OpencodeSource` persists across ticks.
