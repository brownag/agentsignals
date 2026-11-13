# Execution Plan 9: Richer memory blocks: LLM endpoint default and session objective (`planning/EXECUTION_PLAN_9.md`)

Orchestration: 9
Source: user report (2026-11-12): memory blocks are sparse. 85% have empty directives; no session objective is written; no LLM endpoint is configured, so the richer path never runs.
Status: Draft for user approval. Not started. Not committed.
Starts after: orchestration 8 executed (`08e4f22`). Baseline `make test` 65 passed; lint 11 (pre-existing).
Base branch: `g5-g6-g7-g9`. Planning tracked (D3).

## Goal & Scope

**Goal (user's terms).** Memory blocks say what each session was for, and the LLM path works without extra flags when the local model is running.

**Exit criteria.**
- With `CLAUDALIZER_LLM_ENDPOINT` set, `claudalizer distill` and the scan's auto-distill call the LLM. Requests turn off model thinking, cap output at 1024 tokens, and wait up to 300 s. An empty reply is logged, and the offline block is used.
- The offline block includes an `**Objective:**` line taken from the session's first real request, so no block says nothing about purpose.
- `make test` passes. SPEC §3.2 describes both.

**In scope**
- `claudalizer/distiller.py`: `call_llm_completion` (payload, timeout, empty-reply warning); `synthesize_offline_memory_block` (Objective line).
- `claudalizer/cli.py`: resolve the endpoint and model from the environment when the flag is absent (distill, scan, watch).
- Tests: `tests/test_distiller.py` (new tests), `tests/test_cli.py` only if a test helper needs it.
- `planning/SPEC.md` §3.2 and §4.2.

**Out of scope**
- Running `claudalizer distill --force` on the real data. That is the user's run, after this plan lands.
- Changing the LLM prompt (`build_synthesis_prompt`, `DISTILLATION_SYSTEM_PROMPT`).
- Adding a fourth section to the block. The Objective is a header line, so the block still has three sections.
- Starting or configuring a model server.
- G22 (durable notes). Not touched.
- Pushes or other remote actions.

**Verbatim constraints**
- User decision: "1" = the endpoint comes from `CLAUDALIZER_LLM_ENDPOINT` by default; the flag still overrides it.
- Trial evidence (2026-11-12, scratch only): `http://localhost:8090/v1/chat/completions` (Qwen3.6-35B, llama-server) returns usable output in 12 s for a 26k-character prompt when `chat_template_kwargs.enable_thinking` is false and `max_tokens` is 1024. With the old settings (no thinking switch, 30 s timeout) it returned empty or timed out, and the distiller fell back silently.
- AGENTS.md: `make test` after changes; stdlib only; never modify `~/.claude-mined-memories` directly.

## Decision Log

| # | Date | Decision | Why | Source |
| --- | --- | --- | --- | --- |
| D1 | 2026-11-12 | Endpoint from `CLAUDALIZER_LLM_ENDPOINT` when the flag is absent. Model from `CLAUDALIZER_LLM_MODEL` (default `local`). The flag wins | User decision | User |
| D2 | 2026-11-12 | Payload adds `max_tokens: 1024` and `chat_template_kwargs: {"enable_thinking": false}`. Timeout default 300 s | Measured. Thinking consumed the whole budget. Other servers ignore unknown fields (judgment; Ollama and llama.cpp accept these) | Measured + judgment, flagged |
| D3 | 2026-11-12 | An empty or missing reply logs a warning naming the endpoint, then the offline block is used | Today this fallback is silent, which is how the 30 s failure went unnoticed | Judgment, flagged |
| D4 | 2026-11-12 | Objective = first user prompt with length at least 15 (the miner's `MIN_PROMPT_LENGTH`), truncated to 300 characters, on one line, as `**Objective:** ...` under the title. No prompt: `**Objective:** not captured.` | A header line keeps three sections, matching the LLM prompt. Judgment, flagged | Judgment, flagged |
| D5 | 2026-11-12 | The LLM path already receives the prompts through `build_synthesis_prompt`, so it needs no objective change | Avoids changing the prompt | Default |
| D6 | 2026-11-12 | Planning tracked (D3). Inline execution. Acceptance: `make test` green, lint at 11 pre-existing findings with none added | Same as orchestrations 5–8 | Default |
| D7 | 2026-11-12 | Three waves, serial: W1 LLM wiring (distiller + cli + tests); W2 Objective line (distiller + tests); W3 SPEC | Same function and test file | Default |

## Recon Log (facts)

- `claudalizer/distiller.py` `call_llm_completion` (line ~89): payload `{model, messages, temperature: 0.2}`; default `timeout=30.0`; returns `None` on exception, and `choices[0].message.content` otherwise (empty string possible).
- `distill_session` falls back to `synthesize_offline_memory_block` when the reply is empty or `None`.
- `claudalizer/cli.py`: `--llm-endpoint` on `scan` (line 258), `distill` (265), `watch` (274). Call sites pass `args.llm_endpoint` (lines 91, 105, 143).
- `synthesize_offline_memory_block` (line 136): header lines 144–145 (`# Mined Behavioral Memory`, `**Source Directory:**`), then a blank line, then `### 1. Tool / Skill Friction`.
- `MIN_PROMPT_LENGTH = 15` in `claudalizer/miner.py` line 24.
- Live server: port 8090 `llama-server` (Qwen3.6-35B-A3B Q4_K_S), `/v1/chat/completions` 200. Port 8080 is health-only (404 on chat). Ports 8003 (embeddings) and 8090 are the only llama-servers.
- Baseline: 65 passed, 11 lint findings.

## Hazard Notes

- H1: Tests mock `urllib.request.urlopen`. No test calls a real server or the real memories root.
- H2: Do not run `distill` or `scan` on the real data in this orchestration.
- H3: Do not change `build_synthesis_prompt` or `DISTILLATION_SYSTEM_PROMPT` (D5).
- H4: Env variables are read at call time, not import time, so tests can set them with `monkeypatch`.

## Wave Table

| Wave | Task | Files (must edit) | Depends on |
| --- | --- | --- | --- |
| 1 | T9.1.1 LLM wiring: payload, timeout, empty-reply warning, env defaults in CLI | `claudalizer/distiller.py`, `claudalizer/cli.py`, `tests/test_distiller.py`, `tests/test_cli.py` (helper only, if needed) | — |
| 2 | T9.2.1 Objective line in the offline block | `claudalizer/distiller.py`, `tests/test_distiller.py` | T9.1.1 |
| 3 | T9.3.1 SPEC §3.2 and §4.2 | `planning/SPEC.md` | T9.2.1 |

## Task Specs

### T9.1.1 — LLM wiring

- **Files in scope:** `claudalizer/distiller.py` (`call_llm_completion` only), `claudalizer/cli.py` (a resolver function plus its three call sites), `tests/test_distiller.py`, `tests/test_cli.py` (only if a test helper needs the new keyword).
- **Spec**
  1. In `call_llm_completion`, change the default `timeout` to `300.0`. Add to `payload`: `"max_tokens": 1024` and `"chat_template_kwargs": {"enable_thinking": False}`. Keep `temperature` 0.2.
  2. If the reply is missing or empty after `.strip()`, log a warning: `LLM endpoint {endpoint} returned no content; using offline block.` and return `None`.
  3. In `claudalizer/cli.py`, add `resolve_llm_settings(args) -> tuple[Optional[str], str]`: endpoint = `args.llm_endpoint` if set, else `os.environ.get("CLAUDALIZER_LLM_ENDPOINT")` or None; model = `os.environ.get("CLAUDALIZER_LLM_MODEL", "local")` when the flag `--llm-model` was not given explicitly (keep the existing `--llm-model` default of `llama3` as the explicit value; if it equals `llama3`, treat it as not given). Use it in handle_scan's auto-distill, handle_distill, and handle_watch's distill calls. Read env at call time.
  4. Tests in `tests/test_distiller.py`: (a) monkeypatch `urllib.request.urlopen` to capture the request body; assert `max_tokens == 1024`, `chat_template_kwargs == {"enable_thinking": False}`, and that the default timeout is 300. (b) A reply with empty content returns `None` and logs a warning containing the endpoint (use `caplog`). (c) `resolve_llm_settings` with `monkeypatch.setenv("CLAUDALIZER_LLM_ENDPOINT", ...)` and an args object with `llm_endpoint=None` returns that endpoint; with the flag set, the flag wins.
- **Anchors:** `call_llm_completion` (search by name); `payload = {` inside it; `def handle_distill`, `def handle_scan`, `def handle_watch` in `cli.py`.
- **Constraints:** do not change `build_synthesis_prompt`, `DISTILLATION_SYSTEM_PROMPT`, or `synthesize_offline_memory_block`.
- **Acceptance:** `python -m pytest tests/test_distiller.py tests/test_cli.py -q` passes. `make test` passes with 65 + 3 = 68 passed. `make lint` 11 findings, none new.
- **Commit:** `feat(distiller): default LLM endpoint from env and turn off thinking for local models`

### T9.2.1 — Objective line

- **Files in scope:** `claudalizer/distiller.py` (`synthesize_offline_memory_block` only), `tests/test_distiller.py`.
- **Spec**
  1. Read `user_prompts` from the dossier. Take the first prompt with `len(p.strip()) >= 15` (same rule as `MIN_PROMPT_LENGTH`). Collapse whitespace to single spaces; truncate to 300 characters, adding `…` if cut.
  2. Insert after the `**Source Directory:**` line and before `### 1.`: `**Objective:** <text>`. If there is no such prompt: `**Objective:** not captured.`
  3. Do not add or rename sections. The block still has three `###` sections.
  4. Tests: (a) a dossier whose first prompt is `"hi"` and second is `"Build the scan report and check it"` gives that second text; (b) a 400-character prompt is truncated to 300 characters plus `…`; (c) no prompts gives `not captured`.
- **Anchors:** `synthesize_offline_memory_block` (search by name); the `**Source Directory:**` line in its `lines = [` list; `user_prompts` in the dossier.
- **Constraints:** do not change `build_synthesis_prompt` or the friction, blind-alleys, or directives blocks.
- **Acceptance:** `python -m pytest tests/test_distiller.py -q` passes with 3 more tests. `make test` passes with 71 passed. `make lint` 11, none new.
- **Commit:** `feat(distiller): add session objective line to offline memory block`

### T9.3.1 — SPEC

- **Files in scope:** `planning/SPEC.md` (§3.2 "Synthesis" and "Offline block format"; §4.2 bullets for the new tests).
- **Spec:** describe the env defaults (`CLAUDALIZER_LLM_ENDPOINT`, `CLAUDALIZER_LLM_MODEL`), the request settings (`max_tokens` 1024, thinking off, 300 s timeout), the empty-reply warning, and the Objective line. List the new test names. Do not edit other sections.
- **Acceptance:** `grep -c 'CLAUDALIZER_LLM_ENDPOINT' planning/SPEC.md` ≥ 1; `grep -c 'Objective' planning/SPEC.md` ≥ 1; `make test` 71 passed.
- **Commit:** `docs(planning): describe LLM env defaults and objective line in SPEC`

## Verification (orchestrator, serial)

1. `make test`: 71 passed. `make lint`: 11, none new.
2. Scratch check only: with `CLAUDALIZER_LLM_ENDPOINT` set to port 8090 and a copy of one dossier under `$SCRATCH`, `claudalizer --memories-root $SCRATCH distill --force` writes a block with an Objective line and non-empty directives.
3. Report to the user. The real run is theirs: `CLAUDALIZER_LLM_ENDPOINT=http://localhost:8090/v1/chat/completions claudalizer distill --force`. Expect about 12 s per session, so about 25 minutes for 131 sessions.

## Escalation

1. A test fails for a reason other than the code: stop and report.
2. The LLM is unreachable in verification: report it; the code path is still covered by mocks.
3. An acceptance count is off: stop and report; do not widen the change.
