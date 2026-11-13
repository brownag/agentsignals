# Execution Plan 8: G20 blind-alleys excludes test scratch; G21 friction lines show real error text (`planning/EXECUTION_PLAN_8.md`)

Orchestration: 8
Source goals: `planning/GOALS.md` [G20] then [G21] (sequenced in the focus; run one after the other)
Status: Draft for user approval. Not started. Not committed.
Starts after: orchestration 7 executed (`579b758`, `b202eb3`, `f513a87`).
Base branch: `g5-g6-g7-g9` (HEAD `f513a87`). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (D3 carried from orchestrations 1–7). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** The offline memory block lists only real work. Blind-alleys no longer lists the claudalizer's own test-run scratch. Tool-friction lines name the failing command and the real error text, not a bare exit code and a code line.

**Exit criteria (from GOALS.md).**
- G20: a session whose scratchpad holds only test-run files yields `- No ephemeral scratchpads recorded.`. The G20 xfail test passes and its marker is removed.
- G21: a failing `pytest` call shows its error line. A friction entry with no error text is dropped, not printed as `Exit code N`. The G21 xfail test passes and its marker is removed.
- Both: `make test` passes; SPEC §3.2 and §4.2 describe both rules as current behaviour.

**In scope**
- `claudalizer/distiller.py`, `synthesize_offline_memory_block` only: the blind-alleys scratch filter (G20), and the friction line format and drop rule (G21).
- `tests/test_distiller.py`: remove the G20 and G21 xfail markers; add tests for kept scratch and for dropped friction entries.
- `planning/SPEC.md` §3.2 (friction and blind-alleys rules) and §4.2 (G20 and G21 bullets).

**Out of scope**
- `build_synthesis_prompt` (the LLM prompt). It still lists all scratch files. Changing the LLM input is a separate decision (D4).
- The miner (`claudalizer/miner.py`). The dossiers keep all scratch paths and all tool errors. The filter is in the distiller (D2).
- Directive patterns (G19 is done) and the PROJECT_MEMORY rebuild (G18 is done).
- Removing or rewriting existing `memory.md` files or PROJECT_MEMORY.md. They change on the next distill (user-run).
- G16, G11, G4 live check, G17, G22. Not touched.
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- User decision (grill Q1, G20): "1" = exclude `g3-accept` and `rewrite-check` scratch only. `planning-backup` and single files stay.
- User decision (grill Q2, G21): "1" = show the first line that looks like an error; drop the entry if no line does.
- GOALS.md G20 exit: "a session whose scratchpad holds only test-run files yields 'No ephemeral scratchpads recorded.' A test covers it."
- GOALS.md G21 exit: "a test with a failing pytest call shows the error line from its output. Entries with no error text are dropped, not printed as 'Exit code N'."
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." Stdlib only.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | Excluded scratch = paths whose first segment is `g3-accept` or `rewrite-check`. Everything else is kept | User decision (grill Q1). These two came from the claudalizer's own test runs | User (grill Q1) |
| D2 | 2026-11-12 | The G20 filter lives in `synthesize_offline_memory_block`, not in the miner | Dossiers stay raw evidence. No re-mine is needed, and the filter is easy to change | Judgment, flagged for review |
| D3 | 2026-11-12 | Error line = the first line containing one of: `FAILED`, `Error`, `error:`, `error[`, `Traceback`, `panicked`, `Exception`, `command not found`, `No such file`. If none matches, the entry is dropped | User decision (grill Q2) | User (grill Q2) |
| D4 | 2026-11-12 | `build_synthesis_prompt` is unchanged, so the LLM still sees all scratch and all errors | Out of scope for G20/G21. Changing LLM input is a separate choice | Judgment, flagged for review |
| D5 | 2026-11-12 | The friction line format is `- **{tool}** (\`{cmd[:80]}\`): {error_line[:200]}`. The `Exit code N` text and `First line:` are removed | Shows the failing command and its real error, as G21 asks | Judgment, flagged for review |
| D6 | 2026-11-12 | If every friction entry is dropped, the friction section is `- None detected.` | Same rule as an empty section today | Default |
| D7 | 2026-11-12 | Planning files tracked (D3 from orchestration 5). Inline execution (D4 from orchestration 5). Acceptance bar: `make test` green, lint at 11 pre-existing findings with none added | Same as orchestrations 5–7 | Default |
| D8 | 2026-11-12 | Three waves, serial: W1 code for G20; W2 code for G21; W3 SPEC for both | Both code changes are in the same function and the same test file, so they cannot run in parallel. The SPEC is one planning commit | Default |

