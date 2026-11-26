# Execution Plan 12: git history for mined memories (`planning/EXECUTION_PLAN_12.md`)

Orchestration: 12
Source: Magic Wand re-rank 2026-11-25 (`planning/GOALS.md`, commit `c7aca83`). Goals G_dossier-stable, G_churn, G_mem-git, G_mem-baseline.
Status: Approved by user (2026-11-25). Implementation not started. Reviewed on spec and standards axes.
Base branch: `feat/memory-git`, to be created from `feat/opencode-source` at `c7aca83` (D1). Planning is tracked (D8).
Baseline: `make check`: ruff clean, 141 passed (Python 3.12.3).

## Goal & Scope

**Goal (user's terms).** "Bring in git for tracking mined memories at each snapshot/change including forced changes by default." The user does not "like that things could arbitrarily overwrite the memory files and fail." After this orchestration, every pass that changes `~/.claude-mined-memories` leaves a git commit, so any earlier `dossier.json`, `memory.md` or `PROJECT_MEMORY.md` can be restored.

**In scope**
- G_dossier-stable: a re-mine that changes nothing (dossier fields other than `scan_timestamp`, and the bytes of the scratchpad copies) does not rewrite `dossier.json`.
- G_churn: the watch loop re-mines a session at most once every 60 s.
- G_mem-git: a new `claudalizer/memory_git.py`; one commit per scan pass or distill run that changed files; an "external changes" commit first when the tree is dirty; `--no-git` to turn it off; commits under `/tmp/claudalizer.lock`.
- G_mem-baseline: with git on, the first pass that finds no `.git` creates the repo and commits the existing tree as a baseline.
- README, AGENTS.md and SPEC updates for the above.

**Out of scope**
- Running the new code on the real `~/.claude-mined-memories` (restarting `claudalizer-watch`, or any live `scan`/`distill`). That creates the real repo and is ask-first (G_mem-live, after this orchestration).
- G_distill-report, G_distill-offloop, G_memory-fresh, G_llm-live, G_restore-cli, G_mirror-filter.
- Changing `SETTLE_DEBOUNCE_SECONDS` (2 s), the size cap, or the lock timeout (10 s).
- Changes to the systemd units, pushes, pull requests and other remote actions.

**Verbatim constraints**
- User: "commit every snapshot/change … including --force re-distills, by default".
- User decision: "One commit per pass", "Re-mine at most every 60 s", "watch only", "Auto on first pass", "Commit them first" (dirty tree), "claudalizer bot identity".
- AGENTS.md: runtime stays stdlib-only; run `make test` after changing `claudalizer/` or `tests/`; never delete or modify contents under `~/.claude-mined-memories/` directly; ask first before changing the settle window, size cap or lock timeout.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-25 | New branch `feat/memory-git` from `feat/opencode-source` | Keeps the opencode work reviewable on its own | User |
| D2 | 2026-11-25 | One commit per scan pass or distill run that changed files; a pass with no change makes no commit | Readable history, cheap | User |
| D3 | 2026-11-25 | Churn fix: the watch loop does not re-mine a session whose `dossier.json` is younger than 60 s (`WATCH_MIN_REMINE_SECONDS = 60`). `scan` is not throttled. The 2 s settle window is unchanged. Skips count under a new `"recent"` key | User chose a re-mine interval over changing the settle rule | User |
| D4 | 2026-11-25 | Git is on by default for `scan`, `distill` and `watch`; global `--no-git` turns it off. The first pass that finds no `.git` runs `git init`, writes `.gitignore`, and commits the existing tree as `baseline` | "by default"; auto-init | User |
| D5 | 2026-11-25 | A dirty tree at the start of a pass is committed first as `external: changes found before <pass>` | Whatever the pass then overwrites stays restorable | User |
| D6 | 2026-11-25 | Repo-local identity `claudalizer <claudalizer@localhost>`; commits run with `commit.gpgsign=false`, `core.hooksPath=/dev/null`, `core.excludesFile=/dev/null`, and with `GIT_*` variables removed from the environment | Independent of the user's global git config; keeps the user's email out of the history | User (identity); recon (flags) |
| D7 | 2026-11-25 | Workers use Sonnet; escalation goes to Opus. `make check` after every wave. The orchestrator creates worktrees itself (`git worktree add -b wt/<id> .claude/worktrees/wt-<id>`), spawns workers without Agent-tool isolation, and cherry-picks their commits | Same as orchestration 11, including its worktree lesson | User |
| D8 | 2026-11-25 | Planning is tracked, in separate `docs(planning):` commits | Same as orchestrations 1–11 | User |
| D9 | 2026-11-25 | "Unchanged" means: the new dossier dict equals the stored one with `scan_timestamp` removed, **and** the scratchpad copies' bytes did not change. Then `dossier.json` is not rewritten; its mtime is bumped with `os.utime` so the up-to-date check holds. With `force`, the dossier is always written | `test_scratchpad_rewrite_is_recaptured` rewrites a scratchpad file without changing any dossier field | Recon |
| D10 | 2026-11-25 | `file_lock` is never nested. The miner commits inside the lock it already takes in `scan_and_mine`. The distiller takes the lock itself, only around each session's file writes and around its pass commit, never around the LLM call | `flock` on a second file descriptor in the same process blocks until the 10 s timeout. A 108 s LLM call must not hold the lock against the watcher | Recon |

## Recon Log

- Branch `feat/opencode-source` is clean at `c7aca83`. There is no `docs/decisions/`, so no ADR constraints apply.
- Sizes: `miner.py` 493 lines, `distiller.py` 314, `cli.py` 358. Tests: `test_miner.py` 546, `test_distiller.py` 422, `test_cli.py` 244, `test_source_core.py` 124, `test_scan_report.py` 120, `conftest.py` 41.
- Measured 2026-11-25, read-only (a bare git dir outside the root, `GIT_WORK_TREE=~/.claude-mined-memories`):
  - `git add -A` of the whole tree took 5.1 s for 35,051 files, 34,383 of them scratchpad copies.
  - The commit took 0.2 s. The repo is 123 MB loose and 54 MB after `git gc`.
  - A no-change `git status --porcelain` takes 0.05 s.
- `scan_status.json` (the Waybar state) is in the memories root and changes on every scan, so it goes in `.gitignore`. Temp files to ignore: `*.tmp` (dossier writes) and `.PROJECT_MEMORY.*.tmp` (distiller).
- `snapshot_scratchpad` already skips `.git`, `venv`, `.venv`, `node_modules` and `__pycache__`, so no nested repo is copied into the root.
- `miner.py`:
  - `SessionMiner._empty_skips()` (~365) returns `{"active": [], "up_to_date": 0, "no_content": 0}`.
  - `_mine_ref` (~429): the up-to-date check is `ref.changed_at <= dossier_json.stat().st_mtime`; the dossier is written atomically (~477–487); `scan_timestamp=time.time()` (~461).
  - `file_lock(lock_path, timeout=10.0)` (~58) uses `flock`.
- `distiller.py`:
  - `distill_session` (~199) writes `memory.md`, then `_append_to_project_memory` (~240) rebuilds `PROJECT_MEMORY.md`, ordered by `scan_timestamp`.
  - `distill_all` (~280) loops over sessions. It takes no lock.
- `cli.py`:
  - `format_skip_summary` (~74).
  - `handle_scan` (~108) has an auto-distill loop at ~136, `handle_distill` (~149), `handle_watch` (~170).
  - `build_parser` (~290) holds the global flags, `main` (~340).
- Tests that rely on re-mining: `test_scratchpad_rewrite_is_recaptured` (`test_miner.py` ~330–364) changes only scratchpad bytes (see D9). `_mine_session(..., force=True)` is called twice in `test_failed_dossier_write_keeps_previous_dossier` (~423–455), so `force` must always write.
- `tests/test_cli.py` `_fake_miner` takes `**kwargs`, so new `SessionMiner` keywords are tolerated.
- The global git config sets no `commit.gpgsign` or `core.hooksPath`; D6 turns them off anyway.
- The watch drop-in `~/.config/systemd/user/claudalizer-watch.service.d/llm.conf` sets `CLAUDALIZER_LLM_ENDPOINT`. The package is an editable install, so a restart picks up new code.

## Hazard Notes

- H1: No test may create a repo in, or write to, the real `~/.claude-mined-memories`. T12.1.1 adds an autouse conftest fixture that sets `CLAUDALIZER_TESTING=1`; while it is set, `MemoryRepo` raises `RuntimeError` for a root that resolves to `~/.claude-mined-memories`.
- H2: Tests run inside the claudalizer repo. `memory_git` must run git with `cwd=root`, with `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and every other `GIT_*` variable stripped, so it can never touch the claudalizer repo.
- H3: Do not nest `file_lock` (D10). Every `MemoryRepo` call is made by a caller that already holds the lock; `MemoryRepo` itself takes no lock.
- H4: `MemoryRepo` methods never raise on git failure. They log a warning and return `None`/`False`, and mining continues. A missing `git` binary warns once per process.
- H5: `snapshot_scratchpad` is monkeypatched through `miner_module.shutil.copy2` in tests, so the byte comparison in D9 must read the copies after the snapshot, not depend on `copy2` internals.
- H6: Worktrees for waves with more than one task (W1, W3), per D7. Workers write `planning/tasks/*.todo.md` and `STATE_12.md` reports in the main checkout at `/home/andrew/AI/claudalizer/planning/`.
- H7: Never run live `claudalizer scan`/`distill`/`watch`, `make scan`, `make watch`, `make distill`, `make systemd-install`/`make systemd-uninstall`, or `systemctl --user restart claudalizer-watch`.
- H8: `make lint` fails on ruff findings; every task runs `ruff check` on its files.

## Wave Table

| Wave | Task | Files (must edit / can create) | Depends on |
| --- | --- | --- | --- |
| 1 | T12.1.1 `memory_git` module and conftest guard (G_mem-git, G_mem-baseline) | create `claudalizer/memory_git.py`, `tests/test_memory_git.py`; edit `tests/conftest.py` | — |
| 1 | T12.1.2 Stable dossiers and re-mine interval (G_dossier-stable, G_churn) | edit `claudalizer/miner.py`; create `tests/test_remine.py` | — |
| 1 | T12.1.3 Distiller lock and written log (G_mem-git) | edit `claudalizer/distiller.py`, `tests/test_distiller.py` | — (codes against the `MemoryRepo` contract below) |
| 2 | T12.2.1 Miner commits each pass (G_mem-git) | edit `claudalizer/miner.py`; create `tests/test_miner_git.py` | T12.1.1, T12.1.2 |
| 3 | T12.3.1 CLI flags and wiring (G_mem-git, G_churn) | edit `claudalizer/cli.py`, `tests/test_cli.py`, `tests/test_scan_report.py` | T12.1.3, T12.2.1 |
| 3 | T12.3.2 Docs (README, AGENTS, SPEC) | edit `README.md`, `AGENTS.md`, `planning/SPEC.md` | T12.2.1 (names fixed by this plan) |

Within each wave the file sets do not overlap. No task edits `ipc.py`, `sources/`, `systemd/` or the `Makefile`.

## `MemoryRepo` contract (shared by T12.1.1, T12.1.3, T12.2.1, T12.3.1)

```python
# claudalizer/memory_git.py
GIT_IGNORE_LINES = ["scan_status.json", "*.tmp", ".PROJECT_MEMORY.*.tmp"]
BOT_NAME, BOT_EMAIL = "claudalizer", "claudalizer@localhost"

class MemoryRepo:
    def __init__(self, root: Path, enabled: bool = True) -> None: ...
    @property
    def active(self) -> bool: ...                 # enabled, git available, and ensure() succeeded
    def ensure(self) -> bool: ...                 # init + .gitignore + baseline commit if no .git; False if disabled/unavailable/failed
    def commit_external(self, before: str) -> Optional[str]: ...    # dirty tree -> commit "external: changes found before <before>"; returns short sha or None
    def commit_pass(self, title: str, lines: List[str]) -> Optional[str]: ...  # git add -A; commit only if something is staged; body = lines; returns short sha or None
```

- The caller holds `file_lock` for every call (H3). Methods never raise on git errors (H4).
- The commit title for a pass is `<kind>: <summary>`, for example `scan: 2 mined, 1 re-mined` or `distill: 3 distilled (--force)`. Body lines look like `mined <slug>/<sid>`, `re-mined <slug>/<sid>`, `re-mined (--force) <slug>/<sid>`, `distilled <slug>/<sid>`, `re-distilled (--force) <slug>/<sid>`.
- A disabled repo (`enabled=False`) makes every method a no-op that returns `None`/`False`.

## Task Specs

### T12.1.1 `memory_git` module and conftest guard

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** create `claudalizer/memory_git.py`, `tests/test_memory_git.py`; edit `tests/conftest.py` (append only). Scratch goes in `.development/` (excluded).
- **Depends on:** none.
- **Spec:** implement the `MemoryRepo` contract above.
  - `_git(*args)`: `subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "-c", "core.excludesFile=/dev/null", *args], cwd=root, env=<os.environ without GIT_* keys>, capture_output=True, text=True, timeout=120)`. A `FileNotFoundError` marks git unavailable and warns once per process (module-level flag and `_reset_warnings()` for tests). A non-zero exit logs a warning with stderr and returns `None`.
  - `ensure()`:
    - If disabled, return False.
    - If `root/.git` exists, return True.
    - Otherwise:
      1. `root.mkdir(parents=True, exist_ok=True)`.
      2. `git init -q -b main`.
      3. `git config user.name claudalizer`, `git config user.email claudalizer@localhost`.
      4. Write `.gitignore` with `GIT_IGNORE_LINES`.
      5. `git add -A`, then `git commit -q --allow-empty -m "baseline: existing memories"`.
    - Log one info line with the file count. Return True on success.
  - `commit_external(before)`: when `git status --porcelain` is non-empty, `git add -A` and commit `external: changes found before <before>`.
  - `commit_pass(title, lines)`: `git add -A`. If `git diff --cached --quiet` exits 0, return None. Otherwise `git commit -q -F -` with `title + "\n\n" + "\n".join(lines)` on stdin. Return `git rev-parse --short HEAD`.
  - Guard (H1): `__init__` raises `RuntimeError` when `CLAUDALIZER_TESTING` is set and `Path(root).expanduser().resolve() == (Path.home()/".claude-mined-memories").resolve()`. Production never sets `CLAUDALIZER_TESTING`.
  - `conftest.py`: append an autouse fixture that sets `CLAUDALIZER_TESTING=1` with `monkeypatch.setenv`.
- **Constraints:** stdlib only. Do not import `miner` or `distiller`. Do not touch `cli.py`.
- **Anchors:** `ipc.py` (log-and-continue style); `sources/opencode_schema.py` `_warn_once`/`_reset_warnings` (the warn-once pattern).
- **New tests** (`tests/test_memory_git.py`; skip the module with `pytest.importorskip`-style `shutil.which("git")` check):
  - `test_ensure_creates_repo_with_baseline_and_gitignore`
  - `test_ensure_is_idempotent`
  - `test_commit_pass_commits_only_when_changed` (a second call with no change returns None, and the commit count is unchanged)
  - `test_commit_message_has_title_and_lines`
  - `test_commit_external_records_dirty_tree`
  - `test_scan_status_and_tmp_files_are_ignored`
  - `test_disabled_repo_is_noop`
  - `test_missing_git_warns_once_and_continues` (monkeypatch `subprocess.run` to raise `FileNotFoundError`)
  - `test_git_env_vars_do_not_leak` (set `GIT_DIR` to a bogus path; commits still land in `tmp_path`)
  - `test_commits_use_bot_identity`
  - `test_real_memories_root_refused_under_tests`
- **Acceptance:** `python -m pytest tests/test_memory_git.py -q` passes; `ruff check claudalizer/memory_git.py tests/test_memory_git.py tests/conftest.py` is clean.
- **Commit:** `feat(memory-git): add a git history helper for the memories root`

### T12.1.2 Stable dossiers and re-mine interval

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** edit `claudalizer/miner.py`; create `tests/test_remine.py`.
- **Depends on:** none.
- **Spec:**
  1. `_empty_skips()` gains `"recent": 0`.
  2. `SessionMiner.__init__` gains `min_remine_seconds: float = 0.0`, stored on `self`. Add module constant `WATCH_MIN_REMINE_SECONDS = 60.0` (used by `cli.py` in T12.3.1).
  3. In `_mine_ref`, before the up-to-date check: if `dossier.json` exists, `force` is off, `self.min_remine_seconds > 0`, and `time.time() - dossier_json.stat().st_mtime < self.min_remine_seconds`, count `skipped["recent"]` and return `None`.
  4. Stable write (D9): when `dossier.json` exists and `force` is off, compute a digest of the destination scratchpad copies before and after `snapshot_scratchpad` (sha256 over sorted `(relative path, bytes)`, a helper `_tree_digest(path) -> str` that returns `""` for a missing dir). Load the stored dossier. If the new `dossier.to_dict()` equals the stored dict with `scan_timestamp` removed from both, and the two digests are equal, do not write. Instead `os.utime(dossier_json)`, count `skipped["up_to_date"]`, log at debug, and return `None`.
  5. With `force`, or when the content changed, write as today.
  6. Record each written dossier in `self.pass_log: List[str]`, reset at the start of `scan_and_mine`. The entries are `mined <slug>/<sid>`, `re-mined <slug>/<sid>`, or `re-mined (--force) <slug>/<sid>` (`re-mined` when `dossier.json` existed before the write). T12.2.1 uses it.
- **Constraints:** do not change `SETTLE_DEBOUNCE_SECONDS` or `file_lock`. Do not edit existing test files. Keep `_mine_session` behaviour (force always writes).
- **Anchors:** `miner.py` `_empty_skips` (~365), `def scan_and_mine` (~373), `def _mine_ref` (~429), the atomic write (~477).
- **Reference:** the existing atomic-write block; `newest_mtime` for walking a tree.
- **New tests** (`tests/test_remine.py`, `tmp_path` sessions built like `tests/test_miner.py` `test_scratchpad_rewrite_is_recaptured`):
  - `test_unchanged_remine_does_not_rewrite_dossier` (bytes identical; mtime bumped; counted `up_to_date`)
  - `test_transcript_touch_without_new_content_keeps_dossier`
  - `test_scratchpad_byte_change_rewrites_dossier`
  - `test_force_always_rewrites`
  - `test_min_remine_interval_skips_recent_dossier` (counted `recent`)
  - `test_min_remine_zero_by_default`
  - `test_pass_log_names_mined_and_remined`
- **Acceptance:** `python -m pytest tests/test_remine.py tests/test_miner.py tests/test_scan_report.py tests/test_source_core.py -q` passes; `ruff check claudalizer/miner.py tests/test_remine.py` is clean.
- **Commit:** `feat(miner): skip unchanged re-mines and space out watch re-mines`

### T12.1.3 Distiller lock and written log

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** edit `claudalizer/distiller.py`, `tests/test_distiller.py` (add tests only; existing tests unchanged).
- **Depends on:** none. Code against the `MemoryRepo` contract; tests use a small fake repo class, not `memory_git`.
- **Spec:**
  1. `MemoryDistiller.__init__(memories_root, repo=None, lock_file=None)`. Both default to `None`, which keeps today's behaviour exactly: no lock, no commit.
  2. `distill_session`: the LLM call stays outside any lock. When `lock_file` is set, the write of `memory.md` and the `PROJECT_MEMORY.md` rebuild run inside `with file_lock(lock_file):` (import from `claudalizer.miner`). Before the first write of a pass, under that lock, call `repo.commit_external("distill")` once per pass, if `repo` is set.
  3. Record each written session in `self.pass_log`: `distilled <slug>/<sid>` or, when `memory.md` existed and `force` is on, `re-distilled (--force) <slug>/<sid>`.
  4. Add `commit_pass(self, kind: str = "distill") -> Optional[str]`. If `repo` is set and `pass_log` is non-empty, take the lock (if set), call `repo.commit_pass(f"{kind}: {summary}", pass_log)` where summary is `"<n> distilled"` plus `" (--force)"` when any entry is forced, clear `pass_log` and the per-pass external flag, and return the sha.
  5. `distill_all` calls `self.commit_pass()` at the end.
- **Constraints:** never hold the lock during `call_llm_completion` (D10). Do not nest `file_lock`. Do not import `memory_git`. Do not edit `cli.py`.
- **Anchors:** `distiller.py` `class MemoryDistiller` (~196), `def distill_session` (~199), `_append_to_project_memory` (~240), `def distill_all` (~280); `miner.file_lock` (~58).
- **New tests** (appended to `tests/test_distiller.py`; use the `fake_llm` fixture and a `FakeRepo` recording calls):
  - `test_distill_all_commits_one_pass_with_lines`
  - `test_forced_redistill_is_marked_in_pass_log`
  - `test_no_commit_when_nothing_written` (no endpoint, or LLM returns None)
  - `test_lock_not_held_during_llm_call` (the fake LLM tries `file_lock(lock, timeout=0.2)` itself and succeeds)
  - `test_external_commit_once_per_pass`
  - `test_without_repo_behaviour_unchanged`
- **Acceptance:** `python -m pytest tests/test_distiller.py -q` passes; `ruff check claudalizer/distiller.py tests/test_distiller.py` is clean.
- **Commit:** `feat(distiller): record each distill pass and write under the mining lock`

### T12.2.1 Miner commits each pass

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** edit `claudalizer/miner.py`; create `tests/test_miner_git.py`.
- **Depends on:** T12.1.1 (`MemoryRepo`), T12.1.2 (`pass_log`, `recent`).
- **Spec:**
  1. `SessionMiner.__init__` gains `repo: Optional["MemoryRepo"] = None` (string annotation, `TYPE_CHECKING` import).
  2. In `scan_and_mine`, inside the existing `with file_lock(...)`:
     - Before any source runs: `repo.ensure()`, then `repo.commit_external("scan")`.
     - After all sources: if `pass_log` is non-empty, `repo.commit_pass(title, self.pass_log)`, with title `scan: <n> mined, <m> re-mined`, omitting zero parts, and appending ` (--force)` when `force`.
     - Store the returned sha in `self.last_commit` (None when no commit).
  3. Git errors never change the return value of `scan_and_mine` (H4).
- **Constraints:** no second `file_lock` (H3). Do not edit existing tests or `cli.py`.
- **Anchors:** `miner.py` `def scan_and_mine` (~373), `with file_lock` (~383); `memory_git.MemoryRepo` (T12.1.1); `self.pass_log` (T12.1.2).
- **New tests** (`tests/test_miner_git.py`; real `MemoryRepo` in `tmp_path`; skip without git):
  - `test_first_scan_creates_baseline_then_scan_commit`
  - `test_scan_with_no_change_makes_no_commit`
  - `test_remine_commit_lists_session`
  - `test_forced_scan_commit_marked_force`
  - `test_hand_edit_committed_as_external_before_scan`
  - `test_previous_dossier_restorable_from_git` (`git show HEAD~1:<path>` returns the old dossier)
  - `test_repo_none_changes_nothing` (no `.git` is created)
- **Acceptance:** `python -m pytest tests/test_miner_git.py tests/test_remine.py tests/test_miner.py tests/test_source_core.py tests/test_scan_report.py -q` passes; `ruff check claudalizer/miner.py tests/test_miner_git.py` is clean.
- **Commit:** `feat(miner): commit each scan pass to the memories history`

### T12.3.1 CLI flags and wiring

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** edit `claudalizer/cli.py`, `tests/test_cli.py`, `tests/test_scan_report.py` (add tests only).
- **Depends on:** T12.1.3, T12.2.1.
- **Spec:**
  1. Global flag `--no-git` (`action="store_true"`): "Do not record memory changes in git".
  2. `build_repo(args) -> MemoryRepo`: `MemoryRepo(Path(args.memories_root), enabled=not args.no_git)`.
  3. `handle_scan` and `handle_watch` pass `repo=build_repo(args)` to `SessionMiner`. `handle_watch` also passes `min_remine_seconds=WATCH_MIN_REMINE_SECONDS`. Build each once (watch: before the loop).
  4. Every `MemoryDistiller` built in `handle_scan`, `handle_distill` and `handle_watch` gets `repo=` and `lock_file=Path(args.lock_file)`. After each auto-distill batch in `scan` and `watch`, call `distiller.commit_pass("distill")`. `handle_distill` relies on `distill_all`'s own commit.
  5. `format_skip_summary` adds `N re-mined less than 60 s ago` only when `skipped.get("recent")` is non-zero, so the existing output is unchanged otherwise.
- **Constraints:** existing CLI tests must pass unchanged. Do not change notification, history or Waybar behaviour.
- **Anchors:** `cli.py` `format_skip_summary` (~74), `def handle_scan` (~108), `def handle_distill` (~149), `def handle_watch` (~170), `def build_parser` (~290).
- **New tests:**
  - `test_cli.py`:
    - `test_no_git_flag_disables_repo`
    - `test_watch_passes_repo_and_min_remine`
    - `test_scan_then_distill_makes_scan_and_distill_commits`: real `SessionMiner` plus the `fake_llm` fixture in `tmp_path`, through `handle_scan --auto-distill` with `--llm-endpoint`. `git log` shows `baseline`, `scan: …` and `distill: …`.
  - `test_scan_report.py`: `test_format_skip_summary_mentions_recent_only_when_nonzero`.
- **Acceptance:** `python -m pytest tests/test_cli.py tests/test_scan_report.py -q` passes; `ruff check claudalizer/cli.py tests/test_cli.py tests/test_scan_report.py` is clean.
- **Commit:** `feat(cli): record memory changes in git by default`

### T12.3.2 Docs

- **Repo:** claudalizer. **Model:** Sonnet.
- **Files in scope:** edit `README.md`, `AGENTS.md`, `planning/SPEC.md`.
- **Depends on:** T12.2.1 (names in this plan are final).
- **Spec:**
  - README: a short "Memory history" section. Cover:
    - the repo in the memories root and the baseline on first run
    - one commit per pass, with an example `git log --oneline`
    - external-change commits
    - `--no-git`
    - how to restore a file (`git -C ~/.claude-mined-memories log -- <path>`, `git checkout <rev> -- <path>`)
    - what is ignored
    - the 60 s watch re-mine interval
  - AGENTS.md:
    - *Find Things*: `claudalizer/memory_git.py`, and the new test files.
    - *Infrastructure*: the memories root is a git repo with the bot identity.
    - *Non-Obvious*: an unchanged re-mine does not rewrite the dossier; the watch interval is 60 s; the lock is not nested.
    - *Never*: "run git commands that rewrite history in `~/.claude-mined-memories`".
  - SPEC: a new subsection "Memory history (G_mem-git)" with D2–D6, D9 and D10 as rules. Update §3.4 global flags with `--no-git`, and the skip-key list with `recent`.
- **Constraints:** docs only; short plain sentences matching each file's style.
- **Acceptance:** `git diff --check` is clean; `grep -n "no-git\|memory_git\|Memory history" README.md AGENTS.md planning/SPEC.md` shows the additions; `make test` passes.
- **Commit:** `docs: describe the git history of mined memories`

## Wave Gates

- **Pre-wave (orchestrator):**
  - Create `feat/memory-git` from `feat/opencode-source`.
  - Commit `EXECUTION_PLAN_12.md`, `PROMPT_TEMPLATE_12.md` and `STATE_12.md` as `docs(planning):`.
  - Create the W1 worktrees.
- **After each wave:**
  - Cherry-pick the worktree commits.
  - Run `make check` serially.
  - Confirm the existing tests in `tests/test_miner.py` and `tests/test_distiller.py` are not edited, except that `test_distiller.py` may gain tests in T12.1.3.
  - Commit the `STATE_12.md` reports as `docs(planning):`.
- **After W3:**
  - `grep -rn "claude-mined-memories" tests/` shows no test using the real root.
  - `make systemd-dry-run` exits 0, and the watch unit is unchanged.
- **Follow-up, not in this orchestration (ask-first, G_mem-live):**
  1. Restart `claudalizer-watch`. Its first pass creates the real repo and the baseline, about 5 s.
  2. Confirm `git -C ~/.claude-mined-memories log --oneline | head` shows `baseline`.
  3. Confirm watch ticks over unchanged sessions add no commits.
- **Escalation** (`wave-orchestration`):
  - A micro-plan that is off-spec twice: the orchestrator writes the micro-plan.
  - One retry with `FAILED VERIFICATION: ...`, then re-run on Opus.
  - A malformed report gets feedback and one retry, then the task re-runs on Opus.
  - A need for out-of-scope edits: re-scope the task spec in this file.
