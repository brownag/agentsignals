# Execution Plan 6: G18 PROJECT_MEMORY.md updates each session section in place (`planning/EXECUTION_PLAN_6.md`)

Orchestration: 6
Source goal: `planning/GOALS.md` [G18] (circled; focus: PROJECT_MEMORY.md quality)
Status: Draft for user approval. Not started.
Starts after: orchestration 5 executed (`e51e29d`, `eb8e5da`, `44a51d3`, `feedafb`, `109beba`).
Base branch: `g5-g6-g7-g9` (HEAD `109beba`). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (decision D3 carried from orchestrations 1–5). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** PROJECT_MEMORY.md stops duplicating sections when a session is distilled again, including with `--force`.

**Exit criteria (from GOALS.md G18).** Distilling the same session twice with `--force` leaves one `## Session <id8> Distillation` section for it. The strict xfail `test_force_redistill_does_not_duplicate_project_section` passes, and its marker is removed. `make test` passes.

**In scope**
- `claudalizer/distiller.py`: `MemoryDistiller._append_to_project_memory` changes from append-only to replace-in-place for the current session's section (decision D1 below).
- `tests/test_distiller.py`: remove the `xfail` marker from the G18 test; add tests for the replace, append, and hand-edited-file cases.
- `planning/SPEC.md` §3.2: change the G18 rule from target to current behaviour, and remove the `(target, G18)` markers.

**Out of scope**
- G19 (directives), G20 (scratch filter), G21 (friction lines). Their xfail tests stay as they are.
- Rebuilding the whole file from every session's `memory.md` (rejected at the grill; see D1).
- Removing existing duplicate sections from real files under `~/.claude-mined-memories`. Recon found none (8 files, 22 sections, no duplicate headers). If a future run finds one, that's a separate decision.
- Any change to `distill_session`'s skip-without-force behaviour, or to `memory.md` content.
- G16, G11, G4 live check, G17. Not touched.
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G18 exit: "distilling the same session twice with `--force` leaves one section for it. The G15 duplicate test turns from `xfail` to pass. `make test` passes."
- User decision (2026-11-12, grill Q1 for G18): "2" = replace only the current session's section in place. Not a full rebuild from every session's `memory.md`.
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." Stdlib only. Never touch `~/.claude-mined-memories` or `/tmp/claude-1000` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | The current session's section is replaced in place. If no section for that session exists, it is appended, as today. Other sections are left byte-for-byte unchanged | The user chose in-place over full rebuild. Keeps the change small and leaves hand edits to other sections alone | User (grill Q1) |
| D2 | 2026-11-12 | A section runs from its `## Session <id8> Distillation` heading to the next `---` line followed by a `## Session ` heading, or to end of file | Matches the separator the current code writes (`\n\n---\n## Session …`). Needs no parser | Judgment, flagged for review |
| D3 | 2026-11-12 | If the file exists but has no section for this session, the new section is appended. If the file is missing, it is created. No error is raised for a file that was edited by hand | A hand-edited file should not break distillation | Judgment, flagged for review |
| D4 | 2026-11-12 | Existing duplicate sections in real files are not removed by this change | Recon: none present. Removing data from real files is a separate decision | Judgment, flagged for review |
| D5 | 2026-11-12 | Planning files tracked (D3 from orchestration 5). Workers run inline, one task at a time (D4 from orchestration 5). Acceptance bar: `make test` green, lint at the 12 pre-existing findings with none added | Same as orchestration 5. Single small change | Default |
| D6 | 2026-11-12 | The code change and its tests are one commit. The SPEC update is a separate `docs(planning)` commit | Logical unit: behaviour plus its tests. SPEC is planning-only | Default |

## Recon Log (facts)

- `claudalizer/distiller.py`:
  - `MemoryDistiller.distill_session` (line 197): writes `memory.md` if missing or forced, then calls `self._append_to_project_memory(slug, content, session_id)` (line ~233).
  - `_append_to_project_memory` (line 237): `header = f"\n\n---\n## Session {session_id[:8]} Distillation\n"`; opens `PROJECT_MEMORY.md` with mode `"a"`; writes `header + memory_block + "\n"`.
  - `distill_all` (line 247) calls `distill_session` once per session directory.
