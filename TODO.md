# TODO

## Goal
Keep the Waybar label structurally stable and useful by displaying cumulative sessions mined and the current active-session count.

## Tasks
- [ ] Always render `🧠 total <total_mined> | active <active>` using the cumulative mined total and latest active-session count, including zeros.
- [ ] Update focused tests to assert the fixed format for zero and nonzero values and cumulative totals across scans.
- [ ] Run `python -m pytest tests/test_ipc.py -q` and `make test`; review and commit the fix.
- [ ] Mark this plan complete and archive it under `planning/` in a separate planning commit.

## Notes
- Existing user choice: track planning artifacts. Branch `main`; worktree was clean before this plan.
- User chose cumulative total mined plus current active sessions for the headline; latest-scan counts remain in the tooltip.
- Do not modify Waybar config, systemd state, or run a live scan/watch.