## Recon Log (facts)

- `claudalizer/distiller.py` `synthesize_offline_memory_block` (line 127):
  - Line 130: `scratchpads = dossier_data.get("scratchpad_files", [])`.
  - Lines 137–156: friction section. Line 142 `seen_cmds`; line 154 writes `- **{tool}** (\`{cmd[:80]}\`): Exit code {exit_code}. First line: \`{out[:120]}\``; line 156 `- None detected.` when there are no errors.
  - Lines 158–163: blind-alleys. Line 160 writes `- Ephemeral scratchpad tested: \`{s}\``; line 163 `- No ephemeral scratchpads recorded.`
  - Line 183: `directives.append("None detected.")` (G19, done).
- `build_synthesis_prompt` (line 29) also reads `scratchpad_files` (line 36) and lists them (line 73). Unchanged (D4).
- Real scratch paths for the claudalizer slug (2026-11-12): `planning-backup` (11 sessions), `g3-accept` (8), `rewrite-check` (5), and single files (`dry.log`, `check.log`, `waybar-copy.jsonc`, `g3_accept.sh`, etc.). Only `g3-accept` and `rewrite-check` are excluded (D1).
- Real `error_output` first lines are often code or diff lines, for example `if [ -n "" ]; then \`, `pub(crate) fn network_enabled() -> bool {`, or `['     87 numpy.core.multiarray failed to']`. The error marker in D3 is the first line that matches; the `FAILED tests/...` line appears in pytest output.
- `tests/test_distiller.py`: G20 xfail `test_test_runner_scratch_excluded_from_blind_alleys` (scratch `g3-accept/lock`, `rewrite-check/projects/x.jsonl`; asserts `No ephemeral scratchpads recorded.`). G21 xfail `test_friction_line_shows_real_error_text` (output `Exit code 2\nFAILED tests/x.py::test_y - AssertionError`; asserts the FAILED line appears).
- Baseline: `make test` = 56 passed, 2 xfailed. `make lint` = 11 findings (pre-existing). Tree clean at `f513a87`.
- `planning/SPEC.md` §3.2 friction item (line ~141) and blind-alleys item (line ~142) describe current behaviour and carry no target markers for G20/G21 today; the §4.2 G20 and G21 bullets are target bullets.

## Hazard Notes

- H1: Tests use in-memory dossiers only. No real memories root, no network.
- H2: The filter matches only the first path segment. A path like `docs/g3-accept-notes.md` must not match (test it).
- H3: Do not change `build_synthesis_prompt`, the miner, or the directives block (D4, G19 done).
- H4: Do not run `make install-user`, `make systemd-install`, or `claudalizer watch`.
- H5: Do not run `claudalizer distill` or `scan` in this orchestration. The real files change on the user's next run.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T8.1.1 Blind-alleys excludes g3-accept and rewrite-check scratch (G20) | claudalizer | `claudalizer/distiller.py`, `tests/test_distiller.py` | — | No |
| 2 | T8.2.1 Friction lines show the first error line; drop entries with none (G21) | claudalizer | `claudalizer/distiller.py`, `tests/test_distiller.py` | T8.1.1 | No |
| 3 | T8.3.1 Update SPEC §3.2 and §4.2 for G20 and G21 | claudalizer | `planning/SPEC.md` | T8.2.1 | No |

Serial (D8). Waves 1 and 2 touch the same function and test file.

## Task Specs

### T8.1.1 — Blind-alleys excludes test-run scratch (G20)

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/distiller.py` (`synthesize_offline_memory_block`, the blind-alleys block only; plus one module-level constant if needed), `tests/test_distiller.py`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In `claudalizer/distiller.py`, add a module-level constant `TEST_RUN_SCRATCH_ROOTS = ("g3-accept", "rewrite-check")` near the other module constants.
  2. In `synthesize_offline_memory_block`, before the blind-alleys loop (search for `### 2. Blind Alleys`), filter `scratchpads` to drop any path whose first `/`-separated segment is in `TEST_RUN_SCRATCH_ROOTS`. Keep the rest in their original order. Use `s.split("/", 1)[0]`, so a file named `g3-accept-notes.md` at top level is kept (H2).
  3. The existing blind-alleys output is unchanged for kept paths. If the filtered list is empty, the existing `- No ephemeral scratchpads recorded.` line is written.
  4. Do not change the friction section, the directives section, or `build_synthesis_prompt`.
  5. In `tests/test_distiller.py`:
     a. Remove the `@pytest.mark.xfail(...)` line above `test_test_runner_scratch_excluded_from_blind_alleys`. Body unchanged.
     b. Add `test_scratch_outside_test_runs_is_kept`: `scratchpad_files` = `["planning-backup/notes.md", "g3-accept/lock", "docs/g3-accept-notes.md"]`; assert the blind-alleys section contains `planning-backup/notes.md` and `docs/g3-accept-notes.md`, and does not contain `g3-accept/lock`.
- **Anchors:** `claudalizer/distiller.py`: `def synthesize_offline_memory_block` (search by name), `### 2. Blind Alleys & Discarded Spikes` (search by string), `scratchpads = dossier_data.get("scratchpad_files", [])`. `tests/test_distiller.py`: `def test_test_runner_scratch_excluded_from_blind_alleys` and the `reason="G20` marker above it. Reference: `_section` helper in the same file.
- **Reference implementation:** the existing blind-alleys loop in `synthesize_offline_memory_block`. Filter the input list, then leave the loop as is.
- **Constraints (do not touch)**
  - No change to any function except `synthesize_offline_memory_block` and the one module constant.
  - No change to the G21 xfail marker.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q -rx` exits 0. Expected: 18 passed, 1 xfailed (G21 only).
  - `grep -c 'pytest.mark.xfail' tests/test_distiller.py` prints `1`.
  - `make test` exits 0. Expected: 58 passed, 1 xfailed.
  - `make lint` reports 11 findings, none new.
- **Commit:** `fix(distiller): leave test-run scratch out of blind-alleys` (code and tests together)

### T8.2.1 — Friction lines show the first error line; drop entries with none (G21)

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/distiller.py` (`synthesize_offline_memory_block`, the friction block only; plus one module constant if needed), `tests/test_distiller.py`
  - Can create: none
- **Depends on:** T8.1.1
- **Spec**
  1. In `claudalizer/distiller.py`, add a module-level constant `ERROR_MARKERS = ("FAILED", "Error", "error:", "error[", "Traceback", "panicked", "Exception", "command not found", "No such file")`.
  2. In `synthesize_offline_memory_block`, in the friction block (search for `### 1. Tool / Skill Friction`), replace the line that builds `out` (currently the first line of `error_output`) with: the first line of `error_output` (split on `\n`) that contains any string in `ERROR_MARKERS`. If there is none, skip this entry with `continue` and do not add its key to `seen_cmds` (D3).
  3. Write each kept entry as `- **{tool}** (\`{cmd[:80]}\`): {error_line[:200]}`. Remove the `Exit code` text and `First line:` text (D5).
  4. Track how many lines were written. If none were, write `- None detected.` in place of the empty list (D6). Keep the existing `if errors:` / `else:` structure so the no-errors case still writes `- None detected.`.
  5. Do not change the blind-alleys block, the directives block, or `build_synthesis_prompt`.
  6. In `tests/test_distiller.py`:
     a. Remove the `@pytest.mark.xfail(...)` line above `test_friction_line_shows_real_error_text`. Body unchanged.
     b. Add `test_friction_entry_without_error_marker_is_dropped`: one tool error with `command_or_input` `make build`, `error_output` `Exit code 2\nsome code line`, `exit_code` 2. Assert the friction section contains `- None detected.` and does not contain `Exit code 2` or `some code line`.
- **Anchors:** `claudalizer/distiller.py`: `def synthesize_offline_memory_block`, `### 1. Tool / Skill Friction`, `seen_cmds = set()`, `First line:` (the string to replace). `tests/test_distiller.py`: `def test_friction_line_shows_real_error_text` and the `reason="G21` marker above it. Reference: `test_python_error_maps_to_venv_directive` in the same file, for how a friction-related dossier is built.
- **Reference implementation:** the existing friction loop in `synthesize_offline_memory_block`. Change how `out` is chosen and how the line is written; keep the dedupe and loop structure.
- **Constraints (do not touch)**
  - No change to the blind-alleys block (done in T8.1.1), the directives block, or `build_synthesis_prompt`.
  - No change to any other test.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q -rx` exits 0. Expected: 20 passed, 0 xfailed.
  - `grep -c 'pytest.mark.xfail' tests/test_distiller.py` prints `0`.
  - `grep -c 'First line:' claudalizer/distiller.py` prints `0`.
  - `make test` exits 0. Expected: 60 passed.
  - `make lint` reports 11 findings, none new.
- **Commit:** `fix(distiller): show real error line in friction, drop entries without one` (code and tests together)

### T8.3.1 — Update SPEC §3.2 and §4.2 for G20 and G21

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md` (§3.2 "Offline block format" items 1 and 2; §4.2 G20 and G21 bullets only)
  - Can create: none
- **Depends on:** T8.2.1
- **Spec**
  1. §3.2 item 1 (`Tool / Skill Friction`): describe the current format: `- **{tool}** (\`{cmd}\`): {first line containing an error marker}`. Entries with no marker are dropped. If none remain, `- None detected.`. List the marker strings from D3.
  2. §3.2 item 2 (`Blind Alleys`): state that scratch whose first path segment is `g3-accept` or `rewrite-check` is excluded, and that other scratch is kept.
  3. §4.2: change the G20 and G21 bullets from target to characterisation. Name `test\_scratch\_outside\_test\_runs\_is\_kept` and `test\_friction\_entry\_without\_error\_marker\_is\_dropped` as added tests.
  4. Do not edit any other file.
- **Anchors:** `planning/SPEC.md`: `#### **Offline block format**` (items 1 and 2), and the §4.2 bullets beginning `test\_test\_runner\_scratch` and `test\_friction\_line`.
- **Constraints (do not touch)**
  - Do not change §3.2 Synthesis, Control flow, or the PROJECT_MEMORY.md format.
- **Acceptance (mechanical)**
  - `grep -c 'target, G20\|target, G21' planning/SPEC.md` prints `0`.
  - `grep -c 'First line' planning/SPEC.md` prints `0`.
  - `grep -c 'g3-accept' planning/SPEC.md` prints at least `1`.
  - `make test` exits 0 with the count from T8.2.1 (60 passed).
- **Commit:** `docs(planning): describe blind-alleys filter and friction error line in SPEC` (planning-only)

## Verification at end of wave 3 (orchestrator, serial)

1. `make test`: 60 passed, 0 xfailed.
2. `make lint`: 11 findings, none new.
3. `git log --oneline f513a87..HEAD` shows two code commits (G20, G21), one SPEC commit, and the planning commit for this plan.
4. Report to the user: both rules, the counts, the D2 and D4 judgment calls, and that real PROJECT_MEMORY.md files change on the next `claudalizer distill` or `scan` (user-run).
5. After this orchestration, every goal in the focus is done (G15, G18, G19, G20, G21). Choose what to focus on next with magic-wand.

## Escalation (from wave-orchestration)

1. A new test fails for a reason other than the code under test: stop and report.
2. An xfail passes before its change (XPASS): stop and report.
3. A change alters the output of a section outside its own (for example the directives or the prompt): stop and report. Do not widen the change.
4. Acceptance fails after one retry: stop and report. No third attempt (inline).
5. An out-of-scope edit is needed: stop and re-scope the spec in this file.
