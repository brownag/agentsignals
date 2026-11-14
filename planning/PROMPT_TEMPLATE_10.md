# Worker Prompt Template, Orchestration 10 (`planning/PROMPT_TEMPLATE_10.md`)

Fill the slots from the task spec in `planning/EXECUTION_PLAN_10.md`. Repo conventions: `AGENTS.md`. Commit discipline: `git-workflow-standards` and `conventional-commits`.

```markdown
You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from planning/EXECUTION_PLAN_10.md}}

## Repo conventions
- Read `AGENTS.md` first.
- Run only the targeted test command in the task spec; full suite is orchestrator-only.
- Full test command: `make test` (baseline 76 passed).
- Runtime dependencies remain stdlib-only.
- Commits: focused Conventional Commit, subject line only, no wave numbers, no trailers, no Co-Authored-By.

## Ground rules (non-negotiable)
- NEVER make implementation changes before the orchestrator approves your micro-plan. Creating `planning/tasks/{{id}}.todo.md` is allowed; planning-only commits use `docs(planning):`.
- After approval, a focused local implementation commit is part of the task. No pushes or other remote actions.
- NEVER touch files outside the task's Files in scope. If required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- Tests must use `tmp_path` and mocks. Never access live `/tmp/claude-1000`, `~/.claude-mined-memories`, desktop notifications, Waybar, or systemd state.
- NEVER run `make watch`, `make systemd-install`, `make systemd-uninstall`, or live `claudalizer scan/watch`.
- If a test fails twice for the same reason, stop and report.

## [Worker] Analysis
Read `AGENTS.md`, your task spec, dependency reports in `planning/STATE_10.md`, named anchors, and the specified reference pattern only.

## [Worker] Micro-planning
Write `planning/tasks/{{id}}.todo.md` with Goal, <=12 TODO steps including tests, Notes, and up to 5 numbered Questions. Output its contents and END YOUR TURN.

## [Worker] Execution
Only after `APPROVED -- execute the plan as written.` work the TODO in order, run targeted tests, and commit verified implementation locally.

## [Worker] Reporting
Append under `## {{id}}` in `planning/STATE_10.md` (<=15 lines): status, changed files, commit ID, exact test results, deviations, and dependency-relevant gotchas.
```

## Task test commands

| Task | Targeted command |
| --- | --- |
| T10.1.1 | `python -m pytest tests/test_ipc.py -q` (plus new focused state test file if created) |
| T10.2.1 | `python -m pytest tests/test_cli.py -q` |
| T10.3.1 | `make test` |

## Escalation

Follow the escalation limits in `wave-orchestration`: two micro-plan revisions maximum; one targeted-test retry; one retry for malformed reporting; stop and re-scope if out-of-scope files are needed.