- `tests/test_distiller.py`: the G18 test is `test_force_redistill_does_not_duplicate_project_section`, marked `@pytest.mark.xfail(strict=True, reason="G18: PROJECT_MEMORY rebuilt from session files, not appended")`. It distills twice with `force=True` and asserts `project.count("## Session abcdef12 Distillation") == 1`.
- `pytest --runxfail` today: the G18 test fails with `assert 2 == 1`.
- Baseline: `make test` = 48 passed, 4 xfailed. `make lint` = 12 findings, pre-existing.
- Real files (2026-11-12): 8 `PROJECT_MEMORY.md` files, no duplicate `## Session` headers in any of them (checked in Python).
- `planning/SPEC.md` §3.2 has three `(target, G18)` markers, one in "Outputs per session" and two in "PROJECT_MEMORY.md format". §4.2 mentions the G18 test as target.

## Hazard Notes

- H1: Tests use `tmp_path` only. Never the real `~/.claude-mined-memories`.
- H2: Tests make no network calls. `call_llm_completion` is mocked where an endpoint is passed.
- H3: Section boundary logic (D2) must not match a `---` line inside a session's memory block. The block text can contain `---` (it does in the current data), so the boundary must require the `## Session ` heading immediately after the `---`.
- H4: Do not change `distill_session`'s return value or skip behaviour. Other callers and `test_distiller_offline` depend on them.
- H5: Do not run `make install-user`, `make systemd-install`, or `claudalizer watch`.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T6.1.1 Replace the session section in place; remove the G18 xfail; add tests | claudalizer | `claudalizer/distiller.py`, `tests/test_distiller.py` | — | No |
| 2 | T6.2.1 Update SPEC §3.2 to the current G18 behaviour | claudalizer | `planning/SPEC.md` | T6.1.1 | No |

Two tasks with disjoint files, but serial (D5). T6.2.1 describes the behaviour T6.1.1 builds.

## Task Specs

### T6.1.1 — Replace the session section in place; remove the G18 xfail

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `claudalizer/distiller.py` (`_append_to_project_memory`, and at most one private helper next to it), `tests/test_distiller.py`
  - Can create: none
