"""tests/test_distiller.py - Tests for claudalizer/distiller.py (SPEC §3.2, §4.2).

Characterisation tests pin behaviour that is correct today. Strict xfail tests describe
target behaviour owned by goals G18-G21; each one starts passing when its goal lands, and
must then have its marker removed in the same change.

Every test uses tmp_path for the memories root and never makes a network call.
"""

import json


import claudalizer.distiller as distiller_mod
from claudalizer.distiller import MemoryDistiller, build_synthesis_prompt, synthesize_offline_memory_block


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


def test_offline_block_has_three_sections_in_order():
    block = synthesize_offline_memory_block(_dossier())
    headings = [
        "### 1. Tool / Skill Friction",
        "### 2. Blind Alleys & Discarded Spikes",
        "### 3. Directives for CLAUDE.md",
    ]
    positions = [block.index(h) for h in headings]
    assert positions == sorted(positions)


def test_distill_session_writes_memory_md_and_project_memory(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))

    res = MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456")

    assert res is not None and res.exists()
    assert res.name == "memory.md"
    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Session abcdef12 Distillation" in project


def test_distill_session_skips_existing_memory_without_force(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)

    first = distiller.distill_session("-slug-a", "abcdef12-3456")
    project_after_first = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    second = distiller.distill_session("-slug-a", "abcdef12-3456")

    assert second == first
    assert (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8") == project_after_first


def test_llm_block_used_when_endpoint_returns_content(tmp_path, monkeypatch):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: "LLM BLOCK")

    res = MemoryDistiller(memories_root=root).distill_session(
        "-slug-a", "abcdef12-3456", llm_endpoint="http://127.0.0.1:9/v1"
    )

    assert "LLM BLOCK" in res.read_text(encoding="utf-8")


def test_offline_fallback_when_llm_returns_nothing(tmp_path, monkeypatch):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    monkeypatch.setattr(distiller_mod, "call_llm_completion", lambda *a, **k: None)

    res = MemoryDistiller(memories_root=root).distill_session(
        "-slug-a", "abcdef12-3456", llm_endpoint="http://127.0.0.1:9/v1"
    )

    assert "# Mined Behavioral Memory" in res.read_text(encoding="utf-8")


def test_distill_all_respects_target_slug(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "sess-a-0001", _dossier(slug="-slug-a", session_id="sess-a-0001"))
    _write_dossier(root, "-slug-b", "sess-b-0001", _dossier(slug="-slug-b", session_id="sess-b-0001"))

    out = MemoryDistiller(memories_root=root).distill_all(target_slug="-slug-a")

    assert len(out) == 1
    assert "-slug-a" in str(out[0])
    assert not (root / "-slug-b" / "PROJECT_MEMORY.md").exists()


def test_python_error_maps_to_venv_directive():
    dossier = _dossier(
        tool_errors=[
            {
                "tool_name": "Bash",
                "command_or_input": "python run.py",
                "error_output": "Exit code 127\nNo such file or directory: 'python'",
                "exit_code": 127,
            }
        ]
    )
    block = synthesize_offline_memory_block(dossier)
    assert "Verify Python virtualenv or conda environment path" in block


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


def test_force_redistill_does_not_duplicate_project_section(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)

    distiller.distill_session("-slug-a", "abcdef12-3456")
    distiller.distill_session("-slug-a", "abcdef12-3456", force=True)

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.count("## Session abcdef12 Distillation") == 1


