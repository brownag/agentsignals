# Execution Plan 4: G14 Waybar refresh signal is safe (`planning/EXECUTION_PLAN_4.md`)

Orchestration: 4
Source goal: `planning/GOALS.md` [G14] (circled)
Status: Draft for user approval. Not started.
Starts after: orchestration 3 executed (commits `a2eefa3`, `5ab4552`, `b651913`, `d5eb235`).
Base branch: `g5-g6-g7-g9` (HEAD `d5eb235`). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (user, 2026-11-12). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** Confirm that the Waybar refresh signal `pkill -RTMIN+8 waybar` does not terminate Waybar when no module sets `"signal": 8`, before the G4 code is installed.

**Exit criteria (from GOALS.md G14).** A probe on a renamed copy of the Waybar binary, with no `signal` config, shows the process survives `kill -RTMIN+8 <pid>`. If it doesn't, G4 switches to another mechanism (decision D2), and that change is recorded in `EXECUTION_PLAN_3.md`.

**In scope**
- A headless probe (decision D1) of the installed Waybar 0.9.24: does RTMIN+8 kill it, does a module with `"signal": 8` react to it (positive control), and what does SIGUSR2 do?
- If RTMIN+8 survives: record the result and close R1 and G14. No code change.
- If RTMIN+8 kills Waybar: switch the refresh to `pkill -USR2 waybar` (decision D2), with tests and README updated.

**Out of scope**
- Running `make install-user` or `make systemd-install`. The user decides when the G4 code goes live (AGENTS.md ask-first).
- The G4 live refresh check on the real session (user-run).
- Any change to the user's `~/.config/waybar/*` (outside the repo).
- G16, G15, G11, G17 (queued in GOALS.md).
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G14 exit: "a probe on a renamed copy of the Waybar binary, with no `signal` config, shows the process survives `kill -RTMIN+8 <pid>`. If it doesn't, G4 switches to another mechanism."
- GOALS.md G14 first action: "copy `/usr/bin/waybar` to a scratch name (e.g. `waybar-probe`, not `waybar`) ... Do not use `pkill`, which also matches the real Waybar."
- User decision (2026-11-12): "Headless compositor (Recommended)": run the probe under a headless Sway so no bar appears on the user's screen.
- User decision (2026-11-12): "Switch to SIGUSR2 (Recommended)" if the probe shows a kill.
- AGENTS.md: never modify `/tmp/claude-1000` or `~/.claude-mined-memories/` directly. Tests use `tmp_path`.
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." "Add runtime dependencies" is never allowed.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | The probe runs under a headless Sway (`WLR_BACKENDS=headless`). No bar appears on the user's screen | The user's session should not show a second bar; the probe must not touch the real Waybar | User (grill Q1) |
| D2 | 2026-11-12 | If RTMIN+8 kills Waybar, switch the refresh to `pkill -USR2 waybar` (reloads config; the module needs no `signal` key). If the probe shows SIGUSR2 also kills, stop and report | The user chose the fallback now, so the plan does not stall. The reload-on-USR2 behavior is recalled, not verified: T4.1.1 must check it | User (grill Q2). Note: the reload is heavier than a module refresh and runs on every status write |
| D3 | 2026-11-12 | Planning artifacts are tracked, with separate `docs(planning)` commits | Same as orchestrations 1-3 | User (grill Q3) |
| D4 | 2026-11-12 | The probe includes a positive control: a module with `"signal": 8` must refresh when RTMIN+8 is sent | Survival alone does not prove the signal reaches Waybar; a no-op would also survive | Judgment (flagged for review) |
| D5 | 2026-11-12 | Probe artifacts live in `/tmp/g14-probe/`, outside the repo and outside `/tmp/claude-1000` | Keeps the repo clean; AGENTS.md forbids touching `/tmp/claude-1000` | Judgment (flagged for review) |
| D6 | 2026-11-12 | Workers run inline by the orchestrator, one task at a time (same as orchestration 3) | Three small tasks; wave 2 is conditional on the probe result | Default |

## Recon Log (facts)

