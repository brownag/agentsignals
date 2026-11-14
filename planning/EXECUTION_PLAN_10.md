# Execution Plan 10: Waybar history and quieter notifications (`planning/EXECUTION_PLAN_10.md`)

Orchestration: 10
Source: user request: “I want to make the waybar more useful and the notifications more useful and perhaps less frequent/intrusive”; Magic Wand goal G23.
Status: Approved by user (2026-11-14). Implementation not started.
Base branch: `main`. Planning tracked (user decision, 2026-11-14).
Baseline: `make test` — 76 passed.

## Goal & Scope

**Goal (user's terms).** Make Waybar more useful and notifications more useful and less frequent/intrusive. Waybar retains the latest scan's mined/active counts, timestamp, and cumulative history; notifications are opt-in, concise, and emitted once per scan that mined sessions.

**Exit criteria.**
- Waybar status represents the latest scan, reports mined and active session counts, scan time, cumulative scan and mined-session totals, and a bounded recent scan history.
- History retention is configurable with `--history-limit` on `scan` and `watch`, default 50; 0 retains totals/latest status but no individual history records.
- Persistent state is stored as JSON under the configured memories root, written atomically, and remains available after process restart.
- Watch notifications default off. When enabled, each scan that mines one or more sessions sends one concise desktop notification; scans with no mined sessions send none.
- Compositor hooks refresh Waybar but do not create an additional desktop popup.
- `make test` passes; README and SPEC describe behavior. No live scan, watch, systemd install, or user-data mutation is performed.

**In scope**
- `claudalizer/ipc.py` or a small new state module: persistent scan-history and cumulative-counter update/read behavior, Waybar payload.
- `claudalizer/cli.py`: record scan summaries, aggregate notification behavior, notification opt-in and history-limit flags on scan/watch.
- `tests/test_ipc.py`, `tests/test_cli.py`, and focused persistence tests if a new module is added.
- `README.md`, `planning/SPEC.md`, `systemd/claudalizer-watch.service`, and `Makefile` where needed to align documented/default watch behavior.

**Out of scope**
- Installing units, changing the user's Waybar config/style, or live testing against `/tmp/claude-1000`.
- Changing scan/miner active-session detection, debounce behavior, or memory distillation.
- Adding runtime dependencies; the project remains stdlib-only.
- Pushes or other remote actions.

**Verbatim constraints**
- User: “I want to make the waybar more useful and the notifications more useful and perhaps less frequent/intrusive”
- User preference: “all, want to know how many sessions, how many active, last scan, cumulative history”
- User preference: “user configurable history length”
- User chose CLI configuration: `--history-limit`, default 50, and 0 disables individual records while retaining totals.
- User chose watch notifications “Off; one per scan”: watch notifications are opt-in, with a concise aggregate per scan that mines sessions.
- AGENTS.md: runtime dependencies remain stdlib-only; run `make test` after changing code/tests; ask before systemd install/uninstall or long-running live watch; never directly modify `/tmp/claude-1000` or `~/.claude-mined-memories/`.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-14 | Track planning files in Git | Existing planning history is tracked | User |
| D2 | 2026-11-14 | Persist recent history as JSON under memories root; retain latest 50 by default | User wants cumulative history across scans/restarts | User |
| D3 | 2026-11-14 | Expose `--history-limit` on scan/watch, default 50; 0 disables individual records, not totals | User-configurable retention without introducing config-file format | User |
| D4 | 2026-11-14 | Latest scan stores mined count and active count (`skipped.active`); cumulative counters are total scans and total sessions mined | User requested these metrics | User |
| D5 | 2026-11-14 | Watch notifications default off; when enabled, one aggregate desktop notification per scan with mined sessions | Reduce interruption while retaining an opt-in alert | User |
| D6 | 2026-11-14 | Compositor hook only updates status/refreshes Waybar; no Hyprland popup | Avoid duplicate/intrusive popup | User goal / proposed design |

## Recon Log

- Repo is on `main`; `planning/GOALS.md` has a pre-existing user-session modification and must be preserved. No other dirty/untracked files observed.
- `make test`: 76 passed on Python 3.12.3. `tests/conftest.py` redirects default Waybar status and suppresses real signals.
- `claudalizer/cli.py` (307 lines): `_write_mined_status` currently writes extracted then idle, losing useful status; scan and watch call `notify_extraction` per dossier. Watch parser uses `store_true, default=True`, so notification cannot be disabled.
- `claudalizer/ipc.py` (177 lines): status JSON currently has text/alt/tooltip/class/count; `dispatch_wm_hook` invokes `hyprctl notify` for Hyprland, causing popup behavior.
- `tests/test_cli.py` (59 lines) and `tests/test_ipc.py` (122 lines) provide focused patterns. `tests/conftest.py` ensures no real Waybar side effects.
- `systemd/claudalizer-watch.service` explicitly starts `watch --notify`; `Makefile` watch target also opts in. Both must stop forcing notification on to honor quiet defaults.
- `planning/GOALS.md` was updated for G23 in this session; do not overwrite unrelated history or state files.
- No `docs/decisions/` directory or ADR constraints found. Planning conventions from `EXECUTION_PLAN_9.md`; no `PROMPT_TEMPLATE_9.md` exists.

## Hazard Notes

- H1: Persistent state must be tested only under `tmp_path`; never read/write live memories or `/tmp/claude-1000`.
- H2: Atomic state writes and malformed/missing-state recovery should preserve mining success (fail-safe, as with IPC).
- H3: `--history-limit 0` must still update cumulative counters and current status.
- H4: Don't generate a desktop notification through `dispatch_wm_hook`; notify-send is the single notification channel.
- H5: `make test` is the required full-suite gate. Do not run `make watch`, `claudalizer watch/scan`, or systemd state-changing commands.

## Wave Table

| Wave | Task | Files (must edit) | Depends on |
| --- | --- | --- | --- |
| 1 | T10.1.1 Persistent scan state and informative Waybar payload | `claudalizer/ipc.py` (or new state module), `tests/test_ipc.py` (and focused state tests if needed) | — |
| 2 | T10.2.1 CLI aggregation, notification defaults, history-limit integration | `claudalizer/cli.py`, `tests/test_cli.py`, `systemd/claudalizer-watch.service`, `Makefile` | T10.1.1 |
| 3 | T10.3.1 User/spec documentation | `README.md`, `planning/SPEC.md` | T10.2.1 |

## Task Specs

### T10.1.1 — Persistent scan state and informative Waybar payload

- **Files in scope:** `claudalizer/ipc.py` (or add one narrowly scoped module such as `claudalizer/status.py`), `tests/test_ipc.py` (or matching focused test file). Temp files only under `tmp_path`.
- **Depends on:** none.
- **Spec:** Implement JSON-backed persistent scan history and totals under the configured memories root. Record scan timestamp, mined count, active count, and a useful concise project summary if available. Maintain cumulative scan and session-mined totals. Retain only the most recent `history_limit` records; 0 retains no individual records. Writes are atomic. Missing/corrupt prior state recovers safely. Emit a Waybar-compatible JSON payload whose text/tooltip expose latest scan, mined/active counts, cumulative totals, and recent history without making the status file itself the persistent store. Keep the default Waybar status path override testable. Change compositor dispatch so it refreshes status/Waybar only; it must not invoke Hyprland's popup notification command.
- **Anchors:** `emit_waybar_signal`, `dispatch_wm_hook`, `DEFAULT_STATUS_FILE`, atomic-write pattern in `ipc.py`; Hyprland dispatch test and tests using `tmp_path` in `tests/test_ipc.py`.
- **Constraints:** stdlib only; do not touch live user data; do not alter miner semantics or signal number.
- **Acceptance:** focused state/IPC tests cover first scan, subsequent cumulative increments, active count, retention limits including 0, restart/reload, corrupt-state recovery, atomic output, status payload, and absence of Hyprland popup invocation; `python -m pytest tests/test_ipc.py -q` (plus new test module if added) passes.

### T10.2.1 — CLI aggregation and quiet notification defaults

- **Files in scope:** `claudalizer/cli.py`, `tests/test_cli.py`, `systemd/claudalizer-watch.service`, `Makefile`.
- **Depends on:** T10.1.1.
- **Spec:** Pass configured memories-root status state, `len(dossiers)`, and `len(miner.skipped.get("active", []))` into the state/status API for every completed scan, including no-new-session scans. Do not immediately replace the latest result with idle. Replace per-dossier desktop notifications with one concise notification per mining batch only when opted in and dossiers are nonempty. Add explicit `--notify` opt-in for watch (default false) and `--history-limit` to scan/watch (default 50; reject negative values; 0 disables individual history). Remove forced `--notify` from the systemd unit and Makefile watch target. Preserve existing scan behavior unless explicitly changed by these decisions.
- **Anchors:** `_write_mined_status`, `handle_scan`, `handle_watch`, parser definitions in `cli.py`; `notify_extraction` call sites; corresponding CLI test helpers.
- **Constraints:** never invoke live scan/watch; don't modify systemd user state; do not add runtime dependencies. Files owned by T10.1.1 remain unchanged in this wave.
- **Acceptance:** CLI tests cover no dossiers, active/multiple mined dossiers, one notification per batch, notifications off by default and opt-in, history-limit forwarding/default/validation, and persistent latest status; `python -m pytest tests/test_cli.py -q` passes.

### T10.3.1 — README and SPEC

- **Files in scope:** `README.md` (Waybar and CLI/watch usage), `planning/SPEC.md` (IPC/status/notification requirements only).
- **Depends on:** T10.2.1.
- **Spec:** Document the status metrics, persistent history location/behavior, default and configurable history limit (including 0), watch notifications being opt-in and aggregated, and that compositor hooks refresh Waybar without a popup. Keep examples aligned with the actual parser and installed watch unit. Do not rewrite unrelated memory/miner spec sections.
- **Anchors:** README “Continuous Watch Daemon” and “Waybar Configuration Example”; SPEC §1 architecture and IPC-related sections.
- **Constraints:** documentation only; no new behavior beyond accepted decisions.
- **Acceptance:** documented `--history-limit` and opt-in notification usage agree with `build_parser`; `make test` passes.

## Verification (orchestrator, serial)

1. After each wave, inspect diff for scope and atomic/fail-safe behavior.
2. At completion run `make test`; compare against baseline 76 passed.
3. Do not run against real `/tmp/claude-1000`, real memories, Waybar, or systemd. User may install/test separately after approval.

## Escalation

1. Stop if implementation requires touching live user data or changing miner/settle semantics.
2. If a test fails twice for the same reason, report rather than thrash.
3. Any requirement for additional state migration or user-config changes beyond this plan requires a revised plan and approval.
