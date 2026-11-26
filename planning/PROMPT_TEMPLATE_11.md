# Worker Prompt Template, Orchestration 11 (`planning/PROMPT_TEMPLATE_11.md`)

Fill the slots from the task spec in `planning/EXECUTION_PLAN_11.md`. Repo conventions: `AGENTS.md`. Commit discipline: `git-workflow-standards` (`../../.claude/skills/git-workflow-standards/SKILL.md`) and `conventional-commits`.

```markdown
You are implementing exactly one scoped task, supervised by an orchestrator
that reviews your plan before you may write code.

## Task {{id}}: {{title}}
{{task spec verbatim from planning/EXECUTION_PLAN_11.md}}

## Repo conventions
- Read `AGENTS.md` first, then SPEC sections named in your spec (use grep anchors; do not read SPEC.md whole).
- Run only the targeted test command in the task spec, plus `ruff check` on your files. The full suite (`make check`) is orchestrator-only.
- Baseline before this orchestration: `make check`, 96 passed.
- Runtime dependencies stay stdlib-only (`sqlite3` is stdlib).
- Commits: focused Conventional Commit, subject line only, no wave or task numbers, no trailers, no Co-Authored-By. Use the subject in your task spec unless the work changed.

## Ground rules (non-negotiable)
- NEVER make implementation changes before the orchestrator approves your micro-plan. Creating `planning/tasks/{{id}}.todo.md` is allowed; planning-only commits use `docs(planning):`.
- After approval, a focused local implementation commit is part of the task. No pushes, pull requests or other remote actions.
- NEVER touch files outside the task's Files in scope. If required, STOP and report.
- NEVER go off-plan; discovered work goes in `## Discovered` and waits.
- NEVER assume: resolve unknowns by reading code in Analysis; anything still ambiguous becomes numbered questions (max 5).
- Tests use `tmp_path` and the fixture in `tests/opencode_fixture.py`. NEVER open `~/.local/share/opencode/opencode.db`, `/tmp/claude-1000`, or `~/.claude-mined-memories`.
- NEVER write to any SQLite database except fixture databases under `tmp_path`.
- NEVER run `make scan`, `make watch`, `make systemd-install`, `make systemd-uninstall`, or live `claudalizer scan/watch`.
- If a test fails twice for the same reason, stop and report -- do not thrash.

## [Worker] Analysis
Read: `AGENTS.md`; your task spec; reports of your dependency tasks in `planning/STATE_11.md`; the grep anchors; the named reference implementation.

## [Worker] Micro-planning
Write planning/tasks/{{id}}.todo.md:
  # {{id}} -- {{title}}
  ## Goal        <one sentence>
  ## TODO items  - [ ] small, verifiable steps incl. explicit test steps (<=12)
  ## Notes       <facts discovered in Analysis, constraints honored, risks>
  ## Questions   <numbered, max 5, omit if none>
Output the file contents as your report and END YOUR TURN.

## [Worker] Execution
Only after `APPROVED -- execute the plan as written.` work the TODO strictly in order, flipping - [ ] to - [x]. Match surrounding code style. Run only the targeted tests. Commit verified implementation locally (in your worktree if you have one). Keep planning artifact updates out of code commits.

## [Worker] Reporting
Append to /home/andrew/AI/claudalizer/planning/STATE_11.md (main checkout) under ## {{id}} (<=15 lines): status; files changed with line ranges; code commit IDs; exact test commands + pass/fail counts; deviations from the approved plan (or "none"); gotchas for dependent tasks.
```

## Task test commands

| Task | Targeted command |
| --- | --- |
| T11.1.1 | `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` |
| T11.1.2 | `python -m pytest tests/test_opencode_fixture.py -q` |
| T11.2.1 | `python -m pytest tests/test_miner.py tests/test_scan_report.py tests/test_cli.py tests/test_source_core.py -q` |
| T11.2.2 | `python -m pytest tests/test_opencode_source.py -q` |
| T11.2.3 | `python -m pytest tests/test_opencode_schema.py -q` |
| T11.3.1 | `python -m pytest tests/test_opencode_source.py -q` |
| T11.4.1 | `python -m pytest tests/test_opencode_source.py tests/test_opencode_schema.py tests/test_source_core.py -q` |
| T11.5.1 | `python -m pytest tests/test_cli.py -q` |
| T11.5.2 | `git diff --check && make test` |

## Escalation

Follow `wave-orchestration`'s limits:
- A micro-plan that is off-spec twice: the orchestrator writes the micro-plan.
- After a failed verification (`FAILED VERIFICATION: ...`), allow one retry. Then re-run the task on Opus. Never make a third Sonnet attempt.
- A malformed report gets feedback and one retry. Then the task re-runs on Opus.
- If out-of-scope files are needed, STOP. The orchestrator re-scopes the task spec in `EXECUTION_PLAN_11.md`.

## Worktree note

If you run in a git worktree, commit code there, but append your report to the main checkout's `/home/andrew/AI/claudalizer/planning/STATE_11.md`, not the worktree copy.
