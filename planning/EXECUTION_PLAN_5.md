# Execution Plan 5: G15 Distiller spec and tests cover PROJECT_MEMORY.md (`planning/EXECUTION_PLAN_5.md`)

Orchestration: 5
Source goal: `planning/GOALS.md` [G15] (circled; magic-wand focus on project-memory quality)
Status: Draft for user approval. Not started.
Starts after: orchestration 4 executed (`b3e4365`, `edb3cba`, `ba4f645`); the Waybar install change `922db54` is also on the branch.
Base branch: `g5-g6-g7-g9` (HEAD `922db54`). Work stays on this branch unless the user says otherwise.
Planning tracking: tracked (user, 2026-11-12). Planning commits are separate `docs(planning)` commits.

## Goal & Scope

**Goal (user's terms).** The mined per-project memory (`~/.claude-mined-memories/<slug>/PROJECT_MEMORY.md`) is correct, derived, and worth reading. This orchestration does the groundwork: the spec describes the distiller that actually runs, and tests pin that behaviour. The fixes come later (G18–G21).

**Exit criteria (from GOALS.md G15).** SPEC describes the PROJECT_MEMORY.md format and the distiller's current behaviour. Criteria 1–4 each have a test in `tests/test_distiller.py` (strict xfail where the behaviour is a target). Criterion 5 is checked by the grep acceptance in T5.1.1 (D8). Tests for target behaviour that is not built yet are marked `xfail(strict=True)` with the goal id. `make test` passes.

**Working criteria for "good" (from GOALS.md, to be confirmed by the user).**
1. One section per session, no duplicates after re-runs, including `--force` (G18).
2. Every section is derived from its session; no boilerplate directives (G19).
3. Tool-friction lines name the failing command and its real error text (G21).
4. Blind-alleys lists real work, not the claudalizer's own test runs (G20).
5. The format is written down in the spec, so tests can check it (this orchestration).

**In scope**
- Rewrite SPEC §3.2 (distiller) and §4.2 (`tests/test_distiller.py` requirements) to describe the current distiller and PROJECT_MEMORY.md (decision D1).
- Create `tests/test_distiller.py`: characterisation tests for current behaviour that is correct, and strict `xfail` tests for G18–G21 target behaviour (decision D2).

**Out of scope**
- Any change to `claudalizer/` code. G18–G21 do that, one at a time, after this orchestration.
- Changing or moving the existing `tests/test_miner.py::test_distiller_offline`. It stays where it is.
- Re-running distillation on the real `~/.claude-mined-memories`. Tests use `tmp_path` only.
- The `claudalizer.service` start-limit loop (tracked under G6, not this plan).
- The LLM client against a real endpoint (G10, deferred). Tests mock the HTTP call.
- G16, G11, G4 live check, G17. Not touched.
- Pushes, pull requests, or any remote action.

**Verbatim constraints**
- GOALS.md G15 exit: "SPEC §4.2 states the PROJECT_MEMORY.md format and the five criteria above. Each one has a test in `tests/test_distiller.py`. Tests that describe target behaviour that is not yet built (duplicates on `--force`, generic fallback) are marked `xfail` with the goal id. `make test` passes."
- GOALS.md G15 files in scope: `planning/SPEC.md`, `tests/test_distiller.py` (new), `tests/conftest.py` only if a fixture is needed.
- User decision D1 (2026-11-12): "1" = rewrite the spec to the current design, then test that. Not the old CLAUDE.md design (G12 is pruned).
- User decision D2 (2026-11-12): "1" = target behaviour is `xfail` with the goal id.
- User decision D3 (2026-11-12): "1" = planning artifacts tracked, separate `docs(planning)` commits.
- User decision D4 (2026-11-12): "1" = workers run inline, one task at a time (same as orchestrations 3–4).
- AGENTS.md: "Run `make test` after changing `claudalizer/` or `tests/`." "Add runtime dependencies" is never allowed (stdlib only; pytest is dev-only and already present).
- AGENTS.md "Never": do not delete or modify `/tmp/claude-1000` or `~/.claude-mined-memories/` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | Rewrite SPEC §3.2 and §4.2 to describe the current distiller and PROJECT_MEMORY.md. The old CLAUDE.md design is dropped from the spec | Code is what runs. CLAUDE.md injection is pruned in G12. The old spec names functions that do not exist | User (grill Q1) |
| D2 | 2026-11-12 | Target behaviour (G18 duplicates, G19 fallback directive, G20 scratch filter, G21 friction lines) is tested with `xfail(strict=True, reason="G18")` etc. | Shows the gap in the plan. Strict mode makes the marker removal a required step when a goal lands | User (grill Q2) |
| D3 | 2026-11-12 | Planning files are tracked, with separate `docs(planning)` commits | Same as orchestrations 1–4 | User (grill Q3) |
| D4 | 2026-11-12 | Workers run inline by the orchestrator, one task at a time | Two small tasks in sequence; no parallelism needed | User (grill Q4) |
| D5 | 2026-11-12 | Acceptance bar per wave: `make test` green, and lint at the 12 pre-existing findings with none added | Existing convention (AGENTS.md; GOALS G17). Judgment, flagged for review | Default |
| D6 | 2026-11-12 | The tests call `MemoryDistiller(memories_root=tmp_path)` and mock `call_llm_completion`. No test writes to the real memories root or makes a network call | Keeps tests hermetic; AGENTS.md forbids touching `~/.claude-mined-memories` directly | Judgment, flagged for review |
| D7 | 2026-11-12 | The new file is `tests/test_distiller.py`. `test_miner.py::test_distiller_offline` stays where it is | GOALS G15 names the new file. Moving an existing test is out of scope | Judgment, flagged for review |
| D8 | 2026-11-12 | Criterion 5 (the format is written down) is verified by the T5.1.1 grep acceptance, not by a pytest test. The other four criteria have pytest tests | A test that reads the spec would only check that a heading exists. Flagged for review; say so if you want a test | Judgment, flagged for review |

## Recon Log (facts)

- Branch `g5-g6-g7-g9`, HEAD `922db54`, clean except `planning/GOALS.md` (magic-wand update, uncommitted at plan time; committed with the plan approval).
- `make test`: 40 passed (includes 10 from `tests/test_waybar_config.py`). `make lint`: 12 findings, pre-existing.
- `planning/` is **not** git-ignored (tracked per D3).
- SPEC: §3.2 (`### **3.2 distiller.py ...`, line ~123) describes an OpenAI client, `distillation_prompt.md` fallback, and CLAUDE.md marker blocks. §4.2 (`### **4.2 Distillation & HTTP (test\_distiller.py)**`, line ~201) lists three tests against functions that do not exist (`build_distillation_prompt`, `call_openai_completion`, `distill_session`, `append_to_claude_md`). §5 (line ~213) and the test-file skeleton (line ~540) repeat the same names; these are in scope only where they describe distiller tests.
- SPEC never mentions PROJECT_MEMORY.md (`grep -c PROJECT_MEMORY planning/SPEC.md` = 0).
- `claudalizer/distiller.py` (281 lines). Anchors:
  - `build_synthesis_prompt` (line 29): prompt builder; reads `tool_errors`, `scratchpad_files`.
  - `call_llm_completion` (line 89): the HTTP call. Mock this in tests.
  - `synthesize_offline_memory_block` (line 126): offline markdown. Sections: `### 1. Tool / Skill Friction` (friction lines at ~line 140–155), `### 2. Blind Alleys & Discarded Spikes` (line 157), `### 3. Directives for CLAUDE.md` (line 164). Fallback directive at line 181–182. Dedup at line 185.
  - `MemoryDistiller.distill_session` (line 197): writes `memory.md`; skips if it exists and `force` is false; calls `_append_to_project_memory` every time it writes.
  - `MemoryDistiller._append_to_project_memory` (line 237): appends `\n\n---\n## Session {id[:8]} Distillation\n` + block to `<root>/<slug>/PROJECT_MEMORY.md`.
  - `MemoryDistiller.distill_all` (line 247): iterates slug dirs and session dirs under the root.
- `tests/`: `conftest.py` (autouse stub of `ipc._signal_waybar`), `test_cli.py`, `test_ipc.py`, `test_miner.py` (includes `test_distiller_offline` at line 463, uses `MemoryDistiller(memories_root=...)`), `test_waybar_config.py`. No `test_distiller.py` yet.
- Real data (2026-11-12): 8 PROJECT_MEMORY.md files, 22 sections; 17 of 22 contain the generic fallback directive. Used as evidence in GOALS.md, not as test input.

## Hazard Notes

- H1: Tests never use the real memories root. Every test passes `memories_root=tmp_path` (D6). A test that forgets this would write to `~/.claude-mined-memories`.
- H2: Tests never make network calls. Mock `distiller.call_llm_completion` in any test that passes `llm_endpoint`.
- H3: `xfail` tests are `strict=True`. When a goal lands and the test starts passing, it fails as XPASS. That is intended: the goal's task must remove the marker in the same change.
- H4: The SPEC rewrite must not re-introduce CLAUDE.md injection (G12 is pruned).
- H5: Do not run `make install-user`, `make systemd-install`, or `claudalizer watch`.

## Wave Table

| Wave | Task | Repo | Files (must edit) | Depends on | Parallel? |
| --- | --- | --- | --- | --- | --- |
| 1 | T5.1.1 Rewrite SPEC §3.2 and §4.2 to the current distiller | claudalizer | `planning/SPEC.md` | — | No |
| 2 | T5.2.1 Create `tests/test_distiller.py` (characterisation + strict xfail) | claudalizer | `tests/test_distiller.py` (new) | T5.1.1 | No |

Two tasks, one file each, no shared file, but T5.2.1 follows the spec wording from T5.1.1. Serial (D4).

## Task Specs

### T5.1.1 — Rewrite SPEC §3.2 and §4.2 to the current distiller

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: `planning/SPEC.md` (sections §3.2 and §4.2 only, plus the `tests/test_distiller.py` skeleton block at ~line 540 if it names functions that no longer exist)
  - Can create: none
- **Depends on:** none
- **Spec**
  1. §3.2 `distiller.py`: replace the "API Request Contract", "Fallback Mode", and "Memory Block Target Format" subsections with the current behaviour:
     - Two outputs per session: `memory.md` in `<memories_root>/<slug>/<session_id>/`, and an appended block in `<memories_root>/<slug>/PROJECT_MEMORY.md`.
     - Synthesis: optional LLM call (`call_llm_completion`, OpenAI-compatible, stdlib `urllib`) with the prompt from `build_synthesis_prompt`; if there is no endpoint or the call returns nothing, use `synthesize_offline_memory_block`.
     - Offline block format: the three sections (`### 1. Tool / Skill Friction`, `### 2. Blind Alleys & Discarded Spikes`, `### 3. Directives for CLAUDE.md`), in that order, under `# Mined Behavioral Memory for <slug>`.
     - PROJECT_MEMORY.md format: one section per session, headed `## Session <first 8 chars of session id> Distillation`, separated by `---`. Appended on every write today; the rebuild rule belongs to G18 and is written here as a requirement marked **(target, G18)**.
     - Directives: derived from errors (three patterns today); the fallback directive is marked **(target, G19)** for removal.
     - Blind-alleys and friction rules: current behaviour, with G20 and G21 changes marked **(target, G20)** and **(target, G21)**.
     - `distill_session` skips an existing `memory.md` unless `force` is true; `distill_all` walks slug and session directories under the root and can filter by slug.
     - Remove every reference to `.claude/CLAUDE.md` injection, `distillation_prompt.md`, and `call_openai_completion`, `build_distillation_prompt`, `append_to_claude_md`.
  2. §4.2 `test_distiller.py`: replace the three test bullets with a list that matches the tests T5.2.1 will write (one bullet per test name, each with the criterion it covers). Mark which tests are `xfail(strict=True)` and which goal they wait for.
  3. Do not touch §1, §2, §3.1, §3.3, §3.4, §4.1, §4.3, or §5 except where a sentence there names a removed function or CLAUDE.md injection.
  4. Do not change any code or tests.
- **Anchors:** `planning/SPEC.md`: `### **3.2 distiller.py`, `#### **API Request Contract**`, `#### **Fallback Mode**`, `#### **Memory Block Target Format**`, `### **4.2 Distillation & HTTP`. `claudalizer/distiller.py`: `def build_synthesis_prompt` (line 29), `def call_llm_completion` (line 89), `def synthesize_offline_memory_block` (line 126), `class MemoryDistiller` (line 191), `def _append_to_project_memory` (line 237).
- **Reference implementation:** the current code is the reference. Describe it; do not design new behaviour here.
- **Constraints (do not touch)**
  - Do not edit any file other than `planning/SPEC.md`.
  - Do not describe CLAUDE.md injection as current behaviour (G12 pruned, H4).
- **Acceptance (mechanical)**
  - `grep -c 'call_openai_completion\|build_distillation_prompt\|append_to_claude_md\|distillation_prompt.md' planning/SPEC.md` prints `0`.
  - `grep -c 'PROJECT_MEMORY' planning/SPEC.md` prints at least `3`.
  - `grep -c 'target, G18\|target, G19\|target, G20\|target, G21' planning/SPEC.md` prints at least `4`.
  - `make test` passes with the same count as the baseline (40 passed).
- **Commit:** `docs(planning): describe current distiller and PROJECT_MEMORY in SPEC` (planning-only, separate from T5.2.1)

### T5.2.1 — Create `tests/test_distiller.py`

- **Repo:** claudalizer
- **Files in scope**
  - Must edit: none
  - Can create: `tests/test_distiller.py`
  - May edit only if a fixture is required: `tests/conftest.py` (a fixture only; no change to the existing autouse fixture)
- **Depends on:** T5.1.1 (the test names and criteria come from the rewritten SPEC §4.2)
- **Spec**
  1. Imports: `from claudalizer.distiller import MemoryDistiller, build_synthesis_prompt, synthesize_offline_memory_block` and `import claudalizer.distiller as distiller_mod`. Use `pytest` and `monkeypatch`.
  2. Helper: `_write_dossier(root, slug, session_id, dossier)` writes `<root>/<slug>/<session_id>/dossier.json` (keys: `tool_errors`, `scratchpad_files`, `user_prompt` or the same keys `synthesize_offline_memory_block` reads; check the key names at distiller.py lines 126–135 before writing).
  3. Characterisation tests (must pass now):
     - `test_offline_block_has_three_sections_in_order` — the three `### N.` headings appear in order.
     - `test_distill_session_writes_memory_md_and_project_memory` — `memory.md` exists and `PROJECT_MEMORY.md` contains `## Session <id[:8]> Distillation`.
     - `test_distill_session_skips_existing_memory_without_force` — a second call without `force` returns the existing path and does not append again.
     - `test_llm_block_used_when_endpoint_returns_content` — monkeypatch `distiller_mod.call_llm_completion` to return `"LLM BLOCK"`; `memory.md` contains `LLM BLOCK`.
     - `test_offline_fallback_when_llm_returns_nothing` — monkeypatch to return `None`; `memory.md` contains `# Mined Behavioral Memory`.
     - `test_distill_all_respects_target_slug` — two slugs, `target_slug` limits output to one.
     - `test_python_error_maps_to_venv_directive` — a tool error with `No such file or directory` and `python` in the output yields the venv directive.
     - `test_synthesis_prompt_mentions_errors_and_scratchpads` — `build_synthesis_prompt` output contains the error command and a scratchpad path.
  4. Strict xfail tests (target behaviour, must be marked with the goal id):
     - `test_force_redistill_does_not_duplicate_project_section` — `@pytest.mark.xfail(strict=True, reason="G18: PROJECT_MEMORY rebuilt, not appended")`. Distill the same session twice with `force=True`; assert exactly one `## Session <id[:8]> Distillation` header.
     - `test_no_matching_error_shows_none_detected_not_fallback_directive` — `xfail(strict=True, reason="G19: generic fallback directive removed")`. Dossier with no tool errors; assert `"Maintain strict idempotency"` not in the output and `"None detected"` is in the directives section.
     - `test_test_runner_scratch_excluded_from_blind_alleys` — `xfail(strict=True, reason="G20: filter claudalizer test scratch")`. Dossier whose `scratchpad_files` are `g3-accept/lock` and `rewrite-check/projects/x.jsonl`; assert `"No ephemeral scratchpads recorded."` appears in the blind-alleys section.
     - `test_friction_line_shows_real_error_text` — `xfail(strict=True, reason="G21: real error text in friction lines")`. Dossier with a failing `pytest` tool error whose output is `FAILED tests/x.py::test_y - AssertionError`; assert that text appears in the friction section and that a bare `Exit code` line without error text does not.
  5. Every test uses `tmp_path` for `memories_root`. No test calls the real network or the real `~/.claude-mined-memories` (H1, H2).
  6. Do not edit `claudalizer/`. If a characterisation test fails because the code differs from the spec you just wrote, stop and report; do not change the code (H3 / escalation 4).
- **Anchors:** `claudalizer/distiller.py`: `def synthesize_offline_memory_block` (line 126; dossier keys at lines 128–129), `def build_synthesis_prompt` (line 29; keys at 34–35), `def call_llm_completion` (line 89; mock target), `class MemoryDistiller` (line 191), `def distill_session` (line 197), `def _append_to_project_memory` (line 237), `def distill_all` (line 247). `tests/test_miner.py`: `def test_distiller_offline` (line 463) as a style reference for the `MemoryDistiller(memories_root=...)` call.
- **Reference implementation:** `tests/test_miner.py::test_distiller_offline` (line 463). Same style, same `tmp_path` pattern.
- **Constraints (do not touch)**
  - Do not edit `tests/test_miner.py`.
  - Do not edit `claudalizer/distiller.py` or any other code file.
  - Do not assert on exact whole-file contents; assert on the criterion (headers, markers, phrases).
- **Acceptance (mechanical)**
  - `python -m pytest tests/test_distiller.py -q` exits 0. Expected: 8 passed, 4 xfailed.
  - `python -m pytest tests/test_distiller.py -q -rx` lists the four xfail reasons, each with its goal id (G18, G19, G20, G21).
  - `make test` exits 0. Expected: 40 + 8 = 48 passed, 4 xfailed.
  - `make lint` reports 12 findings, none new in `tests/test_distiller.py`.
- **Commit:** `test(distiller): cover current behaviour and mark G18–G21 targets xfail` (code-side test commit; SPEC is committed separately in T5.1.1)

## Verification at end of wave 2 (orchestrator, serial)

1. `make test`: 48 passed, 4 xfailed.
2. `make lint`: 12 findings, none new.
3. `git log --oneline 922db54..HEAD` shows one `docs(planning)` commit for T5.1.1 and one `test(distiller)` commit for T5.2.1, plus the planning commit for the plan and GOALS.md.
4. `git status` clean except the untracked `planning/tasks/` directory if any worker wrote a micro-TODO.
5. Report to the user: what the spec now says, the test counts, and that G18–G21 are next (in GOALS.md order).

## Escalation (from wave-orchestration)

1. A characterisation test fails against current code: stop. The spec was wrong or the test was wrong. Report and ask; do not change code.
2. An xfail test passes (XPASS strict): stop. Either a goal landed by accident or the test is wrong. Report.
3. Acceptance fails after one retry: re-run on a mid-tier model; never a third small-model attempt. (Inline execution, D4: the orchestrator itself stops and reports.)
4. A task needs an out-of-scope edit (for example `claudalizer/distiller.py`): stop and re-scope the spec in this file; do not widen scope ad hoc.