- **Depends on:** none
- **Spec**
  1. In `claudalizer/distiller.py`, change `_append_to_project_memory` (or add a private helper it calls) so that it:
     a. Builds `section = f"## Session {session_id[:8]} Distillation\n{memory_block}\n"`.
     b. If `PROJECT_MEMORY.md` does not exist, writes `"\n\n---\n" + section` (the same leading text as today, so a new file looks the same).
     c. If it exists, finds the line `## Session {session_id[:8]} Distillation`. If found, the section ends at the next line that is `---` immediately followed by a line starting with `## Session `, or at end of file (D2). Replaces that span with `section`, keeping the `---` separator that came after it, if any.
     d. If it exists but the heading is not found, appends `"\n\n---\n" + section` (today's behaviour, D3).
     e. Writes the file with `encoding="utf-8"`. Creates the parent directory as today.
  2. Keep the method's name and signature `(self, slug, memory_block, session_id)`. The call site in `distill_session` does not change.
  3. Do not change other sections' text, order, or whitespace. The replacement touches only the span of the current session's section.
  4. In `tests/test_distiller.py`:
     a. Remove the `@pytest.mark.xfail(...)` line above `test_force_redistill_does_not_duplicate_project_section`. The test body stays as it is.
     b. Add these tests, all using `tmp_path` and `MemoryDistiller(memories_root=...)`:
        - `test_redistill_replaces_only_that_session_section` — two sessions A and B distilled; A re-distilled with `force=True` after its `memory.md` is changed to contain `NEW A`; assert `NEW A` appears once, B's section text is identical before and after, and section order is unchanged.
        - `test_new_session_is_appended_after_existing_sections` — distill A, then B; assert A's heading appears before B's.
        - `test_hand_edited_file_without_session_heading_is_appended_to` — write a `PROJECT_MEMORY.md` with the text `hand notes` and no session headings; distill a session; assert `hand notes` is still present and the new section is present.
  5. Do not change the offline block format, `synthesize_offline_memory_block`, `build_synthesis_prompt`, `call_llm_completion`, or `distill_all`.
- **Anchors:** `claudalizer/distiller.py`: `def _append_to_project_memory` (line 237, search by name, not line); `def distill_session` (line 197). `tests/test_distiller.py`: `def test_force_redistill_does_not_duplicate_project_section` (search by name); `pytest.mark.xfail(strict=True, reason="G18`.
- **Reference implementation:** the current `_append_to_project_memory` (same file, same signature). Replace only its body.
- **Constraints (do not touch)**
  - No change to `distill_session`, `distill_all`, or any function other than `_append_to_project_memory` and its helper.
  - No change to xfail markers for G19, G20, G21.
  - No file under `~/.claude-mined-memories`.
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q -rx` exits 0. Expected: 12 passed, 3 xfailed (the G19, G20, G21 tests).
  - `python -m pytest tests/test_distiller.py -q -k force_redistill` shows the test passing with no xfail marker.
  - `grep -c 'xfail' tests/test_distiller.py` prints 3.
  - `make test` exits 0. Expected: 52 passed, 3 xfailed (40 baseline + 12 test_distiller passing; the 3 remaining xfails are G19–G21).
  - `make lint` reports 12 findings, none new.
- **Commit:** `fix(distiller): update PROJECT_MEMORY session section in place` (code and tests together)

### T6.2.1 — Update SPEC §3.2 to the current G18 behaviour

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md` (§3.2 "Outputs per session" and "PROJECT_MEMORY.md format" only; §4.2 only for the G18 test bullet)
  - Can create: none
- **Depends on:** T6.1.1
- **Spec**
  1. In "Outputs per session", replace the `PROJECT_MEMORY.md` bullet's target sentence with the current behaviour: each distill replaces that session's section in place, or appends it if missing (D1, D3). Remove `**(target, G18)**`.
  2. In "PROJECT_MEMORY.md format", remove the `(target, G18)` marker from the one-section-per-session bullet, and state the in-place rule and the section boundary (D2). Keep the rule that other sections are not touched.
  3. In §4.2, change the G18 bullet from a target xfail to a characterisation test: name the three new tests from T6.1.1, and remove the G18 entry from the target list.
  4. Do not change the G19, G20, or G21 target markers.
  5. Do not edit any other file.
- **Anchors:** `planning/SPEC.md`: `#### **Outputs per session**`, `#### **PROJECT\_MEMORY.md format**`, `#### **4.2`-section bullet beginning `test\_force\_redistill`. Search by these strings.
- **Constraints (do not touch)**
  - Do not change §3.2 Synthesis, Offline block format, or Control flow, except where a sentence names G18.
- **Acceptance (mechanical)**
  - `grep -c 'target, G18' planning/SPEC.md` prints `0`.
  - `grep -c 'target, G19\|target, G20\|target, G21' planning/SPEC.md` prints at least `3`.
  - `grep -c 'in place' planning/SPEC.md` prints at least `1`.
  - `make test` exits 0 with the count from T6.1.1 (52 passed, 3 xfailed).
- **Commit:** `docs(planning): describe in-place PROJECT_MEMORY section update in SPEC` (planning-only, separate from T6.1.1)

## Verification at end of wave 2 (orchestrator, serial)

1. `make test`: 52 passed, 3 xfailed.
2. `make lint`: 12 findings, none new.
3. `git log --oneline 109beba..HEAD` shows one `fix(distiller)` commit and one `docs(planning)` commit for the SPEC, plus the planning commit for this plan.
4. Manual check on a scratch copy: distill one session twice with `--force` in a `tmp_path` root and confirm one section. (The test already covers this; the manual run is only to see the real output.)
5. Report to the user: the change, the test counts, and that G19 is next.

## Escalation (from wave-orchestration)

1. A test in the new set fails for a reason other than the code under test (for example, a fixture bug): stop, report, and fix the test only if the spec was wrong.
2. The G18 xfail passes before the change is made (XPASS): stop. Something else changed the output. Report.
3. The replacement changes another session's text (the test in T6.1.1 step 4b fails): stop and report. Do not widen the replacement.
4. Acceptance fails after one retry: stop and report to the user. (Inline execution, D5: the orchestrator stops; there is no third attempt.)
5. A task needs an out-of-scope edit (for example `claudalizer/miner.py` or a G19 test marker): stop and re-scope the spec in this file.
