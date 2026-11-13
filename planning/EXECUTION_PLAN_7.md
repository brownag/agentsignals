# Execution Plan 7: G19 Directives come from the session only (`planning/EXECUTION_PLAN_7.md`)

Orchestration: 7
Source goal: `planning/GOALS.md` [G19] (circled; focus: PROJECT_MEMORY.md quality)
Status: Draft for user approval. Not started. Not committed.
Starts after: orchestration 6 executed (`c5162a6`, `6864075`, `4cb53fa`).
Base branch: `g5-g6-g7-g9` (HEAD `4cb53fa`). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (decision D3 carried from orchestrations 1–6). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** The "Directives for CLAUDE.md" section of each memory block contains only what the session's errors support. The generic line "Maintain strict idempotency and check environment variables before execution." is no longer written by default.

**Exit criteria (from GOALS.md G19).** With no matching error, the directives section reads `- None detected.`, not the fallback line. The G19 xfail test `test_no_matching_error_shows_none_detected_not_fallback_directive` passes, and its marker is removed. `make test` passes.

**In scope**
- `claudalizer/distiller.py`: in `synthesize_offline_memory_block`, replace the fallback directive with `None detected.` (D1).
- `tests/test_distiller.py`: remove the G19 xfail marker; add one test for the case where errors exist but none match a pattern.
- `planning/SPEC.md` §3.2 and §4.2: state the rule as current behaviour, and remove the `(target, G19)` markers.

**Out of scope**
- Adding new directive patterns. The three existing patterns stay as they are.
- G20 (scratch filter) and G21 (friction lines). Their xfail tests stay.
- Changing the friction or blind-alleys sections.
- Changing the LLM prompt (`build_synthesis_prompt`, `DISTILLATION_SYSTEM_PROMPT`).
- Rewriting the real `~/.claude-mined-memories` files. They change on the next distill (see Verification).
- G16, G11, G4 live check, G17, G22. Not touched.
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G19 exit: "with no matching error, the section reads 'None detected', not the fallback line. The G15 fallback test turns from `xfail` to pass."
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." Stdlib only.
- AGENTS.md "Never": do not modify `~/.claude-mined-memories` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | When no error matches a directive pattern (including when there are no errors at all), the directives section is `- None detected.` This replaces the fallback line | The goal's rule is "directives come from the session only". "No match" and "no errors" get the same answer, so the section never shows boilerplate. Matches the existing `- None detected.` wording in the friction section | Judgment, flagged for review |
| D2 | 2026-11-12 | Directive patterns are not extended in this change | Out of scope. New patterns are a separate goal if wanted | Default |
| D3 | 2026-11-12 | Planning files tracked (D3 from orchestration 5). Workers run inline, one task at a time (D4 from orchestration 5). Acceptance bar: `make test` green, lint at the pre-existing findings with none added | Same as orchestrations 5–6 | Default |
| D4 | 2026-11-12 | The code change and its tests are one commit. The SPEC update is a separate `docs(planning)` commit | Same as orchestration 6 | Default |

## Recon Log (facts)

- `claudalizer/distiller.py` `synthesize_offline_memory_block`:
  - Line 170: `# Infer directives from errors`; line 171: `directives = []`.
  - Lines 172–181: three pattern checks, appending to `directives`.
  - Lines 182–183: `if not directives: directives.append("Maintain strict idempotency and check environment variables before execution.")`.
  - Lines 185–187: sorted, de-duplicated, written as `- {d}`.
  - So with no matching pattern the output is `- Maintain strict idempotency...`. With the change it is `- None detected.`
- `tests/test_distiller.py`: `test_no_matching_error_shows_none_detected_not_fallback_directive` is marked `@pytest.mark.xfail(strict=True, reason="G19: generic fallback directive removed")`. Today it fails with `'Maintain strict idempotency' is contained here`.
- Baseline: `make test` = 54 passed, 3 xfailed. `make lint` = 11 findings (pre-existing).
- Real files (2026-11-12): 17 of 22 sections contain the fallback line (checked before G18). These will change to `- None detected.` on the next distill.
- `planning/SPEC.md` §3.2 "Offline block format" item 3 has the `(target, G19)` marker. §4.2 lists the G19 test as a target.

## Hazard Notes

- H1: Tests use `tmp_path` or in-memory dossiers only. No real memories root.
- H2: No network. The LLM path is not touched.
- H3: The change is one line in the directives block. Do not refactor the three pattern checks; that would widen the change.
- H4: Do not run `make install-user`, `make systemd-install`, or `claudalizer watch`.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T7.1.1 Replace fallback directive with `None detected.`; remove G19 xfail; add a test | claudalizer | `claudalizer/distiller.py`, `tests/test_distiller.py` | — | No |
| 2 | T7.2.1 Update SPEC §3.2 and §4.2 to the G19 rule | claudalizer | `planning/SPEC.md` | T7.1.1 | No |

Serial (D3).

## Task Specs

