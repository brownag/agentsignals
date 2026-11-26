"""tests/test_distiller.py - Tests for agentsignals/distiller.py (SPEC §3.2, §4.2).

Characterisation tests pin behaviour that is correct today. Strict xfail tests describe
target behaviour owned by goals G18-G21; each one starts passing when its goal lands, and
must then have its marker removed in the same change.

Every test uses tmp_path for the memories root and never makes a network call.
"""

import json


import agentsignals.distiller as distiller_mod
from agentsignals.distiller import MemoryDistiller, build_synthesis_prompt, frame_llm_block


EP = "http://127.0.0.1:9/v1"
LLM_SECTIONS = "### 1. Tool / Skill Friction\n- None.\n\n### 2. Blind Alleys & Discarded Spikes\n- None.\n\n### 3. Directives for CLAUDE.md\n- None.\n"



def _write_dossier(root, slug, session_id, dossier):
    sess_dir = root / slug / session_id
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    return sess_dir


def _dossier(slug="-home-andrew-AI-demo", session_id="abcdef12-3456", **overrides):
    base = {
        "slug": slug,
        "session_id": session_id,
        "decoded_path": "/home/andrew/AI/demo",
        "user_prompts": ["Fix the build"],
        "tool_errors": [],
        "scratchpad_files": [],
    }
    base.update(overrides)
    return base


def _section(text, heading):
    """Return the text under a '### N. ...' heading, up to the next '### ' heading."""
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = rest.find("\n### ")
    return rest if end == -1 else rest[:end]


# --- Characterisation tests (must pass on current code) ----------------------------------




def test_distill_session_writes_memory_md_and_project_memory(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))

    res = MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)

    assert res is not None and res.exists()
    assert res.name == "memory.md"
    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Session abcdef12 Distillation" in project


def test_distill_session_skips_existing_memory_without_force(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)

    first = distiller.distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)
    project_after_first = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    second = distiller.distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)

    assert second == first
    assert (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8") == project_after_first


def test_llm_block_used_when_endpoint_returns_content(tmp_path, monkeypatch, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: "LLM BLOCK")

    res = MemoryDistiller(memories_root=root).distill_session(
        "-slug-a", "abcdef12-3456", llm_endpoint="http://127.0.0.1:9/v1"
    )

    assert "LLM BLOCK" in res.read_text(encoding="utf-8")


def test_no_memory_written_when_llm_returns_nothing(tmp_path, monkeypatch, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: None)

    res = MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)

    assert res is None
    assert not (root / "-slug-a" / "abcdef12-3456" / "memory.md").exists()
    assert not (root / "-slug-a" / "PROJECT_MEMORY.md").exists()


def test_failed_llm_keeps_existing_memory_on_force(tmp_path, monkeypatch, fake_llm):
    root = tmp_path / "memories"
    sess = _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    (sess / "memory.md").write_text("old memory\n", encoding="utf-8")
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: None)

    res = MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP, force=True)

    assert res is None
    assert (sess / "memory.md").read_text(encoding="utf-8") == "old memory\n"


def test_no_endpoint_writes_nothing_and_makes_no_call(tmp_path, monkeypatch):
    root = tmp_path / "memories"
    sess = _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    calls = []
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: calls.append(a) or "X")

    assert MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456", force=True) is None
    assert MemoryDistiller(memories_root=root).distill_all(force=True) == []
    assert calls == []
    assert not (sess / "memory.md").exists()


def test_distill_all_respects_target_slug(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "sess-a-0001", _dossier(slug="-slug-a", session_id="sess-a-0001"))
    _write_dossier(root, "-slug-b", "sess-b-0001", _dossier(slug="-slug-b", session_id="sess-b-0001"))

    out = MemoryDistiller(memories_root=root).distill_all(target_slug="-slug-a", llm_endpoint=EP)

    assert len(out) == 1
    assert "-slug-a" in str(out[0])
    assert not (root / "-slug-b" / "PROJECT_MEMORY.md").exists()




def test_synthesis_prompt_mentions_errors_and_scratchpads():
    dossier = _dossier(
        tool_errors=[
            {
                "tool_name": "Bash",
                "command_or_input": "make test",
                "error_output": "Exit code 2",
                "exit_code": 2,
            }
        ],
        scratchpad_files=["probe/repro.sh"],
    )
    prompt = build_synthesis_prompt(dossier)
    assert "make test" in prompt
    assert "probe/repro.sh" in prompt


