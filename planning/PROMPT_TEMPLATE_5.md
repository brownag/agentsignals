# Worker Prompt Template, Orchestration 5 (`planning/PROMPT_TEMPLATE_5.md`)

Fill the slots from the task spec in `planning/EXECUTION_PLAN_5.md`, then give the result to a worker. Repo conventions: `AGENTS.md`. Commit discipline: `git-workflow-standards` (`/home/andrew/.claude/skills/git-workflow-standards/SKILL.md`) and `conventional-commits`. Execution is inline (D4); this template is used only if the user later chooses spawned workers.

```markdown
You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from planning/EXECUTION_PLAN_5.md}}

## Repo conventions
- Read `AGENTS.md` first (Quick Start, Workflows, Never list).
- Test command for this task: {{targeted test command}}
- Full test command: `make test` (expect 40 passed before T5.2.1; 48 passed and 4 xfailed after).
- Lint: `make lint` reports 12 pre-existing findings. Add none.
- Commits follow `git-workflow-standards` and `conventional-commits`: subject line only, no body needed, no trailers, no phase or wave numbers, no "Co-Authored-By".

## Ground rules (non-negotiable)
- NEVER make implementation changes before your plan is approved. Creating or updating `planning/tasks/{{wave}}.{{id}}.todo.md` is allowed before approval; commit it separately with `docs(planning):`.
- After approval, a focused local commit is part of executing the approved task. This does not authorize pushes, pull requests, comments, or other remote actions.
- NEVER touch files outside "Files in scope". If required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER assume: resolve unknowns by reading code. Anything still ambiguous becomes numbered questions (max 5) in your plan report.
- Tests use `tmp_path` for every memories root (H1). No test may call the network (H2) or touch `~/.claude-mined-memories` or `/tmp/claude-1000`.
- NEVER run `make install-user`, `make systemd-install`, or `claudalizer watch` (H5).
- If a test fails twice for the same reason, stop and report. Do not thrash.

## [Worker] Analysis
Read: `AGENTS.md`; the task's anchors (grep, do not read whole files); the reference implementation named in the spec; `planning/STATE_5.md` reports of your dependency tasks.

## [Worker] Micro-planning
Write `planning/tasks/{{wave}}.{{id}}.todo.md`:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] small, verifiable steps incl. explicit test steps (max 12)
  ## Notes       <facts discovered in Analysis, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
Only after the orchestrator sends `APPROVED -- execute the plan as written.`:
Work the TODO strictly in order, flipping `- [ ]` to `- [x]`. Match surrounding code style. Run only the targeted tests in the spec. Commit the verified logical unit locally with a focused Conventional Commit. Keep planning artifact updates out of code commits.

## [Worker] Reporting
Append to `planning/STATE_5.md` under `## {{id}}` (15 lines max): status; files changed with line ranges; code commit IDs; exact test commands with pass/fail/xfail counts; deviations from the approved plan (or "none"); gotchas for dependent tasks.
```

## Slot values for orchestration 5

| Task | `{{wave}}` | `{{targeted test command}}` |
| --- | --- | --- |
| T5.1.1 | 1 | `grep` checks in the spec's Acceptance section, plus `make test` (40 passed) |
| T5.2.1 | 2 | `python -m pytest tests/test_distiller.py -q -rx` (expect 8 passed, 4 xfailed), then `make test` |

## Escalation (from wave-orchestration)
1. Micro-plan off-spec twice: the orchestrator writes the micro-TODO and hands it to the worker as fixed input.
2. Acceptance fails after one retry (feed back `FAILED VERIFICATION: ...`): stop the worker and re-run on a mid-tier model. Never a third small-model attempt.
3. Malformed or missing report: send one feedback message, allow one retry, then re-run on a mid-tier model.
4. Worker needs out-of-scope edits: re-scope the spec in `EXECUTION_PLAN_5.md`; do not widen permissions ad hoc.
5. A characterisation test fails against current code, or an xfail test XPASSes: stop and report (EXECUTION_PLAN_5.md escalation 1–2).
