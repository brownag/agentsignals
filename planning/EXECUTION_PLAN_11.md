# Execution Plan 11: opencode session source (`planning/EXECUTION_PLAN_11.md`)

Orchestration: 11
Source: Magic Wand re-rank 2026-11-25. Goals G_oc-seam, G_oc-fixture, G_oc-read, G_oc-guard and G_oc-cli in `planning/GOALS.md`. Spec: `planning/SPEC.md` §3.1 *Session sources* and *opencode source*, §3.4 global flags, §4.1a. Research: `planning/research/OPENCODE_SESSIONS.md`.
Status: Approved by user (2026-11-25). Implemented; all waves done 2026-11-25.
Base branch: `feat/opencode-source`, created from `docs/opencode-goal` at `9b7d71d`. Planning is tracked (D5).
Baseline: `make check`: ruff clean, 96 passed (Python 3.12.3). `make systemd-dry-run` exits 0.

## Goal & Scope

**Goal (user's terms).** `claudalizer scan` and `watch` mine finished opencode sessions into dossiers and memory, alongside Claude Code sessions. "Every session is mined, subagents included: each subagent session's prompts, errors and touched files are folded into its parent's dossier." User, 2026-11-24: "mine all of it."

**In scope**
- G_oc-seam: split `miner.py` into a shared core plus a Claude Code adapter behind `SessionSource`, with no change in behaviour.
- G_oc-fixture: a builder for an opencode-shaped test database, plus a conftest guard that keeps tests away from the live database.
- G_oc-read: opencode extraction and discovery: the settle rule, the change marker and the subagent fold.
- G_oc-guard: a read-only open, the schema and migration guard, and failure isolation.
- G_oc-cli: the `--source` and `--opencode-db` global flags, the watch pre-check wiring, and README/AGENTS docs.

**Out of scope**
- G_oc-live (a real scan of `~/.local/share/opencode/opencode.db`) needs the user's approval and is a separate step (D6).
- G_llm-live, G22, G13, G_churn, G_sanitize, G_oc-worktree.
- Any change to `distiller.py`, the 2 s settle window, the size cap, or the lock timeout.
- The opencode HTTP API, SSE, `opencode export`, `tool-output/`, `shell/`, `snapshot/` and `/tmp/opencode`.
- Changes to the systemd units. The watch unit runs `claudalizer watch` and picks up the new defaults. Installing is ask-first.
- Pushes, pull requests and other remote actions.

**Verbatim constraints**
- GOALS: "The project slug comes from `session_v2.directory`, so opencode and Claude Code sessions in one repo share a `PROJECT_MEMORY.md`."
- GOALS: "An unknown schema migration skips the opencode source with a warning; the watch loop does not crash." SPEC §3.1 refines this: an unknown *migration* warns and keeps reading; *missing columns* skip the source.
- GOALS: "Tests use a fixture database built in `tmp_path`; `make check` passes."
- SPEC §3.1: "The source never writes to the database." "Never use `immutable=1`."
- AGENTS.md:
  - Runtime stays stdlib-only.
  - Run `make test` after changing `claudalizer/` or `tests/`.
  - Never modify `/tmp/claude-1000` or `~/.claude-mined-memories/` directly.
  - Ask first before `make systemd-install` and before long live `watch` runs.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-25 | Work on `feat/opencode-source`, branched from `docs/opencode-goal` | Keeps the SPEC commit and keeps feature work apart | User |
| D2 | 2026-11-25 | Parallel waves with disjoint files. The schema guard is its own module, `claudalizer/sources/opencode_schema.py`. §4.1a tests are spread over `test_source_core.py`, `test_opencode_fixture.py`, `test_opencode_source.py` and `test_opencode_schema.py`. The review split two oversized tasks, giving 5 waves and 9 tasks | Disjoint files per wave; right-sized tasks | User (shape); review (split) |
| D3 | 2026-11-25 | `SessionMiner()` defaults to the Claude Code source only; `cli.py` builds the list from `--source`. An autouse conftest fixture points `OPENCODE_DB` and `XDG_DATA_HOME` at missing paths under `tmp_path` | No test can open the live opencode database | User |
| D4 | 2026-11-25 | Workers use Sonnet; escalation goes to Opus | The seam refactor and the source carry the most risk | User |
| D5 | 2026-11-25 | Gate: `make check` after every wave; `make systemd-dry-run` after W5. Planning is tracked, in separate `docs(planning):` commits | Same as orchestrations 1–10 | User |
| D6 | 2026-11-25 | G_oc-live is not part of this orchestration | A live scan writes real memories and needs approval | User |
| D7 | 2026-11-24 | Subagent sessions are folded into their root's dossier, not skipped | "mine all of it" | User (GOALS) |
| D8 | 2026-11-25 | `--source` defaults to `claude,opencode`; `OPENCODE_QUIET_SECONDS = 600`; opencode error text is `"<type> error: <message>"` | Recorded in SPEC §3.1; the user reviewed it | SPEC |
| D9 | 2026-11-25 | The watch pre-check skips a tick only if the previous pass found no unsettled family | Otherwise a busy or unmarked family whose database stops changing is never mined (spec review) | Review → SPEC |

## Recon Log

- Branch `feat/opencode-source` was clean at `9b7d71d`. There is no `docs/decisions/`, so no ADR constraints apply.
- Sizes: `claudalizer/miner.py` 489 lines, `cli.py` 322, `distiller.py` 378. Tests: `test_miner.py` 546, `test_cli.py` 129, `test_scan_report.py` 120, `conftest.py` 10.
- `pyproject.toml` `packages.find include = ["claudalizer*"]` already includes a `claudalizer.sources` subpackage.
- `tests/test_miner.py`:
  - Imports `SessionMiner, decode_slug, is_git_discernable, parse_transcript_events, snapshot_scratchpad, file_lock, is_file_settled` from `claudalizer.miner`.
  - Calls `miner._mine_session(slug, None, session_id, scratch, force=True)` (lines ~423, 437, 455).
  - Monkeypatches `miner_module.json.dump` (~435) and `miner_module.shutil.copy2` (~215).
- `tests/test_cli.py` `_fake_miner` replaces `cli.SessionMiner` with a class taking `**kwargs`, so a new `sources=` keyword is tolerated.
- `cli.py` builds `SessionMiner(tmp_root=..., claude_projects=..., memories_root=..., lock_file=...)` (keywords) in `handle_scan` (~85) and `handle_watch` (~145). `build_parser()` is at ~256.
- `scan_and_mine` returns early when `tmp_root` is missing. After the split this has to mean the Claude Code adapter yields nothing, so opencode still runs.
- `newest_mtime` raises `OSError` on a missing path; `scratchpad_changed_since` guards with `is_dir()`.
- `EXIT_CODE_PATTERN = re.compile(r"Exit code (\d+)")` (~149).
- `distiller.py` reads dossier fields with `.get` (`decoded_path`, `user_prompts`, `tool_errors`, `scratchpad_files`, `scan_timestamp`), so an opencode dossier with an empty `scratchpad_files` is expected to distill.
- Live opencode database (read-only checks, 2026-11-25):
  - Every column listed in SPEC §3.1 exists.
  - The latest migration is `20261120004954_machine-key`; the `migration` table has columns `id` and `time_completed`.
  - Indexes include `session_message_session_seq_idx` and `session_part_session_message_idx` (`session_id`, `message_id`, `ordinal`).
  - Part rows carry `type` both in the column and in `data`.
  - Tool names include `shell`, `patch` (`patchText`), `read`, `grep`, `glob`, `skill` and `subagent`.
  - `snapshot.files` holds relative paths.
- The installed CLI (`~/.local/bin/claudalizer`, from `make install-user`) is not editable, so G_oc-live will need a reinstall.
- AGENTS.md still says `make lint` "never fails the build". That has been wrong since G17 (T11.5.2 fixes it).

## Hazard Notes

- H1: Tests must never open `~/.local/share/opencode/opencode.db` (D3). The conftest guard lands in W1, before any code reads a database.
- H2: Keep `SessionMiner._mine_session(slug, decoded_path, session_id, scratchpad_dir, force=False)` working. The dossier write (`json.dump`) and `snapshot_scratchpad` (`shutil.copy2`) stay in `miner.py`, because the tests monkeypatch both through `miner_module`.
- H3: The Claude Code adapter's `changed_at` must reproduce today's check. It is `max(newest_mtime(scratchpad) if it is a dir else 0, transcript mtime if it exists else 0)`, compared with the dossier mtime by `>`.
- H4: opencode times are epoch **milliseconds**; dossier mtimes are seconds.
- H5: Import cycle. `sources/claude_code.py` imports helpers from `claudalizer.miner` at module level. `miner.py` must import `ClaudeCodeSource` lazily, inside `SessionMiner.__init__`. `sources/__init__.py` must not import `miner` at module level; use `TYPE_CHECKING` or string annotations for `ToolErrorEvent`.
- H6: Worktrees. W1, W2 and W5 have more than one task in this repo, so those workers run in git worktrees.
  - The planning files are committed before W1, so worktrees can see them.
  - Workers write their `STATE_11.md` report in the **main checkout** (`/home/andrew/AI/claudalizer/planning/STATE_11.md`), not in the worktree. The orchestrator commits it.
  - The orchestrator merges each worktree's code commits into `feat/opencode-source`, then runs `make check` serially.
- H7: `make lint` fails on ruff findings, so every task runs `ruff check` on its files.
- H8: Do not run live `claudalizer scan`/`watch`, `make scan`, `make watch`, or `make systemd-install`/`make systemd-uninstall`.

## Wave Table

| Wave | Task | Files (must edit / can create) | Depends on |
| --- | --- | --- | --- |
| 1 | T11.1.1 Source types and Claude Code adapter (G_oc-seam, part 1) | edit `claudalizer/miner.py` (regex and dossier fields only); create `claudalizer/sources/__init__.py`, `claudalizer/sources/claude_code.py`, `tests/test_source_core.py` | — |
| 1 | T11.1.2 Fixture builder and conftest guard (G_oc-fixture) | edit `tests/conftest.py`; create `tests/opencode_fixture.py`, `tests/test_opencode_fixture.py` | — |
| 2 | T11.2.1 Core loop over sources (G_oc-seam, part 2) | edit `claudalizer/miner.py`, `tests/test_source_core.py` | T11.1.1 |
| 2 | T11.2.2 opencode extraction functions (G_oc-read, part 1) | create `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py` | T11.1.1, T11.1.2 |
| 2 | T11.2.3 Schema guard module (G_oc-guard) | create `claudalizer/sources/opencode_schema.py`, `tests/test_opencode_schema.py` | T11.1.1, T11.1.2 |
| 3 | T11.3.1 OpencodeSource discovery and settle (G_oc-read, part 2) | edit `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py` | T11.2.1, T11.2.2, T11.2.3 |
| 4 | T11.4.1 Family extract, source_meta, pre-check, scan-level guard (G_oc-read and G_oc-guard, part 3) | edit `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py` | T11.3.1 |
| 5 | T11.5.1 CLI flags and source wiring (G_oc-cli) | edit `claudalizer/cli.py`, `tests/test_cli.py` | T11.4.1 |
| 5 | T11.5.2 README and AGENTS docs (G_oc-cli) | edit `README.md`, `AGENTS.md` | T11.4.1 |

Within each wave the file sets do not overlap. No task edits `distiller.py`, `ipc.py`, `systemd/`, `Makefile` or `planning/SPEC.md`.

## Task Specs

### T11.1.1 Source types and Claude Code adapter (G_oc-seam, part 1)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:**
  - Must edit `claudalizer/miner.py`, for exactly two changes: the regex and the dossier fields.
  - Can create `claudalizer/sources/__init__.py`, `claudalizer/sources/claude_code.py`, `tests/test_source_core.py`.
  - Scratch goes in `.development/` (untracked).
- **Depends on:** none.
- **Spec:**
  1. `sources/__init__.py` defines `SessionRef` (a frozen dataclass), `Extraction` (a dataclass) and the `SessionSource` Protocol, with the fields and signatures exactly as in SPEC §3.1 *Session sources*. Follow H5 for the `ToolErrorEvent` annotation.
  2. `sources/claude_code.py` defines `ClaudeCodeSource(tmp_root: Path, claude_projects: Path)` with `name = "claude_code"`. Its helpers are imported from `claudalizer.miner` at module level.
     - `iter_sessions(target_slug)` reproduces the walk in `scan_and_mine`:
       - Skip non-directories and names starting with `.`.
       - Skip slugs that don't start with `-`.
       - Apply the `target_slug` filter.
       - Set `decoded_path` with `decode_slug`.
       - Skip session folders that are not directories or start with `.`.
       - Yield nothing when `tmp_root` is missing.
     - `settled = is_file_settled(session_dir, SETTLE_DEBOUNCE_SECONDS)`. `changed_at` follows H3.
     - `extract(ref)` returns `Extraction(user_prompts, tool_errors from parse_transcript_events(claude_projects/slug/f"{sid}.jsonl"), scratchpad_dir=tmp_root/slug/sid/"scratchpad", touched_files=[], transcript_found=<transcript exists>, source_meta={})`.
  3. In `miner.py`:
     - Add three fields to `SessionDossier` after `stats`: `source: str = "claude_code"`, `touched_files: List[str] = field(default_factory=list)` and `source_meta: Dict[str, Any] = field(default_factory=dict)`.
     - Change `EXIT_CODE_PATTERN` to `re.compile(r"Exit code:? (\d+)")`.
     - Make no other `miner.py` change.
- **Constraints:** do not edit any existing test file, and do not touch `cli.py`. Do not wire `ClaudeCodeSource` into `SessionMiner` yet (that is T11.2.1).
- **Anchors:** `miner.py` `class SessionDossier` (~38), `EXIT_CODE_PATTERN` (~149), `def scan_and_mine` (~361; the walk to reproduce), `def _mine_session` (~417; the transcript-path and changed check, for H3).
- **Reference:** the current `scan_and_mine` walk.
- **New tests** (`tests/test_source_core.py`):
  - `test_exit_code_pattern_matches_both_forms`: `has_nonzero_exit_code("Exit code 1")` and `("Exit code: 1")` are both true, and `"Exit code: 0"` is false.
  - `test_dossier_has_source_defaults`: `SessionDossier(...).to_dict()` has the three defaults.
  - `test_claude_code_source_matches_walk`: in a `tmp_path` layout with one valid session, one `.hidden` session and one non-dash slug, exactly one `SessionRef` is yielded, with the right `decoded_path` and `changed_at`.
  - `test_claude_code_source_missing_tmp_root_yields_nothing`.
- **Acceptance:**
  - `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` passes.
  - `git diff --stat -- tests/test_miner.py tests/test_scan_report.py tests/test_cli.py` is empty.
  - `ruff check claudalizer tests/test_source_core.py` is clean.
- **Commit:** `refactor(miner): add session source types and a Claude Code adapter`

### T11.1.2 Fixture builder and conftest guard (G_oc-fixture)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `tests/conftest.py`; can create `tests/opencode_fixture.py`, `tests/test_opencode_fixture.py`.
- **Depends on:** none.
- **Spec:**
  1. In `conftest.py`, add an autouse fixture that uses `monkeypatch.setenv` to set `OPENCODE_DB` to `tmp_path/"no-opencode"/"opencode.db"` (which does not exist) and `XDG_DATA_HOME` to `tmp_path/"xdg-data"`. Keep the existing Waybar fixture.
  2. `tests/opencode_fixture.py` holds a builder, `OpencodeDB(path)`, usable as a context manager or with an explicit `close()` that commits:
     - It creates the tables `migration(id TEXT PRIMARY KEY, time_completed INTEGER)`, `session_v2`, `session_message` (PK `id`) and `session_part` (PK `message_id, ordinal`). Include at least the columns in the SPEC §3.1 table plus `time_created` on all three session tables. Create the indexes `session_message_session_seq_idx (session_id, seq)` and `session_part_session_message_idx (session_id, message_id, ordinal)`.
     - It inserts migration `20261120004954_machine-key` unless `migration=None` is passed.
     - `add_session(id, directory, parent_id=None, time_busy=1000, time_idle=2000, idle_outcome="succeeded", time_created=1000, time_updated=1000, version="2.4.1", project_id="p1")`.
     - `add_message(session_id, type, data, seq=None, time_updated=1000, time_created=1000) -> msg_id` auto-increments `seq` for each session and stores `data` as JSON.
     - `add_part(message_id, session_id, ordinal, type, data, call_id=None, time_updated=1000)`.
     - `drop_column(table, column)`.
     - Pure helpers: `tool_item(id, name, status="completed", input=None, metadata=None, content_text=None, error=None, time_completed=None) -> dict`, which builds `{type:"tool", id, name, state:{status, input, metadata, content:[{type:"text",text}], error}, time:{created, completed}}`, and `assistant_data(content=None, snapshot_files=None) -> dict`.
     - All times are epoch ms.
- **Constraints:** this task is tests only. Never open a path under `~/.local/share/opencode`. Stdlib `sqlite3` only.
- **Anchors:** `tests/conftest.py` (10 lines); the SPEC §3.1 table (`grep -n "Columns read" planning/SPEC.md`).
- **Reference:** `_make_mineable_session` in `tests/test_miner.py`.
- **New tests** (`tests/test_opencode_fixture.py`):
  - `test_fixture_builds_family_with_inline_and_part_content`: a root and one child, inline tool items and part-row tool items, read back with `sqlite3`, checking the counts and the `json_extract` fields.
  - `test_conftest_points_opencode_db_at_missing_path`.
  - `test_drop_column_removes_column`.
- **Acceptance:** `python -m pytest tests/test_opencode_fixture.py -q` passes; `make test` gives 96 plus the new tests; `ruff check tests` is clean.
- **Commit:** `test: add an opencode database builder and keep tests off the live database`

### T11.2.1 Core loop over sources (G_oc-seam, part 2)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `claudalizer/miner.py`, `tests/test_source_core.py`.
- **Depends on:** T11.1.1.
- **Spec:** SPEC §3.1 *Session sources*, core loop steps 1–4.
  1. `SessionMiner.__init__` gains `sources: Optional[list] = None`. `None` means `[ClaudeCodeSource(self.tmp_root, self.claude_projects)]`, imported lazily inside `__init__` (H5, D3).
  2. `scan_and_mine(debounce, force, target_slug)`:
     - Reset `self.skipped`, take `file_lock` once, and loop over the sources and their `iter_sessions(target_slug)`.
     - When debounce is on and `ref.settled` is false, append `f"{slug}/{sid}"` to `skipped["active"]`.
     - Otherwise call `self._mine_ref(source, ref, force)`.
     - Wrap each source's iteration (and each `extract`) in `try/except Exception`. Log `logger.warning("Session source %s failed: %s", source.name, e)` and move on to the next source.
     - Remove the early return for a missing `tmp_root`; the adapter handles that now.
  3. `_mine_ref(source, ref, force)`:
     - Up-to-date check: if `dossier.json` exists, `force` is off, and `ref.changed_at <= dossier.json` mtime, count `up_to_date` and return `None`. Log the existing "changed since last mine" info line when re-mining.
     - Call `source.extract(ref)`. Snapshot `scratchpad_dir` with `snapshot_scratchpad` when it is not `None`, else `[], []`.
     - Apply the no-content rule as today (`touched_files` does not count).
     - Build the `SessionDossier` with `source=ref.source`, `touched_files` and `source_meta`, and add `touched_count` to `stats`.
     - Write atomically with the existing temp-file, `json.dump`, fsync and `os.replace` code.
  4. Keep `_mine_session(slug, decoded_path, session_id, scratchpad_dir, force=False)` as a thin wrapper. It builds a `ClaudeCodeSource` ref for that session, using the adapter's `changed_at` logic, then calls `_mine_ref`. Behaviour must stay identical for `test_failed_dossier_write_keeps_previous_dossier`. Note that it ignores the passed `scratchpad_dir` only if that equals the adapter's path; otherwise it honours the argument.
- **Constraints:** do not edit any existing test file or `cli.py`. Keep the skip keys and the log messages.
- **Anchors:** `miner.py` `class SessionMiner` (~341), `def scan_and_mine` (~361), `def _mine_session` (~417); `sources/claude_code.py` (from T11.1.1).
- **Reference:** the current `_mine_session` body is the behaviour to preserve.
- **New tests** (appended to `tests/test_source_core.py`; fake sources are small classes in the test file):
  - `test_source_error_does_not_stop_other_sources`: a fake source that raises, then a fake source with one session, gives one dossier and a warning in `caplog`.
  - `test_missing_tmp_root_still_runs_other_sources`.
  - `test_dossier_source_comes_from_ref`.
  - `test_unsettled_ref_counted_active`.
- **Acceptance:**
  - `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` passes.
  - `git diff --stat 9b7d71d -- tests/test_miner.py tests/test_scan_report.py tests/test_cli.py` is empty.
  - `ruff check claudalizer tests/test_source_core.py` is clean.
- **Commit:** `refactor(miner): mine sessions through a list of session sources`

### T11.2.2 opencode extraction functions (G_oc-read, part 1)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** can create `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py`.
- **Depends on:** T11.1.1 (`EXIT_CODE_PATTERN`, the package) and T11.1.2 (the fixture).
- **Spec:** pure functions over an open `sqlite3.Connection`. There is no discovery, settle rule or guard here. Implement each rule below; each comes from SPEC §3.1 *Extraction*.
  - `slug_for_directory(directory) -> str` is `re.sub(r"[^A-Za-z0-9]", "-", directory)`.
  - `load_messages(conn, session_id)` runs `SELECT type, seq, data FROM session_message WHERE session_id=? ORDER BY seq`. `load_parts(conn, session_id)` runs `SELECT message_id, ordinal, type, call_id, data FROM session_part WHERE session_id=? ORDER BY message_id, ordinal`. Rows with bad JSON are skipped. Message ids are needed to join parts, so also select `id` in `load_messages`.
  - `assistant_content(message_data, part_rows) -> list`:
    - Part items come first, by `ordinal`, then the inline `data.content` items.
    - A part item is its `data` dict. Set `type` from the column if `data` lacks it, and `id` from `call_id` if `data` lacks it.
  - `user_prompts`: `type == "user"` messages. Take `data.text`, stripped, and keep it if `len >= MIN_PROMPT_LENGTH`. Every other type is excluded (`synthetic`, `system`, `skill`, `compaction` and the rest).
  - Tool errors, for each content item with `type == "tool"`:
    - (a) `state.status == "error"`: `error_output = f"{error.get('type','unknown')} error: {error.get('message','')}"`, with `exit_code=None`.
    - (b) `name == "shell"`, `state.status == "completed"`, and a non-zero int `metadata.exit`, or `metadata.signal` or `metadata.timeout` truthy: set `exit_code = metadata.exit`. `error_output` is the text items of `state.content` joined by `"\n"`. Append `f"\nExit code: {exit}"` when `exit` is not `None` and the text doesn't already match `EXIT_CODE_PATTERN` with that code.
    - (c) A shell item with no `metadata.exit`: its text is non-zero by `has_nonzero_exit_code`.
    - The other fields:
      - `tool_use_id` is the item's `id`, and `tool_name` is its `name`.
      - `command_or_input` is the first present of `input.command`, `input.filePath`, the first line of `input.patchText`, or `json.dumps(input, sort_keys=True)`, cut to 500 characters.
      - `timestamp` is ISO-8601 UTC (`datetime.fromtimestamp(ms/1000, timezone.utc).isoformat()`) of `time.completed`, else `time.created`, else `None`.
    - Drop the event when `is_git_discernable(tool_name, command_or_input, error_output)` is true.
  - Failed turns: an `idle` message with `data.outcome == "failed"` adds `ToolErrorEvent(tool_use_id=None, tool_name="session", command_or_input=None, error_output=f"turn error: {(data.get('error') or {}).get('message','')}")`.
  - `touched_files` is the union of three sets. Relative paths are joined to `directory` with `os.path.join` and normalised with `os.path.normpath`. Sort, de-duplicate, and cap at 500.
    - `data.snapshot.files[]` of assistant messages.
    - `input.filePath` of `edit` and `write` items.
    - Paths from `patch` items' `patchText`, matched by `^\*\*\* (?:Add|Update|Delete) File: (.+)$` (multiline).
  - `extract_session(conn, session_id, directory) -> tuple[list[str], list[ToolErrorEvent], list[str]]` ties these together.
- **Constraints:** read-only SQL. Use `.get` for every JSON field; a non-dict value is treated as empty. Import from `claudalizer.miner`; do not edit it.
- **Anchors:** SPEC (`grep -n "Extraction\*, per family member" planning/SPEC.md`); `miner.py` `ToolErrorEvent` (~28), `has_nonzero_exit_code`, `is_git_discernable` (~157), `MIN_PROMPT_LENGTH` (~23).
- **Reference:** how `parse_transcript_events` in `miner.py` builds and filters events.
- **New tests** (`tests/test_opencode_source.py`):
  - `test_slug_from_directory_matches_claude_code_rule`
  - `test_prompts_from_user_messages_only`
  - `test_inline_and_part_content_merged_in_order`
  - `test_tool_error_status_recorded`
  - `test_failed_shell_exit_code_recorded`
  - `test_zero_exit_shell_not_recorded`
  - `test_shell_timeout_recorded`
  - `test_failed_idle_turn_recorded`
  - `test_touched_files_from_snapshot_edit_and_patch`
  - `test_command_or_input_fallback_chain`
- **Acceptance:** `python -m pytest tests/test_opencode_source.py -q` passes; `ruff check claudalizer/sources tests/test_opencode_source.py` is clean.
- **Commit:** `feat(sources): extract prompts, tool errors and touched files from opencode sessions`

### T11.2.3 Schema guard module (G_oc-guard)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** can create `claudalizer/sources/opencode_schema.py`, `tests/test_opencode_schema.py`.
- **Depends on:** T11.1.1 (the package) and T11.1.2 (the fixture).
- **Spec:** SPEC §3.1 *Database* and *Schema guard*.
  - `resolve_db_path(flag: Optional[str]) -> Path` resolves the flag, then `$OPENCODE_DB`, then `$XDG_DATA_HOME/opencode/opencode.db`, then `~/.local/share/opencode/opencode.db`. An empty env value counts as unset.
  - `REQUIRED_COLUMNS: dict[str, set[str]]` comes from the SPEC table. Add `KNOWN_OPENCODE_MIGRATION = "20261120004954_machine-key"`.
  - `open_readonly(path) -> Optional[tuple[sqlite3.Connection, str]]`:
    - A missing file returns `None` with a debug log only.
    - Otherwise connect with `sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)`. Never use `immutable`, and never run a PRAGMA that writes.
    - Missing tables or columns (`pragma table_info`): warn once per process, naming the `table.column` items, close, and return `None`.
    - Migration: `SELECT id FROM migration ORDER BY id DESC LIMIT 1`. If there is no row, the id is `""`. An empty id, or one that sorts after the known id, warns once per process and the open continues.
    - Any `sqlite3.Error` (including "file is not a database") warns, closes, and returns `None`.
    - Success returns `(conn, migration_id)`.
  - The once-per-process state is a module-level `set`. Add `_reset_warnings()` for tests.
- **Constraints:** no writes; stdlib only; do not import `opencode.py`.
- **Anchors:** SPEC (`grep -n "Schema guard" planning/SPEC.md`).
- **Reference:** the log-and-continue style of `ipc.py`.
- **New tests** (`tests/test_opencode_schema.py`):
  - `test_missing_column_returns_none_and_warns`
  - `test_unknown_migration_warns_and_reads`
  - `test_empty_migration_table_warns_and_reads`
  - `test_missing_db_is_silent`
  - `test_corrupt_db_returns_none_and_warns`
  - `test_open_does_not_modify_db` (bytes and mtime unchanged after open, query and close)
  - `test_opencode_db_resolution_order`
- **Acceptance:** `python -m pytest tests/test_opencode_schema.py -q` passes; `ruff check claudalizer/sources/opencode_schema.py tests/test_opencode_schema.py` is clean.
- **Commit:** `feat(sources): open the opencode database read-only behind a schema guard`

### T11.3.1 OpencodeSource discovery and settle (G_oc-read, part 2)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py`.
- **Depends on:** T11.2.1, T11.2.2, T11.2.3.
- **Spec:** SPEC §3.1 *Families*, *Discovery and change marker* and *Settled*.
  - Add `OPENCODE_QUIET_SECONDS = 600` and `class OpencodeSource` with `name = "opencode"` and `__init__(db_path: Path, skip_if_unchanged: bool = False)`. The pre-check itself is T11.4.1; store the flag only.
  - `iter_sessions(target_slug)`:
    1. `open_readonly(db_path)`. `None` means yield nothing. Close the connection in `try/finally`.
    2. Marker query, once:
       ```
       SELECT s.id, s.parent_id, s.directory, s.time_created, s.time_busy, s.time_idle,
              max(coalesce(s.time_updated,0), coalesce(s.time_idle,0),
                  coalesce((SELECT max(time_updated) FROM session_message WHERE session_id=s.id),0),
                  coalesce((SELECT max(time_updated) FROM session_part WHERE session_id=s.id),0))
       FROM session_v2 s
       ```
    3. Roots: follow `parent_id` through the result rows until it is null or names a missing row. A loop, or a depth over 64, stops at the last row reached and logs a warning. Group the rows by root.
    4. For each family:
       - `changed_at = max(marker) / 1000`.
       - `settled = (all members have time_idle is not None and time_idle >= (time_busy or 0)) and now - changed_at >= SETTLE_DEBOUNCE_SECONDS`, **or** `now - changed_at >= OPENCODE_QUIET_SECONDS`.
       - `slug = slug_for_directory(root.directory)`. Skip the family if `target_slug` is set and differs.
    5. Yield `SessionRef(source="opencode", slug, session_id=root.id, decoded_path=root.directory, changed_at, settled)`. Store the family members (ids, directories, `time_created`) in `self._families[root.id]` for T11.4.1.
  - `extract(ref)` is a stub for now: root-only `extract_session`, giving an `Extraction` with `scratchpad_dir=None`, `transcript_found=True` and `source_meta={}`. T11.4.1 replaces it.
  - Tests use `time.time` via a module-level `_now()` that they can monkeypatch.
- **Constraints:** do not edit `miner.py` or `opencode_schema.py`. If the core needs a change, STOP and report.
- **Anchors:** `opencode.py` (T11.2.2 functions); `opencode_schema.open_readonly`; `miner.SessionMiner(sources=[...])` (T11.2.1).
- **Reference:** `ClaudeCodeSource` in `sources/claude_code.py`.
- **New tests** (appended to `tests/test_opencode_source.py`; each drives `SessionMiner(tmp_root=tmp_path/"none", claude_projects=..., memories_root=tmp_path/"mem", lock_file=tmp_path/"lock", sources=[OpencodeSource(db)])`):
  - `test_busy_session_not_mined`
  - `test_unmarked_session_mined_after_quiet_window`
  - `test_part_update_triggers_remine`
  - `test_unchanged_session_is_up_to_date`
  - `test_busy_subagent_holds_root`
  - `test_orphan_subagent_becomes_root`
  - `test_target_slug_filters_families`
- **Acceptance:** `python -m pytest tests/test_opencode_source.py -q` passes; `ruff check claudalizer tests` is clean.
- **Commit:** `feat(sources): find settled opencode session families`

### T11.4.1 Family extract, source_meta, pre-check, scan-level guard (part 3)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `claudalizer/sources/opencode.py`, `tests/test_opencode_source.py`.
- **Depends on:** T11.3.1.
- **Spec:**
  - `extract(ref)`:
    - Reopen the database with `open_readonly`. `None` raises `RuntimeError`, which the core logs.
    - For each member of `self._families[ref.session_id]` (root first, then children by `time_created`), run `extract_session(conn, member_id, member_directory)`. Concatenate the prompts and errors, and union, sort and cap `touched_files` at 500.
    - Return an `Extraction` with `scratchpad_dir=None` and `transcript_found=True`. `source_meta` holds:
      - `project_id`, `opencode_version` (the root's `version`) and `idle_outcome` (the root's), read with one `SELECT` on `session_v2`
      - `subagent_session_ids` (sorted)
      - `schema_migration` (from `open_readonly`)
  - Watch pre-check (SPEC *Watch pre-check*, D9). When `skip_if_unchanged` is set, `iter_sessions` stats the DB file and `<db>-wal` (a missing file counts as 0). If both mtimes equal the stored values and the previous pass yielded no `settled=False` ref, return without opening the database. Store the mtimes and a "had unsettled" flag after each pass.
- **Constraints:** as for T11.3.1. If `distill_all` (used only in T11.5.1) fails on an opencode dossier, STOP and report: `distiller.py` is out of scope.
- **Anchors:** `OpencodeSource.extract` and `iter_sessions` (T11.3.1).
- **New tests** (appended to `tests/test_opencode_source.py`):
  - `test_subagent_folded_into_root`
  - `test_dossier_records_source_fields`
  - `test_missing_column_skips_source_with_warning` (a second `ClaudeCodeSource` with one session is still mined)
  - `test_corrupt_db_does_not_stop_scan`
  - `test_db_opened_read_only` (bytes and mtime unchanged after a full `scan_and_mine`)
  - `test_watch_skips_queries_when_db_unchanged` (spy on `open_readonly`)
  - `test_watch_rechecks_while_family_unsettled`
  - `test_opencode_dossier_distills_offline`: `MemoryDistiller(memories_root).distill_session(...)` writes `memory.md` without error. This is a read-only check of the out-of-scope distiller.
- **Acceptance:** `python -m pytest tests/test_opencode_source.py tests/test_opencode_schema.py tests/test_source_core.py -q` passes; `ruff check claudalizer tests` is clean.
- **Commit:** `feat(sources): fold opencode subagents into their root and skip unchanged polls`

### T11.5.1 CLI flags and source wiring (G_oc-cli)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `claudalizer/cli.py`, `tests/test_cli.py`.
- **Depends on:** T11.4.1.
- **Spec:** SPEC §3.4 global flags.
  - In `build_parser()`, add global `--source`, with a type function that splits on commas, strips, and accepts only `claude` and `opencode`; anything else raises `argparse.ArgumentTypeError`. The default is `"claude,opencode"`. Also add `--opencode-db` (default `None`).
  - Add `build_sources(args, watch: bool) -> list`:
    - `claude` gives `ClaudeCodeSource(Path(args.tmp_root), Path(args.claude_projects))`.
    - `opencode` gives `OpencodeSource(resolve_db_path(args.opencode_db), skip_if_unchanged=watch)`.
  - Pass `sources=build_sources(args, watch=...)` to `SessionMiner` in `handle_scan` (`watch=False`) and `handle_watch` (`watch=True`).
  - Mention opencode in the parser description.
- **Constraints:** existing `test_cli.py` tests must keep passing unchanged; new tests may be added. Do not change notification or history behaviour. Do not edit `distiller.py` (if `distill_all` fails, STOP).
- **Anchors:** `cli.py` `def handle_scan` (~84), `def handle_watch` (~140), `def build_parser` (~256).
- **New tests** (in `tests/test_cli.py`):
  - `test_source_flag_limits_sources` (`--source claude` builds no `OpencodeSource`; `--source bogus` raises `SystemExit`)
  - `test_watch_builds_opencode_source_with_precheck`
  - `test_both_sources_share_project_memory`: a real `SessionMiner`, with a Claude Code session in `tmp_path` and a fixture opencode session for the same directory, mined through `build_sources`, then `MemoryDistiller(memories_root).distill_all()`. One `PROJECT_MEMORY.md` has two `## Session` sections.
- **Acceptance:** `python -m pytest tests/test_cli.py -q` passes; `ruff check claudalizer/cli.py tests/test_cli.py` is clean.
- **Commit:** `feat(cli): add --source and --opencode-db and mine opencode by default`

### T11.5.2 README and AGENTS docs (G_oc-cli)

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** must edit `README.md`, `AGENTS.md`.
- **Depends on:** T11.4.1 (module and constant names). The flag names are fixed by SPEC §3.4.
- **Spec:**
  - README: add a short "opencode sessions" section covering:
    - what is mined (prompts, tool errors, failed shells and failed turns, touched files; no file content)
    - how the database path is resolved (flag, then `OPENCODE_DB`, then the XDG default), and that channel databases need `--opencode-db`
    - that access is read-only
    - that subagents are folded into their parent
    - the shared `PROJECT_MEMORY.md`
    - `--source`
  - AGENTS.md:
    - *Find Things*: add `claudalizer/sources/` (`claude_code.py`, `opencode.py`, `opencode_schema.py`), update the `miner.py` line, and update `tests/` to name the new test files.
    - *Infrastructure*: add the opencode database path and the read-only rule.
    - *Never*: add "write to `opencode.db`".
    - *Non-Obvious*: add the 600 s quiet fallback and the watch pre-check rule. Correct the `make lint` line: it now fails on ruff findings (G17).
- **Constraints:** docs only. Plain, short sentences that match the existing style. Do not edit SPEC.
- **Acceptance:** `git diff --check` is clean; `grep -n "opencode" README.md AGENTS.md` shows the new sections; `make test` passes.
- **Commit:** `docs: describe opencode session mining`

## Wave Gates

- **Pre-wave (orchestrator):** commit `planning/EXECUTION_PLAN_11.md`, `PROMPT_TEMPLATE_11.md`, `STATE_11.md` and the `planning/SPEC.md` review edits as `docs(planning):` before spawning W1 (H6).
- **After each wave:**
  - Merge the worktree code commits.
  - Run `make check` serially.
  - Confirm `git diff --stat 9b7d71d -- tests/test_miner.py tests/test_scan_report.py` is empty, and do the same for `tests/test_cli.py` until W5, where T11.5.1 adds to it.
  - Commit the `STATE_11.md` reports as `docs(planning):`.
- **After W5:**
  - `make systemd-dry-run` exits 0, and the rendered watch unit still runs `claudalizer watch`.
  - `grep -n "\-\-source\|\-\-opencode-db" planning/SPEC.md claudalizer/cli.py` shows the flag names agree.
- **Escalation** (`wave-orchestration`):
  - A micro-plan that is off-spec twice: the orchestrator writes the micro-plan.
  - One retry with `FAILED VERIFICATION: ...`, then re-run on Opus. Never a third Sonnet attempt.
  - A malformed report gets feedback and one retry, then the task re-runs on Opus.
  - A need for out-of-scope edits is a decomposition bug: re-scope the task spec in this file, never widen the worker's permissions ad hoc.
