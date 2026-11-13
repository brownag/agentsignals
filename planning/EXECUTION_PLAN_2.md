# Execution Plan 2: Goals G5, G6, G7, G9 (`planning/EXECUTION_PLAN_2.md`)

Orchestration: 2
Source goals: `planning/GOALS.md` [G5], [G6], [G7], [G9]
Status: Draft, awaiting user approval. No implementation started.
Starts after: orchestration 1 wave 3 (T1.3.1) is done and G1 is closed.
Base branch: `g1-durable-capture` (the G1 code, which is at `5bf8361` on `master` too). New branch `g5-g6-g7-g9`.

## Goal & Scope

**Goal.** Compositor detection chooses Sway only when a Sway socket exists. The systemd path unit triggers only on a non-empty scan directory. Failed tool results reach the index, and the noise filter matches the README. The SPEC §4.1 and §4.3 tests exist and pass.

**In scope**
- G5: `detect_compositor` in `claudalizer/ipc.py` no longer treats a generator as a true value. The Sway fallback requires a real `sway-ipc.*.sock`.
- G6: `systemd/claudalizer.path` sets `DirectoryNotEmpty=/tmp/claude-1000` in its `[Path]` section.
- G7: failed tool results are kept in `tool_errors`. Successful `git diff`, `git status`, `git log`, and Edit/Write results are filtered. Exit code 0 is not a failure. README wording matches the code.
- G9: all SPEC §4.1 tests (`test_slug_decoding`, `test_filter_oversized_scratchpad`, `test_jsonl_corrupt_recovery`, `test_git_state_filtering`) and all SPEC §4.3 tests (`test_sway_dispatch_when_swaysock_present`, `test_hyprland_dispatch`, `test_headless_environment_no_crash`) exist and pass.

**Out of scope**
- G4 (Waybar): needs the user's live G3 timing check.
- G11 (dead code and duplicate setup).
- G10 and G13 (deferred), G12 (pruned).
- SPEC §4.2 (`test_distiller.py`). G9 covers §4.1 and §4.3 only.
- `make systemd-install` and `make systemd-uninstall`. AGENTS.md makes these ask-first. Verification uses `make systemd-dry-run` only.
- Running `claudalizer watch` against live `/tmp/claude-1000`.
- Pushes, pull requests, or any remote action.

**Verbatim constraints (from GOALS.md and AGENTS.md)**
- G5: "Compositor detection picks Sway when Sway is running, and the glob check works (`ipc.py:42-58`)."
- G6: "systemd units are correct on install: `DirectoryNotEmpty=` is set on `claudalizer.path`."
- G7: "Failed tool results are kept in the index, and the noise filter matches the README."
- G9: "The four spec tests (SPEC.md §4.1) exist and pass for G1 and G2."
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." "Use `make systemd-dry-run` before installing unit changes."
- AGENTS.md: "Add runtime dependencies (the project is stdlib-only)" is never allowed.
- AGENTS.md: never modify `/tmp/claude-1000` or `~/.claude-mined-memories/` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | New orchestration 2. EXECUTION_PLAN_1 stays the G1 record and gains wave 3 (T1.3.1) | Keeps the approved G1 plan as a record; the new goals start from STATE_1 | User |
| D2 | 2026-11-12 | G1 closes by implementing SPEC §4.1's `test_filter_oversized_scratchpad`, not by renaming the SPEC. This reverses the earlier recommendation | G9 requires the four §4.1 tests to exist by name | User (via G9 choice) |
| D3 | 2026-11-12 | G7 keeps failed tool results and filters successful ones. README is changed to match the code. No clean test-pass filter is added | Matches the user's choice | User |
| D4 | 2026-11-12 | G9 covers every SPEC §4.1 test and every SPEC §4.3 test. The IPC tests go in a new `tests/test_ipc.py` | Matches the user's choice; SPEC names that file | User |
| D5 | 2026-11-12 | Exit code 0 is not a failure. `has_exit_err` currently matches the substring "Exit code" in "Exit code 0" | SPEC §4.1 requires that clean exit codes do not leak into tool failures | Judgment (flagged for review) |
| D6 | 2026-11-12 | The Sway fallback uses `any(...)` over the glob. Keep the other checks in `detect_compositor` unchanged | One-line fix that matches the goal wording; no behavior change for the other branches | Judgment (flagged for review) |
| D7 | 2026-11-12 | Branch `g5-g6-g7-g9` is created from `g1-durable-capture` after orchestration 1 closes | The G1 work lives on `g1-durable-capture`; it is the branch that carries the G1 closeout | Default |
| D8 | 2026-11-12 | Planning artifacts are tracked, with separate `docs(planning):` commits | Same as orchestration 1 (user choice, D5 there) | User (earlier) |
| D9 | 2026-11-12 | Worker model: cheapest capable. Escalation ladder per wave-orchestration | Default | Default |
| D10 | 2026-11-12 | Acceptance per task: targeted pytest. Orchestrator runs `make check` serially at the end of wave 3 | Per wave-orchestration | Default |
| D11 | 2026-11-12 | Systemd verification is `make systemd-dry-run` only. No install | AGENTS.md: install is ask-first | Default |

