# Worker Prompt Template 1 (`planning/PROMPT_TEMPLATE_1.md`)

Orchestration 1. Fill the slots `{{id}}`, `{{title}}`, and `{{task spec verbatim}}` from the matching task in `planning/EXECUTION_PLAN_1.md`. Paste the spec unchanged.

---

You are implementing exactly one scoped task, supervised by an orchestrator that reviews your plan before you may write code.

## Task {{id}}: {{title}}

{{task spec verbatim}}

## Repository conventions

- Project conventions: `AGENTS.md` (repo root). Read its "Find Things", "Workflows", and "System Boundaries" sections.
- Targeted tests only: `pytest tests/test_miner.py -q -k <name>`. Do not run `make test`, `make check`, or any full suite. The orchestrator owns full-suite runs.
- Lint for files you touched: `ruff check <file>`. Compare with baseline in `planning/STATE_1.md`. Do not fix unrelated findings.
- Never read or write `/tmp/claude-1000` or `~/.claude-mined-memories`. Tests use `tmp_path`.
- Do not change `MAX_SCRATCHPAD_FILE_BYTES`, the settle window, or the lock timeout. These are Ask First per AGENTS.md.

## Commit discipline

Follow `git-workflow-standards` (`/home/andrew/.claude/skills/git-workflow-standards/SKILL.md`) and `conventional-commits`:

- Conventional Commit format, subject line only (body optional).
- One logical unit per commit. Code commits and planning commits stay separate.
- No phase, wave, or task numbers in the subject. Describe the change.
- Do not add `Co-Authored-By` or any attribution trailer.
- Do not push, open PRs, or run any remote action.

## Ground rules (non-negotiable)

- NEVER make implementation changes or run implementation state-changing commands before your plan is approved. Creating or updating the scoped micro-TODO and other planning artifacts required for review is allowed before approval.
- After approval, a focused local commit is part of executing the approved task. This does not authorize pushes, pull requests, comments, remote changes, or other outward-facing actions.
- NEVER touch files outside "Files in scope". If required, STOP and report.
- NEVER go off-plan. Discovered work goes in "## Discovered" in your report and waits.
- NEVER assume. Resolve unknowns by reading code in Analysis. Anything still ambiguous becomes numbered questions (max 5) in your plan report.
- If a test fails twice for the same reason, stop and report. Do not thrash.

## [Worker] Analysis

Read: `AGENTS.md`; the task spec above; `planning/STATE_1.md` reports of your dependency tasks; the grep anchors in the spec; the named reference implementation. Do not read whole large files. Use the anchors.

## [Worker] Micro-planning

Write `planning/tasks/{{id}}.todo.md`:

```
# {{id}} -- {{title}}
## Goal        <one sentence>
## TODO items  - [ ] small, verifiable steps incl. explicit test steps (max 12)
## Notes       <facts discovered in Analysis, constraints honored, risks>
## Questions   <numbered, max 5, omit if none>
```

Output the file contents as your report and END YOUR TURN.

## [Worker] Execution

Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match surrounding code style. Run only the targeted tests named in the spec. Commit each verified, reviewable logical unit locally. Keep planning artifact updates out of code commits.

## [Worker] Reporting

Append to `planning/STATE_1.md` under `## {{id}}` (15 lines max):

- status
- files changed with line ranges
- code commit IDs
- exact test commands with pass/fail counts
- lint result for touched files
- deviations from the approved plan (or "none")
- gotchas for dependent tasks

## Orchestrator gate messages

- Plan approval (sent via SendMessage): `APPROVED -- execute the plan as written. <answers to questions>`
- Revision: `REVISE -- <specific in-scope correction>`
- Escalation: follow the ladder in wave-orchestration (off-spec twice → orchestrator writes the TODO; acceptance fails after one retry → mid-tier model; malformed report → one retry; out-of-scope need → re-scope the spec).
