# Worker Prompt Template, Orchestration 6 (`planning/PROMPT_TEMPLATE_6.md`)

Fill the slots from the task spec in `planning/EXECUTION_PLAN_6.md`, then give the result to a worker. Repo conventions: `AGENTS.md`. Commit discipline: `git-workflow-standards` and `conventional-commits`. Execution is inline (D5); this template is used only if the user later chooses spawned workers.

```markdown
You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from planning/EXECUTION_PLAN_6.md}}

## Repo conventions
- Read `AGENTS.md` first (Quick Start, Workflows, Never list).
- Targeted test command: {{targeted test command}}
- Full test command: `make test` (expect 48 passed, 4 xfailed before T6.1.1; 52 passed, 3 xfailed after).
- Lint: `make lint` reports 12 pre-existing findings. Add none.
- Commits follow `git-workflow-standards` and `conventional-commits`: subject line only, no trailers, no phase or wave numbers, no "Co-Authored-By".

## Ground rules (non-negotiable)
- NEVER make implementation changes before your plan is approved. Creating `planning/tasks/{{wave}}.{{id}}.todo.md` is allowed; commit it separately with `docs(planning):`.
- After approval, a focused local commit is part of the approved task. No pushes or other remote actions.
- NEVER touch files outside "Files in scope". If required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- Tests use `tmp_path` for every memories root. No network. Never touch `~/.claude-mined-memories` or `/tmp/claude-1000`.
- NEVER run `make install-user`, `make systemd-install`, or `claudalizer watch`.
- If a test fails twice for the same reason, stop and report. Do not thrash.

## [Worker] Analysis
Read: `AGENTS.md`; the anchors (search by name); `claudalizer/distiller.py` `_append_to_project_memory` only.

## [Worker] Micro-planning
Write `planning/tasks/{{wave}}.{{id}}.todo.md`:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] small, verifiable steps incl. explicit test steps (max 12)
  ## Notes       <facts discovered, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
Only after the orchestrator sends `APPROVED -- execute the plan as written.`:
Work the TODO in order, flipping `- [ ]` to `- [x]`. Match surrounding style. Run only the targeted tests in the spec. Commit the verified unit with a focused Conventional Commit.

## [Worker] Reporting
Append to `planning/STATE_6.md` under `## {{id}}` (15 lines max): status; files changed with line ranges; commit IDs; exact test commands with pass/fail/xfail counts; deviations (or "none"); gotchas.
```

## Slot values for orchestration 6

| Task | `{{wave}}` | `{{targeted test command}}` |
| --- | --- | --- |
| T6.1.1 | 1 | `python -m pytest tests/test_distiller.py -q -rx` (expect 12 passed, 3 xfailed), then `make test` |
| T6.2.1 | 2 | `grep` checks in the spec's Acceptance section, then `make test` |

## Escalation (from wave-orchestration)
1. Micro-plan off-spec twice: the orchestrator writes the micro-TODO and hands it to the worker as fixed input.
2. Acceptance fails after one retry: stop and report. Never a third attempt on a small model.
3. Malformed or missing report: one feedback message, one retry, then stop and report.
4. Out-of-scope edit needed: re-scope the spec in `EXECUTION_PLAN_6.md`; do not widen permissions ad hoc.