### T7.1.1 — Replace the fallback directive; remove the G19 xfail

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/distiller.py` (`synthesize_offline_memory_block`, the directives block only), `tests/test_distiller.py`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In `claudalizer/distiller.py`, in `synthesize_offline_memory_block`, change the fallback line (search for `Maintain strict idempotency`) from `directives.append("Maintain strict idempotency and check environment variables before execution.")` to `directives.append("None detected.")`. Keep the `if not directives:` guard and the dedupe loop unchanged.
  2. Do not change the three pattern checks, the friction section, the blind-alleys section, or the header.
  3. In `tests/test_distiller.py`:
     a. Remove the `@pytest.mark.xfail(...)` line above `test_no_matching_error_shows_none_detected_not_fallback_directive`. Body unchanged.
     b. Add `test_directives_none_detected_when_errors_match_no_pattern`: a dossier with one tool error whose `command_or_input` is `ls`, `error_output` is `Exit code 1`, and `exit_code` 1 (no pattern matches); assert that the directives section contains `- None detected.` and does not contain `Maintain strict idempotency`.
  4. Do not change any other xfail marker (G20, G21).
- **Anchors:** `claudalizer/distiller.py`: `def synthesize_offline_memory_block` (search by name), the string `Maintain strict idempotency` (the line to replace). `tests/test_distiller.py`: `def test_no_matching_error_shows_none_detected_not_fallback_directive` and the `reason="G19` marker above it. Reference: `test_python_error_maps_to_venv_directive` in the same file, for how a directive assertion is written.
- **Reference implementation:** the existing directives block in `synthesize_offline_memory_block` (same function). Change one string only.
- **Constraints (do not touch)**
  - No change to any function other than `synthesize_offline_memory_block`.
  - No change to xfail markers for G20 and G21.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q -rx` exits 0. Expected: 16 passed, 2 xfailed (G20 and G21 only).
  - `grep -c 'Maintain strict idempotency' claudalizer/distiller.py` prints `0`.
  - `grep -c 'xfail' tests/test_distiller.py` prints `2`.
  - `make test` exits 0. Expected: 56 passed, 2 xfailed.
  - `make lint` reports 11 findings, none new.
- **Commit:** `fix(distiller): write None detected when no directive matches` (code and tests together)

### T7.2.1 — Update SPEC §3.2 and §4.2 to the G19 rule

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md` (§3.2 "Offline block format" item 3; §4.2 G19 bullet only)
  - Can create: none
- **Depends on:** T7.1.1
- **Spec**
  1. In §3.2 "Offline block format", item 3: replace the sentence describing the fallback line and `(target, G19)` with the current rule: when no error matches a pattern, or there are no errors, the section is `- None detected.` (D1). Remove `**(target, G19)**`.
  2. In §4.2, change the G19 target bullet (`test\_no\_matching\_error\_shows\_none\_detected\_not\_fallback\_directive (G19)`) to a characterisation bullet, and add `test\_directives\_none\_detected\_when\_errors\_match\_no\_pattern`. Remove the G19 entry from the target list.
  3. Do not change the G20 or G21 target markers.
  4. Do not edit any other file.
- **Anchors:** `planning/SPEC.md`: `#### **Offline block format**`, the item beginning `3. \`### 3. Directives`, the §4.2 bullet beginning `test\_no\_matching`.
- **Constraints (do not touch)**
  - Do not change §3.2 Synthesis, Control flow, or the PROJECT_MEMORY.md format.
- **Acceptance (mechanical)**
  - `grep -c 'target, G19' planning/SPEC.md` prints `0`.
  - `grep -c 'target, G20\|target, G21' planning/SPEC.md` prints at least `2`.
  - `grep -c 'Maintain strict idempotency' planning/SPEC.md` prints `0`.
  - `make test` exits 0 with the count from T7.1.1 (56 passed, 2 xfailed).
- **Commit:** `docs(planning): describe None detected directive rule in SPEC` (planning-only)

## Verification at end of wave 2 (orchestrator, serial)

1. `make test`: 56 passed, 2 xfailed.
2. `make lint`: 11 findings, none new.
3. `git log --oneline 4cb53fa..HEAD` shows one `fix(distiller)` commit and one `docs(planning)` commit, after the planning commit.
4. Report to the user: the change, the counts, and that the real PROJECT_MEMORY.md files will show `- None detected.` in the directives section after the next `claudalizer distill` or `scan`. Those runs are the user's to start.
5. Next goals (G20, G21) remain sequenced. The circled slot is empty after G19 closes; choose the next circled goal with magic-wand.

## Escalation (from wave-orchestration)

1. A new test fails for a reason other than the code under test: stop and report.
2. The G19 xfail passes before the change (XPASS): stop and report.
3. The change alters a section other than directives (a characterisation test fails): stop and report. Do not widen the change.
4. Acceptance fails after one retry: stop and report to the user. No third attempt (inline).
5. An out-of-scope edit is needed (for example a new directive pattern, or a G20/G21 marker): stop and re-scope the spec in this file.
