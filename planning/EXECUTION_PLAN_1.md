# Execution Plan 1: G1 Durable Capture (`planning/EXECUTION_PLAN_1.md`)

Orchestration: 1
Source goal: `planning/GOALS.md` [G1]
Status: Draft, awaiting user approval
Base branch: `g3-watch` (new branch `g1-durable-capture` to be created from it)

## Goal & Scope

**Goal.** Every session scratchpad file either lands in `~/.claude-mined-memories` or is recorded there as a stub that says why it was not copied. No file is dropped without a trace.

**In scope**
- Oversized scratchpad files (over `MAX_SCRATCHPAD_FILE_BYTES`, 250 KiB) are recorded as stubs, not dropped.
- Binary scratchpad files (NUL byte in first 1 KiB) are recorded as stubs, not dropped.
- Files that cannot be read or stat'ed are recorded as stubs with reason `unreadable`. (Judgment call, see decision log.)
- Stubs are stored in a new `skipped_files` list in `dossier.json`. No content is copied for stubs.
- A session whose only scratchpad content is skipped files still gets a dossier.
- `planning/SPEC.md` §3.1 (dossier schema) and §4.1 (`test_filter_oversized_scratchpad`) are updated to match.
- `planning/GOALS.md` citations for G1 and G9 are corrected.

**Out of scope**
- Deliberate excludes stay silent: `venv`, `.venv`, `node_modules`, `.git`, `__pycache__`, and symlinks. They are noise filters, not data loss. (Judgment call, see decision log.)
- G8 size-policy changes. The cap stays at 250 KiB.
- Settle window, lock timeout, and debounce behavior.
- Distillation (`distiller.py`) changes. Read-only check only.
- G9 spec test suite beyond the §4.1 entry. G9 is a separate goal.
- G7 (failed tool-result retention).
- Pushes, pull requests, or any remote action.

**Verbatim constraints (from GOALS.md and user)**
- "Every session scratchpad file is in `~/.claude-mined-memories` before `/tmp/claude-1000` is deleted, with no silent drops."
- "The size policy does not have to be rigid but should be no larger than absolutely necessary." (user, 2026-11-12)
- Size cap: 250 KiB. Oversized files are recorded as stubs (user choice: stub record only).
- Binary files get the same stub treatment (user choice: yes).
- Stub location: new `skipped_files` field in dossier (user choice).
- Tracking: planning artifacts are tracked, committed separately as `docs(planning):` (user choice).
- Branch: new branch from `g3-watch` (user choice). The repo has no `main`; the default branch is `master`, which lacks G2.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | Oversized file → stub record only, no content copied | Keeps archive within cap; makes the drop visible | User |
| D2 | 2026-11-12 | Binary file → same stub, reason `binary` | "No silent drops" applies to binaries too | User |
| D3 | 2026-11-12 | Stubs stored in new `skipped_files` list in dossier.json | Keeps copied and skipped files separate | User |
| D4 | 2026-11-12 | Update SPEC §4.1 test description to stub behavior; fix 256 KB → 250 KiB; fix GOALS citation (old SPEC L783-786 is IPC test code) | Spec and code must agree | User |
| D5 | 2026-11-12 | Planning artifacts tracked; `docs(planning):` commits separate from code | Matches existing tracked planning/ files | User |
| D6 | 2026-11-12 | Work on new branch `g1-durable-capture` from `g3-watch` | Needs G2 atomic-write commit; repo has no `main` | User |
| D7 | 2026-11-12 | Add stub reason `unreadable` for OSError during stat/read | Current `except OSError: continue` is a silent drop; user said "no silent drops" | Judgment (flagged for review) |
| D8 | 2026-11-12 | Deliberate excludes (venv, node_modules, .git, __pycache__, symlinks) stay silent | They are noise filters, not data; recording them would bloat the dossier | Judgment (flagged for review) |
| D9 | 2026-11-12 | Parallelism: waves as set below; worker model = cheapest capable, escalation ladder per wave-orchestration | Defaults. The user did not ask; within-file work cannot be parallel | Default |
| D10 | 2026-11-12 | Acceptance per task = targeted pytest; orchestrator runs `make check` serially at end of wave 2 | Per wave-orchestration rules | Default |

## Recon Log (facts, not questions)

