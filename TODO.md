# TODO

## Goal
Make Waybar’s zero-result status concise and its tooltip useful at a glance, while keeping only a short history of scans that mined sessions.

## Tasks

### 1. Waybar status formatting
- [ ] Render zero mined sessions as `🧠` without redundant `0 | active 0`; show active count only when nonzero.
- [ ] Place the current scan summary and `Last project` together, before cumulative totals.
- [ ] Replace the full per-scan tooltip dump with at most the three most recent history entries that mined one or more sessions.
- [ ] Add focused tests for zero/nonzero display, tooltip order, and filtering/limiting useful history.

### 2. Verify and record
- [ ] Run `python -m pytest tests/test_ipc.py tests/test_cli.py -q` and `make test`.
- [ ] Review the diff and commit the implementation in a focused local Conventional Commit.
- [ ] Mark this plan complete and commit planning updates separately.

## Notes
- User chose to keep some history: show a short, filtered list of scans with mined sessions (maximum three); omit zero-result scans from that list.
- User asked for a compact zero-result status and said the last-project line is misplaced; keep the project label adjacent to the latest-scan details.
- Planning artifacts are tracked, following the recorded orchestration 10 decision. Current branch is `main`; worktree was clean before this plan. No remote actions.
- Do not run live scans/watch or modify systemd/Waybar config. Tests use `tmp_path` and mocks.