- Waybar installed: `/usr/bin/waybar`, version 0.9.24 (Debian package `waybar`). Doc directory has only `changelog.Debian.gz` and `copyright`. Changelog has no signal entries.
- The binary contains the strings `startSignalThread`, `pthread_sigmask failed in startSignalThread`, and `Received signal with number {}, but not handling`. So Waybar 0.9.24 runs a signal thread and logs unhandled signals.
- Web lookup (upstream Waybar source, commit `54f7991` `src/main.cpp`, and commit `418767c` "feat-rtsignal"): newer Waybar routes RTMIN+1..SIGRTMAX to each bar's `handleSignal`, and a custom module refreshes when `SIGRTMIN + signal` arrives. This does not confirm 0.9.24. Only the probe does.
- Sway 1.9 is installed (`/usr/bin/sway`, `/usr/bin/swaymsg`). `seatd` was not found in `PATH`; headless mode may not need it (T4.1.1 records this).
- `pkill` matches by substring. `pkill waybar` also matches a process named `waybar-probe`.
- `ipc.py`: `WAYBAR_SIGNAL = 8` (line 8), `_signal_waybar` (after `emit_waybar_signal`), `pkill -RTMIN+{WAYBAR_SIGNAL} waybar` (from orchestration 3 commit `a2eefa3`).
- `README.md`: the Waybar snippet has `"signal": 8,` after `"interval": 3,` and a sentence about `pkill -RTMIN+8 waybar` (commit `5ab4552`).
- `tests/test_ipc.py`: `test_waybar_refresh_signal_sent` asserts `["pkill", "-RTMIN+8", "waybar"]`. `tests/conftest.py` stubs `_signal_waybar` for all tests.
- `make test`: 29 passed at `d5eb235`. `make lint`: 12 findings, all pre-existing.
- The real Waybar config `~/.config/waybar/config.jsonc` has no claudalizer module (G4 live check not yet done).

## Hazard Notes

- H1: Never use `pkill` or `killall` in the probe. Signal the probe copy by PID only (`kill -RTMIN+8 <pid>`). Otherwise the real Waybar may be hit.
- H2: Run the probe Waybar and headless Sway with a clean environment. Do not inherit the real `WAYLAND_DISPLAY`, `SWAYSOCK`, or `HYPRLAND_INSTANCE_SIGNATURE`. The probe runs only on its own headless socket.
- H3: Kill every probe process before reporting (probe Waybar, headless sway). Verify with `pgrep -a -f 'g14-probe|wb-probe'` that none are left.
- H4: Do not write to `/tmp/claudalizer_status.json` or `/tmp/claude-1000`. The probe writes only under `/tmp/g14-probe/`.
- H5: Do not run `make install-user`, `make install`, `make systemd-install`, or `claudalizer watch`.
- H6: If headless sway fails to start (no DRM/seat, missing libs), the probe task stops and reports the error. Do not switch to the live session without a new user decision.
- H7: The positive control's exec writes to a file under `/tmp/g14-probe/`. Waybar's module `exec` must not run `pkill`.
- H8: A probe that cannot run is not a pass. Only the explicit RESULT lines decide the path.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T4.1.1 Headless probe of RTMIN+8 and SIGUSR2 | claudalizer | `planning/STATE_4.md` (report only) | — | No |
| 2 | T4.2.1 Survives path: close R1 and G14 | claudalizer | `planning/GOALS.md`, `planning/EXECUTION_PLAN_3.md` | T4.1.1 | Runs only if RESULT survives-RTMIN8=yes |
| 2 | T4.2.2 Kill path: refresh with SIGUSR2 | claudalizer | `claudalizer/ipc.py`, `tests/test_ipc.py`, `README.md` | T4.1.1 | Runs only if RESULT survives-RTMIN8=no |

Wave 2 has exactly one active task. The other is marked `skipped (probe result)` in STATE_4.md. T4.2.1 and T4.2.2 have disjoint files, so they could run in parallel, but only one ever runs.

## Task Specs

### T4.1.1 — Headless probe of RTMIN+8 and SIGUSR2

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/STATE_4.md` (append the `## T4.1.1` report only)
  - Can create: files under `/tmp/g14-probe/` only (outside the repo)