- `claudalizer/miner.py` is 452 lines. Relevant anchors:
  - `MAX_SCRATCHPAD_FILE_BYTES = 250 * 1024` at line 22.
  - `SessionDossier` dataclass at lines 38-50. `scratchpad_files` is at line 46.
  - `snapshot_scratchpad` at lines 281-325. Silent skips: `if sz > max_file_size: continue`, binary `continue`, and `except (OSError, PermissionError): continue`.
  - `_mine_session` at lines 389-452. Caller of `snapshot_scratchpad` at line 415. Empty-session early return is just after it (`if not user_prompts and not tool_errors and not copied_files: return None`).
- `snapshot_scratchpad` has one production caller (`miner.py:415`) and one test caller (`tests/test_miner.py:112`).
- `tests/test_miner.py` is 385 lines. `test_snapshot_scratchpad` is at lines 90-117. It covers the binary, large, and venv skips.
- `planning/SPEC.md` is 817 lines. Dossier schema is at §3.1 (lines ~77-112). The oversized test is at line 187 ("Verify files >256 KB are skipped"). Line 348-368 is the test body in the spec's appendix.
- `planning/SPEC.md` lines 783-786 are IPC test code. GOALS.md cites them as "the four spec tests for G1 and G2". That citation is wrong.
- No `docs/decisions/` directory exists, so there are no active ADRs to check.
- Git: current branch `g3-watch`. Only branches are `g3-watch` and `master`. G2 commit `80f5ba4` is on `g3-watch` only. Uncommitted: `planning/GOALS.md` (modified), `TODO-g3.md`, `TODO.md` (untracked, not part of this plan).
- Baseline: `make test` on `g3-watch` gives 14 passed (confirmed this session).
- Dossier schema readers: `distiller.py` loads dossiers; worker must confirm it tolerates a missing `skipped_files` key (see T1.2).

## Hazard Notes

- **Silent-drop trap in `_mine_session`.** The empty-session early return ignores skipped files. Without the fix in T1.2, a session whose only scratchpad file is oversized vanishes from the archive.
- **Signature change.** `snapshot_scratchpad` returns a tuple after T1.1. Its one production caller must be updated in the same task, or the code breaks between waves.
- **Stat inside the try block.** `item.stat()` is inside the `try`, so stat failures land in `unreadable`. `size_bytes` may be `None` for those.
- **Lint is soft.** `make lint` ends with `|| echo`. Read its output for ruff findings after each task.
- **Do not touch live state.** Never write to `/tmp/claude-1000` or `~/.claude-mined-memories` directly. Tests must use `tmp_path`.
- **Cap is unchanged.** Do not edit `MAX_SCRATCHPAD_FILE_BYTES` (AGENTS.md: cap changes are Ask First).

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T1.1.1 | claudalizer | `claudalizer/miner.py` (snapshot_scratchpad + its one caller), `tests/test_miner.py` | — | Yes, disjoint from T1.1.2 |
| 1 | T1.1.2 | claudalizer | `planning/SPEC.md`, `planning/GOALS.md` | — | Yes, disjoint from T1.1.1 |
| 2 | T1.2.1 | claudalizer | `claudalizer/miner.py` (SessionDossier, _mine_session), `tests/test_miner.py` | T1.1.1 | No (same files as T1.1.1, so separate wave) |
| 3 | T1.3.1 | claudalizer | `tests/test_miner.py` (new `test_filter_oversized_scratchpad` only) | T1.1.1, T1.2.1 | Single task; closes G1 |

Wave 1 tasks are disjoint: T1.1.1 owns the code and its tests, T1.1.2 owns the two planning docs. Wave 2 is sequenced because it edits the same two files as T1.1.1.

Before wave 1: create branch `g1-durable-capture` from `g3-watch` and record the baseline in STATE_1.md. Run `make test` and `make lint` and record both.

## Task Specs

