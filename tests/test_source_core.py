import os

from claudalizer.miner import SessionDossier, has_nonzero_exit_code
from claudalizer.sources.claude_code import ClaudeCodeSource

OLD = 1_000_000_000.0


def _age(*paths):
    for p in paths:
        os.utime(p, (OLD, OLD))


def test_exit_code_pattern_matches_both_forms():
    assert has_nonzero_exit_code("Exit code 1")
    assert has_nonzero_exit_code("Exit code: 1")
    assert not has_nonzero_exit_code("Exit code: 0")


def test_dossier_has_source_defaults():
    d = SessionDossier("s", "id", None, False, 0.0).to_dict()
    assert d["source"] == "claude_code"
    assert d["touched_files"] == []
    assert d["source_meta"] == {}


def test_claude_code_source_matches_walk(tmp_path):
    tmp_root = tmp_path / "tmp"
    projects = tmp_path / "projects"
    slug = "-home-andrew-proj"
    sess = tmp_root / slug / "sid1"
    scratch = sess / "scratchpad"
    scratch.mkdir(parents=True)
    note = scratch / "a.txt"
    note.write_text("x")
    (tmp_root / slug / ".hidden").mkdir()
    (tmp_root / "files" / "sid2").mkdir(parents=True)
    transcript = projects / slug / "sid1.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("")
    _age(note, scratch, sess, tmp_root / slug, tmp_root)
    os.utime(transcript, (OLD + 50, OLD + 50))

    src = ClaudeCodeSource(tmp_root, projects)
    refs = list(src.iter_sessions(None))
    assert len(refs) == 1
    r = refs[0]
    assert (r.source, r.slug, r.session_id) == ("claude_code", slug, "sid1")
    assert r.decoded_path == "/home/andrew/proj"
    assert r.changed_at == OLD + 50
    assert r.settled
    assert list(src.iter_sessions("-other")) == []
    ex = src.extract(r)
    assert ex.transcript_found and ex.scratchpad_dir == scratch
    assert ex.touched_files == [] and ex.source_meta == {}


def test_claude_code_source_missing_tmp_root_yields_nothing(tmp_path):
    src = ClaudeCodeSource(tmp_path / "nope", tmp_path / "p")
    assert list(src.iter_sessions(None)) == []
