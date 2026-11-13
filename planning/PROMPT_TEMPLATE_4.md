# Worker Prompt Template, Orchestration 4 (`planning/PROMPT_TEMPLATE_4.md`)

Fill the slots from the task spec in `planning/EXECUTION_PLAN_4.md`, then give the result to a worker. Repo conventions: `AGENTS.md`. Commit discipline: `git-workflow-standards` (`/home/andrew/.claude/skills/git-workflow-standards/SKILL.md`) and `conventional-commits`.

```markdown
You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from planning/EXECUTION_PLAN_4.md}}

## Repo conventions
- Read `AGENTS.md` first (Quick Start, Workflows, Never list).
- Test command for this task: {{targeted test command}}
- Full test command: `make test`. Lint: `make lint` (reports 12 pre-existing findings; check that you add none).
- Commits follow `git-workflow-standards` and `conventional-commits`: subject line only, no body needed, no trailers, no phase or wave numbers, no "Co-Authored-By".

## Ground rules (non-negotiable)
- NEVER make implementation changes or run implementation state-changing commands before your plan is approved. Creating or updating the scoped micro-TODO at `planning/tasks/{{wave}}.{{id}}.todo.md` is allowed before approval; commit it separately with `docs(planning):`.
- After approval, a focused local commit is part of executing the approved task. This does not authorize pushes, pull requests, comments, remote changes, or other outward-facing actions.
- NEVER touch files outside "Files in scope". If required, STOP and report.
- NEVER go off-plan; discovered work goes in "## Discovered" and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5) in your plan report.
- NEVER run `pkill`, `killall`, `make install`, `make install-user`, `make systemd-install`, or `claudalizer watch`. Signal probe processes by PID only.
- NEVER touch the real Waybar, the real Sway session, `/tmp/claude-1000`, or `/tmp/claudalizer_status.json`.
- If a test fails twice for the same reason, stop and report. Do not thrash.

## [Worker] Analysis
Read: `AGENTS.md`; the task's anchors (grep, do not read whole files); the reference implementation named in the spec; `planning/STATE_4.md` reports of your dependency tasks.

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
Append to `planning/STATE_4.md` under `## {{id}}` (15 lines max): status; files changed with line ranges; code commit IDs; exact test commands with pass/fail counts; deviations from the approved plan (or "none"); gotchas for dependent tasks. For T4.1.1, include the exact `RESULT:` lines from the spec.
```

## Slot values for orchestration 4

| Task | `{{wave}}` | `{{targeted test command}}` |
| --- | --- | --- |
| T4.1.1 | 1 | none (probe). Acceptance: the RESULT lines in `planning/STATE_4.md` plus `pgrep -a -f 'g14-probe\|wb-probe'` printing nothing |
| T4.2.1 | 2 | `make test` (no code change) plus the grep checks in the spec |
| T4.2.2 | 2 | `python -m pytest tests/test_ipc.py -q` then `make test` |

## Escalation (from wave-orchestration)
1. Micro-plan off-spec twice: orchestrator writes the micro-TODO and hands it to the worker as fixed input.
2. Acceptance fails after one retry (feed back `FAILED VERIFICATION: ...`): stop the worker and re-run on a mid-tier model. Never a third small-model attempt.
3. Malformed or missing report: send one feedback message, allow one retry, then re-run on a mid-tier model.
4. Worker needs out-of-scope edits: re-scope the spec in `EXECUTION_PLAN_4.md`; do not widen permissions ad hoc.
5. Probe `inconclusive`: stop and report to the user (EXECUTION_PLAN_4.md escalation 1).