### T1.1.1 — Snapshot reports every skipped scratchpad file

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/miner.py`, `tests/test_miner.py`
  - Can create: none
  - Temp/scratch: `.development/` (untracked)
- **Depends on:** none
- **Spec**
  1. Change `snapshot_scratchpad` to return `Tuple[List[str], List[Dict[str, Any]]]`: `(copied, skipped)`.
  2. Each `skipped` entry is `{"path": <rel posix str>, "size_bytes": <int or None>, "reason": "oversized" | "binary" | "unreadable"}`.
  3. Order of checks per file: symlink/non-file → silent (unchanged). Excluded directory part → silent (unchanged). `stat` fails → `unreadable`. Size > cap → `oversized`. Read chunk has NUL → `binary`. Copy fails with OSError → `unreadable`.
  4. Do not copy content for skipped files.
  5. Update the single caller in `_mine_session` to unpack: `copied_files, _ = snapshot_scratchpad(...)`. T1.2.1 wires the value through.
  6. Update `test_snapshot_scratchpad` to unpack the tuple. Keep its existing assertions.
  7. Add `test_snapshot_reports_skipped_files`: one oversized file, one binary file, one unreadable case (use `monkeypatch` to make `open` or `copy2` raise `PermissionError`). Assert each appears in `skipped` with the right reason, and that none appears in `copied`.
- **Anchors (grep, do not read whole file)**
  - `miner.py`: `def snapshot_scratchpad`, `if sz > max_file_size`, `b"\x00" in chunk`, `except (OSError, PermissionError)`, `snapshot_scratchpad(scratchpad_dir`.
  - `tests/test_miner.py`: `def test_snapshot_scratchpad`, `copied = snapshot_scratchpad`.
- **Reference implementation:** the existing `snapshot_scratchpad` body (`miner.py` lines 281-325). Extend it. Do not rewrite it.
- **Constraints (do not touch)**
  - Do not change `MAX_SCRATCHPAD_FILE_BYTES`.
  - Do not change the excluded-directory list or symlink handling.
  - Do not edit `SessionDossier` or `_mine_session` beyond the one-line unpack.
  - Do not edit `planning/`.
- **Acceptance (mechanical)**
  - `pytest tests/test_miner.py -q -k snapshot` exits 0, and includes `test_snapshot_reports_skipped_files`.
  - `ruff check claudalizer/miner.py tests/test_miner.py` reports no new findings compared with baseline.
- **Commit:** `feat(miner): report skipped scratchpad files` (one commit, code only).

### T1.1.2 — Spec and goal docs match the stub policy

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md`, `planning/GOALS.md`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In SPEC §3.1 (dossier schema, around lines 77-112), add a `skipped_files` field to the JSON example. Shape: `[{"path": "...", "size_bytes": 1234, "reason": "oversized|binary|unreadable"}]`. Add one sentence: skipped files are not copied; each is listed here.
  2. In SPEC §3.1 stats example, add `"skipped_count"`.
  3. In SPEC §4.1, replace the `test_filter_oversized_scratchpad` bullet (line ~187). New text: "Verify files over 250 KiB and binary files are not copied, each is listed in `skipped_files` with its reason, and smaller .py, .sh, and .log files are archived." Keep the test name.
  4. In `planning/GOALS.md`, G1 exit criteria: replace any mention of "SPEC.md L783-786" with "SPEC.md §4.1 and §3.1".
  5. In `planning/GOALS.md`, G9 description: replace "(SPEC.md L783-786)" with "(SPEC.md §4.1)".
- **Anchors:** `SPEC.md`: "Dossier Schema", "test\_filter\_oversized\_scratchpad", "256". `GOALS.md`: "L783-786".
- **Constraints (do not touch):** no other spec sections. No changes to code files. Do not change the 250 KiB cap.
- **Acceptance (mechanical, docs-only, no pytest)**
  - `grep -n "256" planning/SPEC.md` returns no line about scratchpad size.
  - `grep -n "L783" planning/GOALS.md` returns nothing.
  - `grep -n "skipped_files" planning/SPEC.md` returns at least two lines.
- **Commit:** `docs(planning): record stub policy for skipped scratchpad files` (planning-only commit, separate from code).

### T1.2.1 — Skipped files reach the dossier; sessions with only skipped files are kept

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/miner.py` (`SessionDossier`, `_mine_session`), `tests/test_miner.py`
  - Can edit (conditional, only if step 6 finds a strict key lookup): `claudalizer/distiller.py`
  - Can create: none
- **Depends on:** T1.1.1 (its tuple return and `skipped` list)
- **Spec**
  1. Add `skipped_files: List[Dict[str, Any]] = field(default_factory=list)` to `SessionDossier`, placed after `scratchpad_files`.
  2. In `_mine_session`, unpack `copied_files, skipped_files = snapshot_scratchpad(...)`.
  3. Change the empty-session early return so a session with any skipped file is kept: `if not user_prompts and not tool_errors and not copied_files and not skipped_files: return None`.
  4. Pass `skipped_files=skipped_files` into `SessionDossier(...)`.
  5. Add `"skipped_count": len(skipped_files)` to `stats`.
  6. Check `claudalizer/distiller.py` for how it reads `dossier.json`. If it reads with a strict key lookup, switch it to tolerate a missing `skipped_files` key. This check is read-only unless a strict lookup is found.
  7. Add `test_session_with_only_skipped_file_gets_dossier`: a session dir with no transcript and one oversized file. Assert a dossier is written, `skipped_files` has one entry with reason `oversized`, and `stats["skipped_count"] == 1`.
- **Anchors:** `miner.py`: `class SessionDossier`, `scratchpad_files: List[str]`, `def _mine_session`, `if not user_prompts and not tool_errors and not copied_files`, `stats={`. `distiller.py`: grep `dossier` and `json.load`. `tests/test_miner.py`: `test_session_miner_pipeline` as reference for building a session workspace.
- **Reference implementation:** `test_session_miner_pipeline` (`tests/test_miner.py:126`) for the fixture shape. Do not invent a new harness.
- **Constraints (do not touch)**
  - Do not change `snapshot_scratchpad` (owned by T1.1.1).
  - Do not change the dossier-write atomic logic (G2, done).
  - Do not change the re-mine check (`scratchpad_changed_since`).
  - Do not edit `planning/`.
- **Acceptance (mechanical)**
  - `pytest tests/test_miner.py -q` exits 0 with all tests passing, including the new one.
  - `pytest tests/test_miner.py -q -k "dossier or skipped"` exits 0.
- **Commit:** `feat(miner): keep skipped scratchpad files in dossier` (code only).

### T1.3.1 — SPEC §4.1 test for oversized and binary scratchpad files

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `tests/test_miner.py` (add one test)
  - Can create: none
- **Depends on:** T1.1.1 (skipped reasons), T1.2.1 (dossier wiring is not used by this test, but wave 3 starts after wave 2 is done)
- **Spec**
  1. Add `test_filter_oversized_scratchpad` to `tests/test_miner.py`. The name is fixed by SPEC.md §4.1; do not rename it.
  2. In a temp scratchpad, create `small.py`, `small.sh`, `small.log` (each a few bytes), `big.log` (`MAX_SCRATCHPAD_FILE_BYTES + 1` bytes of `a`), and `blob.bin` (a NUL byte followed by text).
  3. Call `snapshot_scratchpad(src, dst)` with default size cap.
  4. Assert `copied` equals the three small files, and that each small file exists in `dst`.
  5. Assert `big.log` and `blob.bin` are not in `dst`.
  6. Assert `skipped` has exactly two entries: `big.log` with reason `oversized` and `size_bytes == MAX_SCRATCHPAD_FILE_BYTES + 1`, and `blob.bin` with reason `binary`.
- **Anchors:** `tests/test_miner.py`: `def test_snapshot_reports_skipped_files` (around line 120), the closest reference. `claudalizer/miner.py`: `MAX_SCRATCHPAD_FILE_BYTES` (line 22), `def snapshot_scratchpad` (line 281).
- **Reference implementation:** `test_snapshot_reports_skipped_files`. Copy its fixture shape.
- **Constraints (do not touch)**
  - Do not change `claudalizer/miner.py`. If the test fails because the code is wrong, STOP and report. Do not fix the code in this task.
  - Do not edit `planning/`.
- **Acceptance (mechanical)**
  - `pytest tests/test_miner.py -q -k filter_oversized` exits 0 with 1 passed.
  - `pytest tests/test_miner.py -q` exits 0.
- **Commit:** `test(miner): cover oversized and binary scratchpad filtering` (test only).

## Verification at end of wave 3 (orchestrator, serial)

1. `make check` exits 0. Read lint output; no findings beyond the 12 pre-existing.
2. Confirm G1 exit criteria in GOALS.md are met: stubs for oversized and binary files, the dossier for skipped-only sessions, and the §4.1 test passing.
3. Close G1 in GOALS.md and STATE_1.md. This unblocks orchestration 2.

## Verification at end of wave 2 (orchestrator, serial)

1. `make check` (lint + full test) exits 0. Read lint output for ruff findings.
2. Confirm `git log --oneline g3-watch..g1-durable-capture` shows code commits from T1.1.1 and T1.2.1 and a `docs(planning)` commit from T1.1.2.
3. Confirm the G1 exit criteria in GOALS.md are met: stubs for oversized and binary files, and a dossier for skipped-only sessions.