## Recon Log (facts, not questions)

- Branches: `master`, `g1-durable-capture`, and `g3-watch` all point at `5bf8361`. The G1 commits are on master.
- `claudalizer/ipc.py` (151 lines). `detect_compositor` is at lines 42-58. Line 57 is `if shutil.which("swaymsg") and (os.environ.get("SWAYSOCK") or Path(f"/run/user/{os.getuid()}").glob("sway-ipc.*.sock")):`. `glob()` returns a generator, which is always truthy. So the fallback returns "sway" whenever `swaymsg` is on PATH and `WAYLAND_DISPLAY` is set.
- `tests/` contains only `test_miner.py` (444 lines, 17 test functions). There is no `tests/test_ipc.py`. `test_ipc_waybar_status` is at `tests/test_miner.py:410`.
- `tests/test_miner.py:24` is `def test_decode_slug()`. SPEC §4.1 names `test_slug_decoding`.
- `tests/test_miner.py:37` is `test_is_git_discernable`. It asserts `git status` and `git diff` with empty output are discernable, and `cargo test` with "Exit code 101" and `python test.py` with "No such file" are not. Its existing assertions must keep passing.
- `claudalizer/miner.py:149` is `is_git_discernable(tool_name, command_or_input, error_output)`. Its git clause (`cmd.startswith("git diff"|"git status"|"git log")`) ignores `error_output`. Its Edit/Write clause requires empty output.
- `claudalizer/miner.py:244`: `has_exit_err = "Exit code" in text_out or "command not found" in text_out or "Error:" in text_out`. "Exit code 0" matches. `miner.py:256` calls `is_git_discernable` only inside `if is_err or has_exit_err:`. So the git clause runs only on error results. That is why failed `git diff` results are dropped.
- `claudalizer/miner.py:259-262` parses the exit code with `split("Exit code ")`.
- `claudalizer/miner.py:281` is `snapshot_scratchpad` (already returns `(copied, skipped)` from wave 1).
- `distiller.py:218` reads `dossier.json` with `json.load` and then uses `.get(...)` everywhere. There is no strict key lookup. This closes the open STATE_1 item "Confirm distiller.py dossier read path".
- `systemd/claudalizer.path` has `[Unit]`, `[Path]` with `PathModified=/tmp/claude-1000` and `Unit=claudalizer.service`, and `[Install]`. No `DirectoryNotEmpty`.
- `claudalizer/cli.py:137` copies `systemd/claudalizer.path` as-is at install time, so the file is the only place to change.
- Baseline (from STATE_1, 2026-11-12): `make test` 16 passed. `make lint` shows 12 pre-existing ruff findings (11 F401 and 1 F541, after G1 wave 1 removed two). The baseline is re-recorded in STATE_2 after orchestration 1 closes.
- `README.md:12-13` describes the filter: it "Ignores code modifications, checked-in commits, file diffs, and standard clean test passes", and "Preserves ... tool failures, command exit codes".
- `docs/` does not exist. No ADRs apply, so no decisions need superseding.
- `ruff` is at `~/.local/bin/ruff`.

