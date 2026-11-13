# Execution Plan 3: G4 Waybar state and refresh (`planning/EXECUTION_PLAN_3.md`)

Orchestration: 3
Source goal: `planning/GOALS.md` [G4] (circled)
Status: Approved by user (2026-11-12). Executed: waves 1-2 done (commits `a2eefa3`, `5ab4552`, `b651913`). Live Waybar check pending.
Starts after: orchestration 2 closed (G5, G6, G7, G9 done on `g5-g6-g7-g9`).
Base branch: `g5-g6-g7-g9` (HEAD `6756b5c` at plan time). Work stays on this branch unless the user says otherwise.

## Goal & Scope

**Goal (user's terms).** Waybar shows the current capture state and refreshes after each scan.

**Exit criteria (from GOALS.md G4).** After a scan writes a dossier, the Waybar module re-reads the status within a few seconds, verified by a test that checks the refresh call is made. `make check` passes.

**In scope**
- After a status write, send a Waybar refresh signal (`pkill -RTMIN+8 waybar`) from `emit_waybar_signal`. Polling every 3 s stays as the fallback.
- After each watch cycle that mined sessions, return the status to `idle`, keeping the last mined session and its time in the tooltip. A stuck `extracted` status is a bug.
- A plain `claudalizer scan` (without `--notify`) always writes the status. `--notify` still controls desktop notifications only.
- README Waybar snippet: add `"signal": 8` and a note about the refresh.

**Out of scope**
- Editing `~/.config/waybar/config.jsonc`. The user adds the module (decision recorded below).
- Live Waybar refresh timing check. It is user-run, with the G3 live check. Acceptance here is the mocked test only.
- G3 live timing check on `/tmp/claude-1000` (user-run; AGENTS.md ask-first).
- G11 (duplicate setup and dead fields in `cli.py`). Note that T3.2.1 edits `cli.py` near the same code; do not refactor the setup duplication.
- `make systemd-install` and `make systemd-uninstall` (ask-first per AGENTS.md).
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G4: "Waybar shows current capture state and refreshes after each scan."
- GOALS.md G4 exit: "after a scan writes a dossier, the Waybar module re-reads the status within a few seconds, verified by a test that checks the refresh call is made. `make check` passes."
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." "Add runtime dependencies" is never allowed (stdlib only).
- AGENTS.md: never modify `/tmp/claude-1000` or `~/.claude-mined-memories/` directly. Tests use `tmp_path`.
- AGENTS.md: "Changing the settle window, size cap, or lock timeout" is ask-first. This plan changes none of them.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | After a mined cycle, the status returns to `idle`. The last mined session and its time go in the tooltip | Current status sticks at `extracted` after one mine (STATE recon: `/tmp/claudalizer_status.json` read as `extracted` with no watch running) | User (grill Q1) |
| D2 | 2026-11-12 | Refresh is a signal (`pkill -RTMIN+8 waybar`) on top of the existing 3 s polling | Polling alone is correct but up to 3 s late; the signal makes refresh immediate | User (grill Q2) |
| D3 | 2026-11-12 | The signal is sent from `emit_waybar_signal` (`claudalizer/ipc.py:60`), after the status file is written | It is the single status write point; `dispatch_wm_hook` already routes through it, so every write refreshes | User (grill Q3) |
| D4 | 2026-11-12 | A plain `scan` always writes the status. `--notify` controls notifications only | Otherwise a hand-run scan leaves the module stale | User (grill Q4) |
| D5 | 2026-11-12 | The user adds the module to `~/.config/waybar/config.jsonc`. The plan updates only the README snippet | The config is outside this repo; no module exists in it yet | User (grill Q5) |
| D6 | 2026-11-12 | Signal number is 8 (`RTMIN+8`) | Judgment: unused in the user's setup as far as known. Easy to change in one constant | Judgment (flagged for review) |
| D7 | 2026-11-12 | Planning files are tracked, with separate `docs(planning)` commits | Same as orchestrations 1 and 2 | User (grill Q6) |
| D8 | 2026-11-12 | Waves are serial where files overlap (`cli.py` is touched only in wave 2). Workers run inline by the orchestrator, one task at a time | Two small tasks; no file collisions | Default |
| D9 | 2026-11-12 | Acceptance is mocked (subprocess monkeypatched) plus `make check`. Live Waybar refresh is a user-run check | No Waybar in the test environment; matches G3's user-run check | Default |
| D10 | 2026-11-12 | Amendment: `tests/conftest.py` (autouse stub of `ipc._signal_waybar`) is added to T3.1.1 | Without it, `tests/test_miner.py:515` and the dispatch tests would send real `pkill -RTMIN+8 waybar` on every test run (H6). Spec did not list it; re-scoped rather than widened ad hoc | Judgment (flagged for review) |
| D11 | 2026-11-12 | Amendment: T3.2.1 writes `extracted` then `idle` in scan and watch | Only `notify_extraction` wrote `extracted`, and only under `--notify`; nothing wrote `idle` after, so the status stuck (D1). Final state is always `idle` | Judgment (flagged for review) |
| R1 | 2026-11-12 | Risk, unverified: `pkill -RTMIN+8 waybar` may terminate Waybar if it has no handler for signal 8 | Waybar binary references `__libc_current_sigrtmin`; not confirmed. Do not run `make install-user` until checked | Closed (orchestration 4 probe: RTMIN+8 survives on 0.9.24) |
| D12 | 2026-11-12 | Orchestration 4 probe (headless Sway 1.9, Waybar 0.9.24 copy): `kill -RTMIN+8` does not terminate Waybar with no `signal` config; a `"signal": 8` module refreshes on it. G4 keeps `pkill -RTMIN+8 waybar`; no code change | Closes R1 and G14. Evidence in `planning/STATE_4.md` `## T4.1.1` | Probe |

## Recon Log (facts)

- `claudalizer/ipc.py` (151 lines). `emit_waybar_signal` at lines 60-87 writes `status_file` (default `/tmp/claudalizer_status.json`) through a `.tmp` file and `replace()`. It swallows `OSError`. It is called only from `dispatch_wm_hook` (line 100).
- `dispatch_wm_hook` (lines 90-137) calls `emit_waybar_signal` first, then routes to swaymsg or hyprctl.
- `notify_extraction` (lines 140-151) is called only from `cli.py` when `--notify` is set (`cli.py:54`, `cli.py:110`).
- `claudalizer/cli.py` (257 lines). `handle_scan` starts at line 36 and calls `notify_extraction` only `if args.notify` (line 54). It never writes the status without `--notify`. `handle_watch` starts near line 87: it writes `dispatch_wm_hook("watching")` at line 92, loops with `time.sleep(args.interval)` at line 121, and writes `idle` only on `KeyboardInterrupt` (line 124).
- `README.md:86-97` is the Waybar snippet: `"exec": "cat /tmp/claudalizer_status.json ..."`, `"interval": 3`. No `signal` key.
- `~/.config/waybar/config.jsonc` (user) contains no claudalizer module. `pgrep waybar` shows it running. No `signal` settings are set for any module (checked by grep of `custom/` names only).
- Current status file (observed): `{"text": "🧠", "alt": "extracted", "tooltip": "Claudalizer: extracted\nMined -home-andrew-AI-claudalizer (3 errors)", "class": "extracted", "count": 0}`. Stale: no watch process is running.
- `tests/test_ipc.py` (orchestration 2) has 5 tests and monkeypatches `ipc.emit_waybar_signal` and `ipc.subprocess.run`. Reuse that fixture shape.
- `tests/test_miner.py:515` calls `emit_waybar_signal(status_file=..., status="extracted", ...)` directly. Do not change that test's assertions.
- Baseline (branch `g5-g6-g7-g9`, recorded in STATE_3.md): `make test` 22 passed; `make lint` 12 findings, all pre-existing.

## Hazard Notes

- H1: `emit_waybar_signal` runs on every status write, including the watch loop's per-cycle writes. The signal call must be quick and never raise: use `timeout=2`, `check=False`, and swallow `OSError`/`SubprocessError`.
- H2: `pkill` is not guaranteed to exist. If `shutil.which("pkill")` is None, skip the signal silently.
- H3: `pkill -RTMIN+8 waybar` only refreshes if the module has `"signal": 8`. Without it the signal is a no-op. The README change in T3.1.2 is required for the feature to work.
- H4: The tests must never write to the real `/tmp/claudalizer_status.json`. Pass `status_file=tmp_path/...` in every new test. The default path is a hazard.
- H5: `cli.py` is edited only in T3.2.1 (wave 2). Do not touch it in wave 1.
- H6: Do not call `make systemd-install`. Do not signal the real Waybar from tests (mock `subprocess.run`).

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T3.1.1 | claudalizer | `claudalizer/ipc.py`, `tests/test_ipc.py` | — | Yes, disjoint from T3.1.2 |
| 1 | T3.1.2 | claudalizer | `README.md` | — | Yes, disjoint from T3.1.1 |
| 2 | T3.2.1 | claudalizer | `claudalizer/cli.py`; creates `tests/test_cli.py` | T3.1.1 | No (serial, after wave 1) |

Wave 2 starts only after wave 1 is all `done`.

## Task Specs

### T3.1.1 — Status write sends a Waybar refresh signal

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/ipc.py`, `tests/test_ipc.py`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In `claudalizer/ipc.py`, add a module constant `WAYBAR_SIGNAL = 8`.
  2. In `emit_waybar_signal` (line 60), after the status file `replace()` succeeds, call a new helper `_signal_waybar()`. Do not call it if the write failed.
  3. `_signal_waybar()`: if `shutil.which("pkill")` is None, return. Otherwise `subprocess.run(["pkill", f"-RTMIN+{WAYBAR_SIGNAL}", "waybar"], stdout=DEVNULL, stderr=DEVNULL, timeout=2, check=False)`. Catch `(subprocess.SubprocessError, OSError)` and return. Never raise.
  4. Add tests to `tests/test_ipc.py`, each using `tmp_path` for `status_file`:
     - `test_waybar_refresh_signal_sent`: `shutil.which` returns a path for `pkill`; `subprocess.run` is monkeypatched to record args. After `emit_waybar_signal(status_file=tmp_path/"s.json", ...)`, assert the recorded args are `["pkill", "-RTMIN+8", "waybar"]`.
     - `test_waybar_refresh_skipped_without_pkill`: `shutil.which` returns None for `pkill`. Assert `subprocess.run` is not called and the status file still exists.
     - `test_waybar_refresh_failure_is_silent`: `subprocess.run` raises `subprocess.TimeoutExpired`. Assert `emit_waybar_signal` returns normally and the status file exists.
- **Anchors (grep, do not read whole file)**
  - `claudalizer/ipc.py`: `def emit_waybar_signal`, `temp_file.replace(status_file)`, `def dispatch_wm_hook`.
  - `tests/test_ipc.py`: `def _fake_which`, `def clean_env`, `def test_sway_dispatch_when_swaysock_present`.
- **Reference implementation:** `notify_extraction`'s `send_notification` (ipc.py lines 11-37): `shutil.which` check, `subprocess.run` with `DEVNULL` and `timeout`, `except (subprocess.SubprocessError, OSError)`. Copy that shape.
- **Constraints (do not touch)**
  - Do not change `dispatch_wm_hook`, `detect_compositor`, `notify_extraction`, or `send_notification`.
  - Do not change the status JSON payload or the file path.
  - Do not edit `cli.py`, `README.md`, or `tests/test_miner.py`.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_ipc.py -q` exits 0 with 8 passed (5 existing + 3 new).
  - `python -m pytest tests/test_miner.py -q -k ipc` exits 0.
- **Commit:** `feat(ipc): signal Waybar to refresh after each status write`

### T3.1.2 — README Waybar snippet refreshes on signal

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `README.md`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In the Waybar snippet (`README.md` lines 86-97), add `"signal": 8` to the `custom/claudalizer` module object, after `"interval": 3`.
  2. Under the snippet, add two short sentences: the module refreshes immediately after each status write (`pkill -RTMIN+8 waybar`), and polling every `interval` seconds is the fallback.
  3. Do not change the rest of the README.
- **Anchors:** `README.md`: `## Waybar Configuration Example`, `"custom/claudalizer": {`, `"interval": 3`.
- **Reference implementation:** the existing snippet in the same section.
- **Constraints (do not touch)**
  - Do not edit `~/.config/waybar/*` (outside the repo).
  - Do not change the CLI section or test instructions.
- **Acceptance (mechanical)**
  - `grep -c '"signal": 8' README.md` prints `1`.
  - `grep -c 'RTMIN+8' README.md` prints `1` or more.
  - `python -c "import json,re; s=open('README.md').read(); m=re.search(r'\"custom/claudalizer\": (\{.*?\n\})', s, re.S); json.loads(m.group(1))"` exits 0 (the snippet is valid JSON).
- **Commit:** `docs(readme): document Waybar signal refresh`

### T3.2.1 — Status returns to idle; plain scan writes status

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/cli.py`
  - Can create: `tests/test_cli.py`
- **Depends on:** T3.1.1 (the signal is sent from `emit_waybar_signal`, so status writes here refresh Waybar)
- **Spec**
  1. In `handle_scan` (starts line 36), write the status after mining, regardless of `--notify`. Use `emit_waybar_signal` directly, not `dispatch_wm_hook`, so the scan does not fire WM hooks unless `--notify` is set. Status: `extracted` with `mined_count=len(dossiers)` and message `Mined <slug> at HH:MM` when dossiers exist; `idle` with message `No new sessions` when none. The notify call stays under `if args.notify`.
  2. In `handle_watch` (starts near line 87), after each cycle that mined at least one session, write `extracted` as today, then write `idle` with message `Last mined <slug> at HH:MM`. Keep the existing `watching` write at start and the `idle` write on `KeyboardInterrupt`.
  3. Use `datetime.now().strftime("%H:%M")` for the time. Import `datetime` at the top of `cli.py`. Add `emit_waybar_signal` to the existing `from claudalizer.ipc import ...` line (currently `dispatch_wm_hook, notify_extraction, send_notification`).
  4. Create `tests/test_cli.py` with two tests. Monkeypatch `claudalizer.cli.emit_waybar_signal` to record calls and `claudalizer.cli.SessionMiner` to return fake dossiers (or use `tmp_path` roots with no sessions for the no-session case). Assert:
     - `test_scan_without_notify_writes_status`: with one fake dossier and `args.notify=False`, the recorded calls include `status="extracted"`, and `notify_extraction` is not called.
     - `test_scan_no_sessions_writes_idle`: with no dossiers, the recorded calls include `status="idle"`.
  5. Do not add a watch-loop test. The loop is a `while True`; cover it by reading the code and by the user-run live check.
- **Anchors (grep, do not read whole file)**
  - `claudalizer/cli.py`: `def handle_scan`, `if args.notify:`, `notify_extraction(d.slug`, `def handle_watch`, `dispatch_wm_hook("watching"`, `dispatch_wm_hook("idle"`, `time.sleep(args.interval)`, `^from claudalizer.ipc import`.
  - `tests/test_miner.py`: `def test_cli_dry_run` (for CLI test shape).
- **Reference implementation:** `handle_scan` itself, for the loop over `dossiers`. For the test shape, `tests/test_ipc.py` (orchestration 2) monkeypatch style.
- **Constraints (do not touch)**
  - Do not refactor the duplicate `SessionMiner`/`MemoryDistiller` setup (G11 is out of scope).
  - Do not change `--notify` or `--auto-distill` defaults. `store_true` with `default=True` stays as is (AGENTS.md note).
  - Do not change `build_parser`.
  - Do not touch `ipc.py`.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_cli.py -q` exits 0 with 2 passed.
  - `python -m pytest tests/ -q` exits 0 (full suite serially).
  - `make lint` reports 12 findings, all pre-existing (no new ones in `cli.py` or `tests/test_cli.py`).
- **Commit:** `feat(cli): keep Waybar status current after scan and watch cycles`

## Verification at end of wave 2 (orchestrator, serial)

1. `make check` exits 0. Read lint output: no findings beyond the 12 pre-existing ones.
2. `grep -n "signal" README.md` shows the `"signal": 8` line.
3. `git log --oneline 6756b5c..HEAD` shows one code commit per task plus `docs(planning)` commits, with no mixed commits.
4. Report to the user: the live Waybar refresh check (add the module to `~/.config/waybar/config.jsonc` per README, run `claudalizer scan`, confirm the module updates without waiting 3 s) is user-run. Do not run it for them.
5. Update GOALS.md: move G4 to Done only after the user confirms the live check. Until then, record G4 as "implemented; live refresh check pending".
