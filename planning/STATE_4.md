# Orchestration 4 State (`planning/STATE_4.md`)

Plan: `planning/EXECUTION_PLAN_4.md` (G14 Waybar refresh signal is safe)
Status: Running. Wave 1 done. Wave 2 in progress.
Last Updated: 2026-11-12

## Pre-wave checklist

- [x] Orchestration 3 executed (`a2eefa3`, `5ab4552`, `b651913`, `d5eb235`)
- [x] Recon: Waybar 0.9.24 present; Sway 1.9 present
- [x] User approved `EXECUTION_PLAN_4.md` (user request "run plan 4", 2026-11-12)
- [x] Planning files committed before wave 1 (`c7ee0cf`, `950ff0f`)
- [x] Planning tracking: tracked (separate `docs(planning)` commits)
- [x] Record baseline: `make test` 29 passed (branch `g5-g6-g7-g9`, HEAD `950ff0f`)
- [x] Record baseline: `make lint` 12 findings, all pre-existing
- [x] Record baseline: real Waybar PID `3479493` (`/usr/bin/waybar`), real Sway PID `106996`

### Baseline records

- Tests: `make test` 29 passed.
- Lint: `make lint` 12 findings (pre-existing, not added to).
- Real session before probe: waybar `3479493`, sway `106996`.

## Wave board

| Wave | Task | Status | Code commit(s) | Notes |
| --- | --- | --- | --- | --- |
| 1 | T4.1.1 Headless probe of RTMIN+8 and SIGUSR2 | done | none (planning only) | path=survives |
| 2 | T4.2.1 Survives path: close R1 and G14 | pending | | runs: path=survives |
| 2 | T4.2.2 Kill path: refresh with SIGUSR2 | skipped (probe result) | | path=kills only |

Wave 2 starts only after wave 1 is all `done`. Exactly one wave-2 task runs; the other is marked `skipped (probe result)`.

Live check (user-run, not a gate): G4 refresh timing with the module added per README. Record the result here when the user reports it.

## Task reports

## T4.1.1

Status: done. Probe artifacts only under `/tmp/g14-probe/`; no repo files changed.
Environment: Sway 1.9 headless (`WLR_BACKENDS=headless`), socket `wayland-1`, IPC `sway-ipc.1000.320103.sock`. Waybar 0.9.24 copy `wb-probe`. Private `dbus-daemon` for the probe only.
Deviations: (a) first probe start exited on "Cannot autolaunch D-Bus without X11 $DISPLAY" (clean env had no bus). Not a signal result, discarded. Fixed by a private session bus. (b) Sway config left empty; probe Waybars launched from the shell, not via `exec` in sway.conf (same display, same env).
Test: survives-RTMIN8 by `kill -0` 3 s after `kill -RTMIN+8 <pid>`. Positive control: `refresh.log` got 1 line after clearing and RTMIN+8 (startup exec wrote 1 line before clearing).
Log note: `basic_string::_M_create` appears in probe log at startup on both probes; not investigated (benign for the check).
Cleanup: probe waybars, private dbus, headless sway killed by PID. `pgrep -x wb-probe` empty. Real Waybar `3479493` and Sway `106996` unchanged.

RESULT: survives-RTMIN8=yes
RESULT: refresh-with-signal8=yes
RESULT: survives-USR2=yes
RESULT: path=survives

Gotcha: `pkill -RTMIN+8 waybar` does not kill Waybar 0.9.24 when no module has `"signal": 8`. The `exec`-based signal refresh works on this version. No change to `ipc.py` needed (D2 kill path not taken).