## Hazard Notes

- H1: Do not change `snapshot_scratchpad` in G5 or G7 tasks. Orchestration 1 owns it.
- H2: `tests/test_miner.py` is edited in wave 2 (T2.2.1) and wave 3 (T2.3.1). Keep them in separate waves.
- H3: Do not run `make systemd-install` or `make systemd-uninstall`. Dry-run only.
- H4: `detect_compositor` has three branches. Only the fallback's glob check changes. Do not reorder the checks.
- H5: The existing `test_is_git_discernable` asserts behavior for empty output. Keep those assertions true.
- H6: `make lint` prints "ruff not found" after its output even though ruff runs. Read the findings above that line.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T2.1.1 | claudalizer | `claudalizer/ipc.py`; creates `tests/test_ipc.py` | — | Yes, disjoint from T2.1.2 |
| 1 | T2.1.2 | claudalizer | `systemd/claudalizer.path` | — | Yes, disjoint from T2.1.1 |
| 2 | T2.2.1 | claudalizer | `claudalizer/miner.py` (parse_transcript_events, is_git_discernable), `tests/test_miner.py`, `README.md` | Orchestration 1 closed | No (waves 2 and 3 share tests/test_miner.py) |
| 3 | T2.3.1 | claudalizer | `tests/test_miner.py` (rename test_decode_slug, add test_jsonl_corrupt_recovery) | T2.2.1 | No (same file as T2.2.1) |

Wave 1 tasks are disjoint: T2.1.1 owns `ipc.py` and the new IPC test file, and T2.1.2 owns the systemd path unit. Wave 2 depends on orchestration 1 being closed. Wave 3 is sequenced after wave 2 because both edit `tests/test_miner.py`.

Before wave 1: create branch `g5-g6-g7-g9` from `g1-durable-capture` (after orchestration 1 closes) and record the baseline in STATE_2.md. Run `make test` and `make lint` and record both.

## Task Specs