# --- Strict xfail: target behaviour owned by G18-G21 -------------------------------------


def test_force_redistill_does_not_duplicate_project_section(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)

    distiller.distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)
    distiller.distill_session("-slug-a", "abcdef12-3456", force=True, llm_endpoint=EP)

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.count("## Session abcdef12 Distillation") == 1


def test_rebuild_changes_only_the_redistilled_session_text(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "aaaa1111-0001", _dossier(slug="-slug-a", session_id="aaaa1111-0001", scan_timestamp="2026-01-01"))
    _write_dossier(root, "-slug-a", "bbbb2222-0002", _dossier(slug="-slug-a", session_id="bbbb2222-0002", scan_timestamp="2026-01-02"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "aaaa1111-0001", llm_endpoint=EP)
    distiller.distill_session("-slug-a", "bbbb2222-0002", llm_endpoint=EP)

    dossier_a = _dossier(
        slug="-slug-a",
        session_id="aaaa1111-0001",
        scan_timestamp="2026-01-01",
        tool_errors=[{"tool_name": "Bash", "command_or_input": "make NEWA", "error_output": "Error: NEWA failed", "exit_code": 2}],
    )
    (root / "-slug-a" / "aaaa1111-0001" / "dossier.json").write_text(json.dumps(dossier_a), encoding="utf-8")
    distiller.distill_session("-slug-a", "aaaa1111-0001", force=True, llm_endpoint=EP)

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.count("make NEWA") == 1
    b_text = (root / "-slug-a" / "bbbb2222-0002" / "memory.md").read_text(encoding="utf-8")
    assert b_text in project
    assert project.index("## Session aaaa1111") < project.index("## Session bbbb2222")


def test_rebuild_orders_sessions_by_scan_timestamp(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "zzzz0000-0001", _dossier(slug="-slug-a", session_id="zzzz0000-0001", scan_timestamp="2026-01-02"))
    _write_dossier(root, "-slug-a", "aaaa0000-0002", _dossier(slug="-slug-a", session_id="aaaa0000-0002", scan_timestamp="2026-01-01"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "zzzz0000-0001", llm_endpoint=EP)
    distiller.distill_session("-slug-a", "aaaa0000-0002", llm_endpoint=EP)

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.index("## Session aaaa0000") < project.index("## Session zzzz0000")


def test_rebuild_skips_session_without_memory_md(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    _write_dossier(root, "-slug-a", "nomemo00-0001", _dossier(slug="-slug-a", session_id="nomemo00-0001"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)

    project =(root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Session nomemo00" not in project
    assert "## Session abcdef12" in project


def test_rebuild_is_idempotent(tmp_path, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)
    path = root / "-slug-a" / "PROJECT_MEMORY.md"
    first = path.read_bytes()

    distiller.distill_session("-slug-a", "abcdef12-3456", force=True, llm_endpoint=EP)

    assert path.read_bytes() == first


def test_rebuild_discards_hand_edits_outside_session_files(tmp_path, fake_llm):
    root = tmp_path / "memories"
    proj = root / "-slug-a"
    proj.mkdir(parents=True)
    (proj / "PROJECT_MEMORY.md").write_text("hand notes\n", encoding="utf-8")
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))

    MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456", llm_endpoint=EP)

    project = (proj / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "hand notes" not in project
    assert "## Session abcdef12 Distillation" in project














# --- LLM request settings and endpoint defaults (orchestration 9, T9.1.1) ----------------


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_llm_request_turns_off_thinking_and_caps_output(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": "BLOCK TEXT"}}]}).encode())

    monkeypatch.setattr(distiller_mod.urllib.request, "urlopen", fake_urlopen)
    out = distiller_mod.call_llm_completion("prompt", endpoint="http://127.0.0.1:9/v1/chat/completions", model="local")

    assert out == "BLOCK TEXT"
    assert captured["body"]["max_tokens"] == 1024
    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert captured["timeout"] == 300.0


def test_empty_llm_reply_returns_none_and_warns(monkeypatch, caplog):
    def fake_urlopen(req, timeout=None):
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": ""}}]}).encode())

    monkeypatch.setattr(distiller_mod.urllib.request, "urlopen", fake_urlopen)
    with caplog.at_level("WARNING"):
        out = distiller_mod.call_llm_completion("prompt", endpoint="http://127.0.0.1:9/v1/chat/completions")

    assert out is None
    assert "returned no content" in caplog.text
    assert "http://127.0.0.1:9/v1/chat/completions" in caplog.text


def test_resolve_llm_settings_uses_environment_when_flag_absent(monkeypatch):
    import argparse
    from agentsignals.cli import resolve_llm_settings

    monkeypatch.setenv("AGENTSIGNALS_LLM_ENDPOINT", "http://127.0.0.1:8090/v1/chat/completions")
    monkeypatch.delenv("AGENTSIGNALS_LLM_MODEL", raising=False)
    args = argparse.Namespace(llm_endpoint=None, llm_model="llama3")

    assert resolve_llm_settings(args) == ("http://127.0.0.1:8090/v1/chat/completions", "local")


def test_resolve_llm_settings_flag_wins_over_environment(monkeypatch):
    import argparse
    from agentsignals.cli import resolve_llm_settings

    monkeypatch.setenv("AGENTSIGNALS_LLM_ENDPOINT", "http://127.0.0.1:8090/v1/chat/completions")
    args = argparse.Namespace(llm_endpoint="http://127.0.0.1:9999/v1/chat/completions", llm_model="mymodel")

    assert resolve_llm_settings(args) == ("http://127.0.0.1:9999/v1/chat/completions", "mymodel")


def test_resolve_llm_settings_no_endpoint_is_none(monkeypatch):
    import argparse
    from agentsignals.cli import resolve_llm_settings

    monkeypatch.delenv("AGENTSIGNALS_LLM_ENDPOINT", raising=False)
    args = argparse.Namespace(llm_endpoint=None, llm_model="llama3")

    assert resolve_llm_settings(args)[0] is None


# --- Session objective line (orchestration 9, T9.2.1) -------------


def test_objective_is_first_real_request():
    block = frame_llm_block(_dossier(user_prompts=["hi", "Build the scan report and check it"]), LLM_SECTIONS)
    assert "**Objective:** Build the scan report and check it" in block


def test_objective_truncated_to_300_chars_with_ellipsis():
    long_prompt = "word " * 100  # 500 characters
    block = frame_llm_block(_dossier(user_prompts=[long_prompt]), LLM_SECTIONS)
    line = next(text_line for text_line in block.splitlines() if text_line.startswith("**Objective:**"))
    text = line[len("**Objective:** "):]
    assert text.endswith("…")
    assert len(text) == 301


def test_objective_not_captured_when_no_prompts():
    block = frame_llm_block(_dossier(user_prompts=[]), LLM_SECTIONS)
    assert "**Objective:** not captured." in block
    assert block.count("### ") == 3


def test_objective_unwraps_slash_command_and_skips_bare_ones():
    prompts = [
        "<command-name>/clear</command-name>\n<command-message>clear</command-message>\n<command-args></command-args>",
        "<command-message>wave-orchestration</command-message>\n<command-name>/wave-orchestration</command-name>\n<command-args>run plan 11</command-args>",
    ]
    block = frame_llm_block(_dossier(user_prompts=prompts), LLM_SECTIONS)
    assert "**Objective:** /wave-orchestration run plan 11" in block


# --- LLM blocks carry the title and objective (orchestration 10) ------------------------


def test_llm_block_gets_title_and_objective(tmp_path, monkeypatch, fake_llm):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a", user_prompts=["Ship the memory report today"]))
    llm_text = "### 1. Tool / Skill Friction\n- None detected.\n\n### 2. Blind Alleys & Discarded Spikes\n- None.\n\n### 3. Directives for CLAUDE.md\n- Check the report.\n"
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: llm_text)

    res = MemoryDistiller(memories_root=root).distill_session(
        "-slug-a", "abcdef12-3456", llm_endpoint="http://127.0.0.1:9/v1"
    )

    text = res.read_text(encoding="utf-8")
    assert text.startswith("# Mined Behavioral Memory for `-slug-a`")
    assert "**Objective:** Ship the memory report today" in text
    assert text.index("**Objective:**") < text.index("### 1.")
    assert text.count("### ") == 3


def test_llm_block_with_own_title_is_not_reframed():
    text = "# Mined Behavioral Memory for `x`\n### 1. Tool / Skill Friction\n- a\n"
    assert frame_llm_block(_dossier(), text) == text


def test_llm_request_sets_temperature_and_sends_no_auth_header(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        return _FakeResponse(json.dumps({"choices": [{"message": {"content": "BLOCK TEXT"}}]}).encode())

    monkeypatch.setattr(distiller_mod.urllib.request, "urlopen", fake_urlopen)
    distiller_mod.call_llm_completion("prompt", endpoint="http://127.0.0.1:9/v1/chat/completions", model="local")

    assert captured["body"]["temperature"] == 0.2
    assert "authorization" not in captured["headers"]


def test_llm_failure_makes_one_attempt_and_returns_none(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        raise OSError("connection refused")

    monkeypatch.setattr(distiller_mod.urllib.request, "urlopen", fake_urlopen)
    out = distiller_mod.call_llm_completion("prompt", endpoint="http://127.0.0.1:9/v1/chat/completions", model="local")

    assert out is None
    assert len(calls) == 1


class FakeRepo:
    def __init__(self):
        self.externals = []
        self.passes = []

    def ensure(self):
        return True

    def commit_external(self, before):
        self.externals.append(before)
        return "ext1234"

    def commit_pass(self, title, lines):
        self.passes.append((title, list(lines)))
        return "abc1234"


def test_distill_all_commits_one_pass_with_lines(tmp_path, fake_llm):
    root = tmp_path / "mem"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))
    _write_dossier(root, "-demo", "s2", _dossier(session_id="s2"))
    repo = FakeRepo()

    MemoryDistiller(root, repo=repo).distill_all(llm_endpoint=EP)

    assert len(repo.passes) == 1
    title, lines = repo.passes[0]
    assert title == "distill: 2 distilled"
    assert sorted(lines) == ["distilled -demo/s1", "distilled -demo/s2"]


def test_forced_redistill_is_marked_in_pass_log(tmp_path, fake_llm):
    root = tmp_path / "mem"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))
    distiller = MemoryDistiller(root, repo=FakeRepo())
    distiller.distill_session("-demo", "s1", llm_endpoint=EP)
    distiller.distill_session("-demo", "s1", llm_endpoint=EP, force=True)

    assert distiller.pass_log == ["distilled -demo/s1", "re-distilled (--force) -demo/s1"]
    assert distiller.commit_pass() == "abc1234"
    assert distiller.repo.passes[-1][0] == "distill: 2 distilled (--force)"


def test_no_commit_when_nothing_written(tmp_path, fake_llm, monkeypatch):
    root = tmp_path / "mem"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))
    repo = FakeRepo()

    MemoryDistiller(root, repo=repo).distill_all(llm_endpoint=None)
    assert repo.passes == []
    assert repo.externals == []

    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: None)
    MemoryDistiller(root, repo=repo).distill_all(llm_endpoint=EP)
    assert repo.passes == []


