# TODO

## Goal
Keep the Waybar label structurally stable and useful by displaying current active sessions over cumulative sessions mined.

## Tasks
- [ ] Always render `🧠 <active> | <total_mined>` using the latest active-session count and cumulative mined total, including zeros.
- [ ] Update focused tests to assert the fixed order and cumulative total across scans.
- [ ] Update README and SPEC to define the headline order and describe the stable fields.
- [ ] Run `python -m pytest tests/test_ipc.py -q` and `make test`; review and commit the fix.
- [ ] Mark this plan complete and archive it under `planning/` in a separate planning commit.

## Notes
- Existing user choice: track planning artifacts. Branch `main`; worktree was clean before this plan.
- User chose active sessions first, followed by cumulative mined sessions, separated by `|`; tooltip labels explain the order and latest-scan counts remain there.
- Do not modify Waybar config, systemd state, or run a live scan/watch.