### T2.1.1 — Sway detection requires a socket; SPEC §4.3 IPC tests

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/ipc.py`
  - Can create: `tests/test_ipc.py`
- **Depends on:** none
- **Spec**
  1. In `detect_compositor` (`ipc.py:42-58`), change the fallback at line 57 so the glob is wrapped in `any(...)`. Sway is returned only when a `sway-ipc.*.sock` exists under `/run/user/<uid>`. Keep the other branches as they are.
  2. Create `tests/test_ipc.py`. Add these tests, named as in SPEC §4.3:
     - `test_sway_dispatch_when_swaysock_present`: set `SWAYSOCK` and `WAYLAND_DISPLAY`. Mock `shutil.which` and `subprocess.run`. Verify `subprocess.run` receives the swaymsg arguments that the dispatch function builds. Read the dispatch function in `ipc.py` (lines 60-151) to get the expected arguments.
     - `test_hyprland_dispatch`: set `HYPRLAND_INSTANCE_SIGNATURE` and `WAYLAND_DISPLAY`. Mock `shutil.which` and `subprocess.run`. Verify the hyprctl dispatch invocation.
     - `test_headless_environment_no_crash`: unset `WAYLAND_DISPLAY`, `SWAYSOCK`, `HYPRLAND_INSTANCE_SIGNATURE`. Call every public function in `ipc.py`. Assert no exception.
     - `test_sway_glob_fallback_requires_socket`: unset `SWAYSOCK`, set `WAYLAND_DISPLAY`, mock `shutil.which` to return a path for `swaymsg`. Point the glob at a temp directory with no socket. Assert `detect_compositor()` is not `"sway"`. To point the glob at a temp dir, monkeypatch `claudalizer.ipc.Path` with a wrapper, or patch `os.getuid` and create the directory tree under `tmp_path`. Pick the simpler one and record it in Notes.
  3. Add the second case: create a `sway-ipc.0.sock` file in the same temp directory. Assert `detect_compositor()` returns `"sway"`.
- **Anchors:** `claudalizer/ipc.py`: `def detect_compositor` (line 42), the fallback line containing `glob("sway-ipc.*.sock")` (line 57). `tests/test_miner.py`: `def test_ipc_waybar_status` (line 410) for the test shape, and the `from claudalizer.ipc import` line (line 20).
- **Reference implementation:** `test_ipc_waybar_status` in `tests/test_miner.py`.
- **Constraints (do not touch)**
  - Do not change `send_notification`, `emit_waybar_signal`, or the other non-detection functions.
  - Do not change `tests/test_miner.py`.
  - Do not change the order of checks in `detect_compositor`.
- **Acceptance (mechanical)**
  - `pytest tests/test_ipc.py -q` exits 0 with 5 passed.
  - `pytest tests/test_miner.py -q -k ipc` exits 0.
- **Commit:** `fix(ipc): choose Sway only when a Sway socket exists` (one commit containing the fix and `tests/test_ipc.py`).

### T2.1.2 — Path unit triggers only on a non-empty scan directory

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `systemd/claudalizer.path`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. Add `DirectoryNotEmpty=/tmp/claude-1000` to the `[Path]` section of `systemd/claudalizer.path`, before `Unit=`.
  2. Do not change `[Unit]`, `[Install]`, `PathModified=`, or `Unit=`.
- **Anchors:** `systemd/claudalizer.path`: `[Path]` section and `PathModified=`. `claudalizer/cli.py:137` shows the file is copied as-is at install time.
- **Reference implementation:** none. The file is 10 lines.
- **Constraints (do not touch)**
  - Do not run `make systemd-install` or `make systemd-uninstall`. Use `make systemd-dry-run` only.
  - Do not edit the watch service or service templates.
- **Acceptance (mechanical)**
  - `make systemd-dry-run 2>&1 | grep -c "DirectoryNotEmpty=/tmp/claude-1000"` prints `1` or more.
  - `make systemd-dry-run` exits 0.
- **Commit:** `fix(systemd): trigger the path unit only on a non-empty scan directory`.

### T2.2.1 — Failed tool results are kept; successful git and edit results are filtered; exit code 0 is not a failure

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/miner.py`, `tests/test_miner.py`, `README.md`
  - Can create: none
- **Depends on:** orchestration 1 closed (T1.3.1 done)
- **Spec**
  1. In `parse_transcript_events` (`miner.py:244`), a result is a failure only if `is_err` is true, or the output contains `command not found`, or `Error:`, or a non-zero `Exit code N`. Exit code 0 is not a failure. Replace the substring check `"Exit code" in text_out` with a check for a non-zero exit code. Keep the existing exit-code parsing at `miner.py:259-262` unchanged.
  2. In `is_git_discernable` (`miner.py:149`), the git clause and the Edit/Write clause return True only when `error_output` is empty. A failed `git diff`, `git status`, or `git log` is not discernable, so it is kept. Keep the existing assertions in `test_is_git_discernable` (`tests/test_miner.py:37-45`) true.
  3. Add `test_git_state_filtering` to `tests/test_miner.py`. The name is fixed by SPEC §4.1. It must check that:
     - a transcript with `git diff` returning "Exit code 1" is kept in `tool_errors`;
     - a transcript with a result containing only "Exit code 0" is not in `tool_errors`;
     - a successful `git status` with empty output is not in `tool_errors`.
     Build the transcript the way `test_transcript_parsing` (`tests/test_miner.py:48`) does.
  4. In `README.md` lines 12-13, reword the noise-filter sentence so it lists only what the code filters: successful git inspection (`git diff`, `git status`, `git log`) and successful Edit/Write results. Do not claim that clean test passes are filtered. Keep the "preserves behavioral signals" line, and state that failed tool results and non-zero exit codes are kept.