def test_rebuild_changes_only_the_redistilled_session_text(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "aaaa1111-0001", _dossier(slug="-slug-a", session_id="aaaa1111-0001", scan_timestamp="2026-01-01"))
    _write_dossier(root, "-slug-a", "bbbb2222-0002", _dossier(slug="-slug-a", session_id="bbbb2222-0002", scan_timestamp="2026-01-02"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "aaaa1111-0001")
    distiller.distill_session("-slug-a", "bbbb2222-0002")

    dossier_a = _dossier(
        slug="-slug-a",
        session_id="aaaa1111-0001",
        scan_timestamp="2026-01-01",
        tool_errors=[{"tool_name": "Bash", "command_or_input": "make NEWA", "error_output": "Error: NEWA failed", "exit_code": 2}],
    )
    (root / "-slug-a" / "aaaa1111-0001" / "dossier.json").write_text(json.dumps(dossier_a), encoding="utf-8")
    distiller.distill_session("-slug-a", "aaaa1111-0001", force=True)

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.count("make NEWA") == 1
    b_text = (root / "-slug-a" / "bbbb2222-0002" / "memory.md").read_text(encoding="utf-8")
    assert b_text in project
    assert project.index("## Session aaaa1111") < project.index("## Session bbbb2222")


def test_rebuild_orders_sessions_by_scan_timestamp(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "zzzz0000-0001", _dossier(slug="-slug-a", session_id="zzzz0000-0001", scan_timestamp="2026-01-02"))
    _write_dossier(root, "-slug-a", "aaaa0000-0002", _dossier(slug="-slug-a", session_id="aaaa0000-0002", scan_timestamp="2026-01-01"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "zzzz0000-0001")
    distiller.distill_session("-slug-a", "aaaa0000-0002")

    project = (root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert project.index("## Session aaaa0000") < project.index("## Session zzzz0000")


def test_rebuild_skips_session_without_memory_md(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    _write_dossier(root, "-slug-a", "nomemo00-0001", _dossier(slug="-slug-a", session_id="nomemo00-0001"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "abcdef12-3456")

    project =(root / "-slug-a" / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "## Session nomemo00" not in project
    assert "## Session abcdef12" in project


def test_rebuild_is_idempotent(tmp_path):
    root = tmp_path / "memories"
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))
    distiller = MemoryDistiller(memories_root=root)
    distiller.distill_session("-slug-a", "abcdef12-3456")
    path = root / "-slug-a" / "PROJECT_MEMORY.md"
    first = path.read_bytes()

    distiller.distill_session("-slug-a", "abcdef12-3456", force=True)

    assert path.read_bytes() == first


def test_rebuild_discards_hand_edits_outside_session_files(tmp_path):
    root = tmp_path / "memories"
    proj = root / "-slug-a"
    proj.mkdir(parents=True)
    (proj / "PROJECT_MEMORY.md").write_text("hand notes\n", encoding="utf-8")
    _write_dossier(root, "-slug-a", "abcdef12-3456", _dossier(slug="-slug-a"))

    MemoryDistiller(memories_root=root).distill_session("-slug-a", "abcdef12-3456")

    project = (proj / "PROJECT_MEMORY.md").read_text(encoding="utf-8")
    assert "hand notes" not in project
    assert "## Session abcdef12 Distillation" in project


def test_no_matching_error_shows_none_detected_not_fallback_directive():
    block = synthesize_offline_memory_block(_dossier(tool_errors=[]))
    directives = _section(block, "### 3. Directives for CLAUDE.md")
    assert "Maintain strict idempotency" not in directives
    assert "None detected" in directives


def test_directives_none_detected_when_errors_match_no_pattern():
    dossier = _dossier(
        tool_errors=[
            {
                "tool_name": "Bash",
                "command_or_input": "ls",
                "error_output": "Exit code 1",
                "exit_code": 1,
            }
        ]
    )
    block = synthesize_offline_memory_block(dossier)
    directives = _section(block, "### 3. Directives for CLAUDE.md")
    assert "- None detected." in directives
    assert "Maintain strict idempotency" not in directives


def test_test_runner_scratch_excluded_from_blind_alleys():
    dossier = _dossier(scratchpad_files=["g3-accept/lock", "rewrite-check/projects/x.jsonl"])
    block = synthesize_offline_memory_block(dossier)
    blind = _section(block, "### 2. Blind Alleys & Discarded Spikes")
    assert "No ephemeral scratchpads recorded." in blind


def test_scratch_outside_test_runs_is_kept():
    dossier = _dossier(scratchpad_files=["planning-backup/notes.md", "g3-accept/lock", "docs/g3-accept-notes.md"])
    block = synthesize_offline_memory_block(dossier)
    blind = _section(block, "### 2. Blind Alleys & Discarded Spikes")
    assert "planning-backup/notes.md" in blind
    assert "docs/g3-accept-notes.md" in blind
    assert "g3-accept/lock" not in blind


def test_friction_line_shows_real_error_text():
    # First output line is a bare exit code; the real error is on the second line.
    dossier = _dossier(
        tool_errors=[
            {
                "tool_name": "Bash",
                "command_or_input": "pytest tests/x.py",
                "error_output": "Exit code 2\nFAILED tests/x.py::test_y - AssertionError",
                "exit_code": 2,
            }
        ]
    )
    block = synthesize_offline_memory_block(dossier)
    friction = _section(block, "### 1. Tool / Skill Friction")
    assert "FAILED tests/x.py::test_y - AssertionError" in friction


def test_friction_entry_without_error_marker_is_dropped():
    dossier = _dossier(
        tool_errors=[
            {
                "tool_name": "Bash",
                "command_or_input": "make build",
                "error_output": "Exit code 2\nsome code line",
                "exit_code": 2,
            }
        ]
    )
    block = synthesize_offline_memory_block(dossier)
    friction = _section(block, "### 1. Tool / Skill Friction")
    assert "- None detected." in friction
    assert "Exit code 2" not in friction
    assert "some code line" not in friction