- **Depends on:** none
- **Spec**
  1. Create `/tmp/g14-probe/`. Copy `/usr/bin/waybar` to `/tmp/g14-probe/wb-probe` (name must not contain "waybar"; `wb-probe` is the chosen name).
  2. Write a headless Sway config at `/tmp/g14-probe/sway.conf` with no outputs-specific settings and a single `exec` that runs the probe Waybar (step 3). Start headless sway with a clean environment: `env -i PATH=/usr/bin:/bin HOME=$HOME XDG_RUNTIME_DIR=/tmp/g14-probe/run WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 sway -c /tmp/g14-probe/sway.conf`. Find the headless `WAYLAND_DISPLAY` name and `SWAYSOCK` it creates under `XDG_RUNTIME_DIR`. If sway fails to start, STOP (H6).
  3. Start the probe Waybar with the headless display only: `env -i PATH=... XDG_RUNTIME_DIR=... WAYLAND_DISPLAY=<headless> /tmp/g14-probe/wb-probe -c /tmp/g14-probe/config-nosignal.jsonc -s /tmp/g14-probe/style.css`. `config-nosignal.jsonc` has one bar with no modules. Record its PID with `$!`.
  4. Survival test (no module with signal): `kill -RTMIN+8 <pid>`, wait 3 s, check `kill -0 <pid>`. Record `survives-RTMIN8=yes` or `no`. If the process died, record the exit status and stop the test (do not restart the probe for this check).
  5. Positive control: start a second probe Waybar copy (`/tmp/g14-probe/wb-probe` with `config-signal.jsonc`) on the same headless display. The config has one `custom/probe` module with `"signal": 8`, `"exec": "date +%s%N >> /tmp/g14-probe/refresh.log"`, `"interval": 3600` (so only a signal refreshes it), `"return-type": ""`, and `"format": "{}"`. Clear `refresh.log`, send `kill -RTMIN+8 <pid2>`, wait 2 s, count lines in `refresh.log`. Record `refresh-with-signal8=yes` if the count went up by at least 1, otherwise `no`. Check that `pid2` is still alive.
  6. SIGUSR2 check: `kill -USR2 <pid>` on the no-module process (if it survived step 4), wait 3 s, check `kill -0 <pid>` (record `survives-USR2=yes|no`), and grep the probe's stderr/stdout log (redirect it at launch) for "reload" or "config" and record what it logs (`usr2-log=<line or none>`).
  7. Clean up (H3): kill both probe Waybar PIDs and the headless sway. Run `pgrep -a -f 'g14-probe|wb-probe'` and confirm no output.
  8. Append to `planning/STATE_4.md` under `## T4.1.1` (15 lines max) the exact RESULT lines below, plus the sway version, the headless socket name used, and any error text. Do not commit probe artifacts (they are outside the repo).
- **RESULT lines (mandatory, exact keys)**
  - `RESULT: survives-RTMIN8=yes|no`
  - `RESULT: refresh-with-signal8=yes|no|not-run`
  - `RESULT: survives-USR2=yes|no|not-run`
  - `RESULT: path=survives|kills|inconclusive`
  - `path=survives` only if survives-RTMIN8=yes AND refresh-with-signal8=yes. `path=kills` only if survives-RTMIN8=no AND survives-USR2=yes. Anything else is `inconclusive`: stop, report, do not start wave 2.
- **Anchors**
  - `claudalizer/ipc.py`: `WAYBAR_SIGNAL = 8`, `def _signal_waybar`, `pkill -RTMIN+` (for the exact command being verified).
  - `README.md`: `## Waybar Configuration Example`, `"signal": 8,`.
- **Reference implementation:** none. The probe is new. Waybar config syntax: the existing snippet in `README.md` `## Waybar Configuration Example`.
- **Constraints (do not touch)**
  - Do not edit any file in the repo except `planning/STATE_4.md`.
  - Do not run `pkill`, `killall`, `make install-user`, or any command that touches the real Waybar or real Sway.
- **Acceptance (mechanical)**
  - `planning/STATE_4.md` contains the four RESULT lines and `path=`.
  - `pgrep -a -f 'g14-probe|wb-probe'` prints nothing after cleanup.
  - `git diff --stat` before and after the task differs only by `planning/STATE_4.md` (the worker records the stat before starting). Planning files committed before wave 1 are not counted.
