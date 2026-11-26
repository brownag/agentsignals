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


class _FakeSource:
    def __init__(self, name, refs=(), boom=False, settled=True):
        self.name = name
        self.refs = list(refs)
        self.boom = boom

    def iter_sessions(self, target_slug):
        if self.boom:
            raise RuntimeError("kaboom")
        yield from self.refs

    def extract(self, ref):
        from claudalizer.sources import Extraction

        return Extraction(["hello"], [], None, ["f.py"], True, {"k": 1})


def _ref(source="fake", settled=True):
    from claudalizer.sources import SessionRef

    return SessionRef(source, "-slug", "sid", "/x", 1.0, settled)


def _miner(tmp_path, sources):
    from claudalizer.miner import SessionMiner

    return SessionMiner(
        tmp_root=tmp_path / "nope",
        claude_projects=tmp_path / "proj",
        memories_root=tmp_path / "mem",
        lock_file=tmp_path / "lock",
        sources=sources,
    )


def test_source_error_does_not_stop_other_sources(tmp_path, caplog):
    m = _miner(tmp_path, [_FakeSource("bad", boom=True), _FakeSource("ok", [_ref()])])
    with caplog.at_level("WARNING"):
        out = m.scan_and_mine()
    assert len(out) == 1
    assert "Session source bad failed" in caplog.text


def test_missing_tmp_root_still_runs_other_sources(tmp_path):
    m = _miner(tmp_path, [ClaudeCodeSource(tmp_path / "nope", tmp_path / "proj"), _FakeSource("ok", [_ref()])])
    assert len(m.scan_and_mine()) == 1


def test_dossier_source_comes_from_ref(tmp_path):
    m = _miner(tmp_path, [_FakeSource("fake", [_ref("opencode")])])
    d = m.scan_and_mine()[0]
    assert d.source == "opencode"
    assert d.touched_files == ["f.py"]
    assert d.source_meta == {"k": 1}
    assert d.stats["touched_count"] == 1


def test_unsettled_ref_counted_active(tmp_path):
    m = _miner(tmp_path, [_FakeSource("fake", [_ref(settled=False)])])
    assert m.scan_and_mine() == []
    assert m.skipped["active"] == ["-slug/sid"]
    assert len(m.scan_and_mine(debounce=False)) == 1