- **Anchors:** `claudalizer/miner.py`: `def is_git_discernable` (line 149), the line starting `has_exit_err =` (line 244), `if not is_git_discernable(` (line 256). `tests/test_miner.py`: `def test_is_git_discernable` (line 37), `def test_transcript_parsing` (line 48). `README.md` lines 12-13.
- **Reference implementation:** `test_transcript_parsing` for the transcript fixture.
- **Constraints (do not touch)**
  - Do not change `snapshot_scratchpad`, `_mine_session`, or the dossier write path.
  - Do not add a clean test-pass filter. Do not add new dependencies.
  - Do not edit `planning/`.
- **Acceptance (mechanical)**
  - `pytest tests/test_miner.py -q -k "git or transcript"` exits 0.
  - `pytest tests/test_miner.py -q` exits 0.
- **Commits:** two commits, each a logical unit.
  - `fix(miner): keep failed git commands and ignore exit code 0` (miner.py, tests/test_miner.py)
  - `docs(readme): describe the actual noise filter` (README.md)

### T2.3.1 — SPEC §4.1 slug and corrupt-transcript tests

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `tests/test_miner.py`
  - Can edit (only if the test in step 2 fails because the parser raises): `claudalizer/miner.py`, inside `parse_transcript_events` only
  - Can create: none
- **Depends on:** T2.2.1 (same file; wave 3)
- **Spec**
  1. Rename `test_decode_slug` (line 24) to `test_slug_decoding`. Add cases for multiple dashes, a nested path, and a trailing dash, as SPEC §4.1 describes (e.g., `-home-user-work-src-my-pkg`).
  2. Add `test_jsonl_corrupt_recovery`. Write a transcript containing one valid user line, a half-written JSON line, a truncated JSON line, and a line with non-UTF-8 bytes (`b"\xff\xfe"`), followed by a valid user line. Call `parse_transcript_events` on it. Assert no exception is raised and both valid user prompts are returned.
  3. If step 2 raises, STOP and report the exception. You may change `parse_transcript_events` only to catch decode and JSON errors per line. Record the change in the report.
- **Anchors:** `tests/test_miner.py`: `def test_decode_slug` (line 24), `def test_transcript_parsing` (line 48) for the transcript fixture. `claudalizer/miner.py`: `def parse_transcript_events` (around line 226).
- **Reference implementation:** `test_transcript_parsing`.
- **Constraints (do not touch)**
  - Do not change `is_git_discernable` or the exit-code logic (done in T2.2.1).
  - Do not change the decode function `decode_slug` beyond what the test requires.
- **Acceptance (mechanical)**
  - `pytest tests/test_miner.py -q -k "slug or corrupt"` exits 0.
  - `pytest tests/test_miner.py -q` exits 0.
- **Commit:** `test(miner): add slug decoding and corrupt-transcript spec tests`. If step 3 changed `miner.py`, use a separate `fix(miner): tolerate undecodable transcript lines` commit first.

## Verification at end of wave 3 (orchestrator, serial)

1. `make check` exits 0. Read lint output. No findings beyond the baseline recorded in STATE_2.md.
2. `make systemd-dry-run` shows `DirectoryNotEmpty=/tmp/claude-1000` in the rendered path unit.
3. `pytest tests/test_ipc.py tests/test_miner.py -q` shows every SPEC §4.1 test (except the §4.2 distiller tests, which are out of scope) and every §4.3 test passing.
4. `git log --oneline g1-durable-capture..g5-g6-g7-g9` shows one commit per task, plus `docs(planning)` commits, with no mixed commits.
5. Update GOALS.md: close G5, G6, G7, G9. Update STATE_2.md wave board.