- **Commit:** `docs(planning): record G14 Waybar signal probe result` (planning-only; the report goes in a separate commit from the task's implementation, of which there is none)

### T4.2.1 — Survives path: close R1 and G14

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/GOALS.md`, `planning/EXECUTION_PLAN_3.md`
  - Can create: none
- **Depends on:** T4.1.1 (`path=survives`)
- **Spec**
  1. In `planning/GOALS.md`, move G14 from Circled to Done with the probe result (sway version, RTMIN+8 survived, positive control refreshed). Move G4 to the Circled Goal section, with Depends on: none. Keep its status line: live refresh check pending.
  2. In `planning/EXECUTION_PLAN_3.md`, change risk R1 status from `Open` to `Closed (orchestration 4 probe: RTMIN+8 survives on 0.9.24)`. Add a decision line D12 recording the probe result.
  3. Do not change any code or README.
- **Anchors:** `planning/GOALS.md`: `## Circled Goal (Active)`, `**[G14]**`, `Depends on: G14`. `planning/EXECUTION_PLAN_3.md`: `| R1 |`.
- **Constraints (do not touch)**
  - No code, tests, or README changes.
  - Do not run `make install-user`. The user decides when G4 goes live.
- **Acceptance (mechanical)**
  - `grep -c 'Closed' planning/EXECUTION_PLAN_3.md` prints at least `1`.
  - `grep -n 'G14' planning/GOALS.md` shows G14 only under `## Done`.
  - `make test` passes unchanged (29 passed).
- **Commit:** `docs(planning): close G14 after signal probe`

### T4.2.2 — Kill path: refresh with SIGUSR2

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/ipc.py`, `tests/test_ipc.py`, `README.md`
  - Can create: none
- **Depends on:** T4.1.1 (`path=kills`)
- **Spec**
  1. In `claudalizer/ipc.py`, remove `WAYBAR_SIGNAL = 8`. In `_signal_waybar`, change the command to `["pkill", "-USR2", "waybar"]`. Keep the `shutil.which`, `timeout=2`, `check=False`, and exception handling as they are.
  2. In `tests/test_ipc.py`, change the assertion in `test_waybar_refresh_signal_sent` to `["pkill", "-USR2", "waybar"]`. Do not change the other two tests except to fix any reference to `RTMIN`.
  3. In `README.md`, remove the `"signal": 8,` line from the snippet. Replace the two sentences under it with: after each status write, claudalizer sends `SIGUSR2` to Waybar, which reloads its config, so the module refreshes; polling every `interval` seconds is the fallback. Add one sentence: Waybar reloads on every status write, so keep the status file writes infrequent.
  4. Do not touch `tests/conftest.py`, `cli.py`, or `tests/test_cli.py`.
- **Anchors:** `claudalizer/ipc.py`: `WAYBAR_SIGNAL = 8`, `def _signal_waybar`. `tests/test_ipc.py`: `def test_waybar_refresh_signal_sent`, `RTMIN+8`. `README.md`: `"signal": 8,`, `RTMIN+8`.
- **Reference implementation:** the existing `_signal_waybar` in `claudalizer/ipc.py` (orchestration 3, commit `a2eefa3`). Change only the command and remove the constant.
- **Constraints (do not touch)**
  - Do not change `emit_waybar_signal`, `dispatch_wm_hook`, `notify_extraction`, or `send_notification`.
  - Do not change the status payload or path.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_ipc.py -q` exits 0 with 8 passed.
  - `grep -c 'RTMIN' claudalizer/ipc.py README.md tests/test_ipc.py` prints 0 for each file.
  - `grep -c 'USR2' claudalizer/ipc.py tests/test_ipc.py` prints at least 1 for each file.
  - `make test` exits 0 (29 passed).
- **Commit:** `feat(ipc): refresh Waybar with SIGUSR2 after status writes` (code), then `docs(planning):` for the STATE_4 report and R1 update (separate commit).

## Verification at end of wave 2 (orchestrator, serial)

1. `make check` exits 0 (29 passed; lint 12 pre-existing findings).
2. `pgrep -a -f 'g14-probe|wb-probe'` prints nothing. Confirm the real Waybar is still running (`pgrep -a waybar` shows the original PID, unchanged).
3. `git log --oneline d5eb235..HEAD` shows one `docs(planning)` commit for the probe result, one for the path (T4.2.1 or T4.2.2), and code commits only for T4.2.2.
4. Report to the user: the probe result, the path taken, and that G4's live check and the `make install-user` decision remain with the user.

## Escalation (from wave-orchestration)

1. Probe result `inconclusive` (e.g. headless sway fails, positive control gives no refresh): stop, report, and ask the user. Do not start T4.2.x.
2. `path=kills` but SIGUSR2 also kills: stop and report (D2 says stop).
3. Acceptance fails after one retry: re-run on a mid-tier model; never a third small-model attempt.
4. Worker needs out-of-scope edits: re-scope the spec; do not widen permissions ad hoc.