def test_lock_not_held_during_llm_call(tmp_path, monkeypatch):
    from agentsignals.miner import file_lock

    root = tmp_path / "mem"
    lock = tmp_path / "miner.lock"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))
    seen = []

    def _llm_that_takes_the_lock(prompt, **_kwargs):
        with file_lock(lock, timeout=0.2) as acquired:
            seen.append(acquired)
        return LLM_SECTIONS

    monkeypatch.setattr(distiller_mod, "call_llm_completion", _llm_that_takes_the_lock)
    MemoryDistiller(root, lock_file=lock).distill_all(llm_endpoint=EP)

    assert seen == [True]
    assert (root / "-demo" / "s1" / "memory.md").exists()


def test_external_commit_once_per_pass(tmp_path, fake_llm):
    root = tmp_path / "mem"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))
    _write_dossier(root, "-demo", "s2", _dossier(session_id="s2"))
    repo = FakeRepo()

    MemoryDistiller(root, repo=repo).distill_all(llm_endpoint=EP)

    assert repo.externals == ["distill"]


def test_without_repo_behaviour_unchanged(tmp_path, fake_llm):
    root = tmp_path / "mem"
    _write_dossier(root, "-demo", "s1", _dossier(session_id="s1"))

    written = MemoryDistiller(root).distill_all(llm_endpoint=EP)

    assert len(written) == 1
    assert (root / "-demo" / "PROJECT_MEMORY.md").exists()
    assert not (root / ".git").exists()
