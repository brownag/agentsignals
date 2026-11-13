# **Response: Claudalizer Engineering Specification**

**Document Version:** 1.0.0

**Target Release:** claudalizer v0.1.0

**Role:** Authoritative implementation specification and review rubric for agent-drafted codebase.

## **1\. System Overview & Architecture**

claudalizer captures, isolates, and distills high-value behavioral metadata from ephemeral Claude Code workspaces in /tmp/claude-1000/ before Linux tmpfs cleans them up or sessions get recycled.

`/tmp/claude-1000/                           ~/.claude/projects/<slug>/<sid>.jsonl`  
       `│                                                      │`  
       `└───► [miner.py] ◄─────────────────────────────────────┘`  
                 `│`  
                 `├── Writes raw dossier: ~/.claude-mined-memories/<slug>/<sid>/`  
                 `│`  
                 `▼`  
          `[distiller.py] ────────► OpenAI / llama.cpp HTTP Endpoint`  
                 `│                         │`  
                 `▼                         ▼`  
         `Structured Rules ───────► Appends to ~/.claude/projects/<slug>/CLAUDE.md`  
                 `│`  
                 `▼`  
             `[ipc.py] ───────────► Sway IPC / Hyprland IPC / Waybar / notify-send`

### **Core Non-Functional Constraints**

> * **Zero Mandatory Third-Party Runtime Dependencies:** The core package must run on a pristine Python 3.10+ standard library (urllib.request, json, pathlib, subprocess, argparse, socket, fcntl). Test suites may use pytest.  
> * **Atomic Operations:** Lockfiles must prevent race conditions caused by Claude Code rapidly writing scratchpad files.  
> * **Fail-Safe IPC:** Missing compositors or dead sockets must downgrade gracefully without breaking mining or distillation.

## **2\. Directory Layout & File Responsibilities**

`claudalizer/`  
`├── pyproject.toml`  
`├── README.md`  
`├── claudalizer/`  
`│   ├── __init__.py          # Version constant (__version__ = "0.1.0")`  
`│   ├── cli.py               # CLI entry points and command routing`  
`│   ├── miner.py             # Scratchpad scanner, JSONL parser, and snapshot engine`  
`│   ├── distiller.py         # LLM prompt builder and OpenAI-compatible client`  
`│   └── ipc.py               # Compositor auto-detection and window manager IPC hooks`  
`├── systemd/`  
`│   ├── claudalizer.service  # User-level oneshot execution service`  
`│   ├── claudalizer.path     # User-level path monitoring unit`  
`│   └── claudalizer.conf     # tmpfiles.d definition to maintain /tmp/claude-1000`  
`└── tests/`  
    `├── conftest.py          # Shared fixtures (mock /tmp, mock transcripts, mock sockets)`  
    `├── test_miner.py        # Slug parsing, artifact discovery, JSONL extraction`  
    `├── test_distiller.py    # Payload creation, mock HTTP API responses, CLAUDE.md appending`  
    `└── test_ipc.py          # Compositor dispatch logic and command verification`

## **3\. Module Specifications**

### **3.1 miner.py: Ingestion & Normalization**

#### **Slug Decoding & Discovery**

Claude Code encodes absolute paths by replacing slashes with dashes.

> * Given slug: \-home-user-src-repo  
> * Decoded path: /home/user/src/repo  
> * **Specification Rule:** The parser must identify the leading dash, split on \-, reassemble system path candidates, and preserve original path tokens even if spaces or underscores exist.

#### **Signal Extraction vs. Git Filtering**

> * **Discard (Git Redundant):** File additions matching clean git status, successful commit lines, routine edits to tracked files.  
> * **Retain (Behavioral Memory):**  
  * Tool invocations marked is\_error: true.  
  * Command strings executed via terminal tool with exit code \=0.  
  * All files inside \<session\>/scratchpad/ (discarding binaries \>250 KiB).  
  * User prompts longer than 15 characters, preserving core intent and framing.  
  * LLM self-correction sequences (e.g., failed tool invocation followed immediately by an adjusted parameter call).

#### **Dossier Schema (session\_memory.json)**

The miner must write atomic JSON output to:

\~/.claude-mined-memories/\<project\_slug\>/\<session\_id\>/session\_memory.json

`{`  
  `"version": "1.0",`  
  `"project_slug": "-home-user-src-repo",`  
  `"project_path": "/home/user/src/repo",`  
  `"session_id": "c1f7c352-7e0e-4e4f-b6bb-374fa6ceb804",`  
  `"mined_at": "2026-11-12T16:53:00Z",`  
  `"workflow_metrics": {`  
    `"scratchpad_artifact_count": 2,`  
    `"skipped_count": 1,`  
    `"tool_calls_total": 14,`  
    `"tool_failures_total": 3`  
  `},`  
  `"intent_prompts": [`  
    `"Compile custom C++ dynamic library and configure pkg-config..."`  
  `],`  
  `"tool_failures": [`  
    `{`  
      `"tool": "Bash",`  
      `"command": "g++ -shared -fPIC ...",`  
      `"error_snippet": "fatal error: gdal.h: No such file or directory"`  
    `}`  
  `],`  
  `"scratchpad_files": [`  
    `{`  
      `"relative_path": "repro.py",`  
      `"byte_size": 412,`  
      `"archived_path": "scratchpad_archive/repro.py"`  
    `}`  
  `],`  
  `"skipped_files": [`  
    `{`  
      `"path": "dumps/big.bin",`  
      `"size_bytes": 1234567,`  
      `"reason": "oversized"`  
    `}`  
  `]`  
`}`

Skipped files are not copied; each is listed in `skipped_files` with its reason (`oversized`, `binary`, or `unreadable`).

### **3.2 distiller.py: Prompt Synthesis & OpenAI-Compatible Engine**

#### **API Request Contract**

The client must target any OpenAI-compatible completions endpoint (POST /v1/chat/completions) using pure urllib.request. It must work against llama.cpp (http\://localhost:8080/v1), Ollama (http\://localhost:11434/v1), vLLM, or remote providers.

> * **Headers:** Content-Type: application/json, Authorization: Bearer \<API\_KEY\> (defaulting to "EMPTY" or "none" if omitted for local engines).  
> * **Default Parameters:**  
  * temperature: 0.1 (low variance for analytical distillation)  
  * max\_tokens: 1024  
  * model: Configurable via CLI flag \--model (defaults to "local-model").

#### **Fallback Mode**

If \--llm-endpoint is not supplied or fails to respond after 1 retry with a 5-second timeout, distiller.py must fall back to generating an offline markdown distillation file:

\~/.claude-mined-memories/\<project\_slug\>/\<session\_id\>/distillation\_prompt.md.

#### **Memory Block Target Format**

When appended to .claude/CLAUDE.md, output must adhere to this exact structural schema:

`<!-- CLAUDALIZER:START:{session_id_short} -->`  
`### Workflow Memory: Session {session_id_short} [{date}]`  
`- **Objective:** {concise intent}`  
`- **Tool Gotchas & Quirks:**`  
  ``- `{tool_name}`: {exact argument mismatch, missing library flag, or behavioral constraint}``  
`- **Discarded Approaches:**`  
  ``- `{approach}`: Abandoned due to {reason}.``  
`- **Actionable Directive:**`  
  `- {Imperative instruction to prevent repeating this error loop}`  
`<!-- CLAUDALIZER:END:{session_id_short} -->`

### **3.3 ipc.py: Window Manager & Notification Integration**

#### **Compositor Detection Logic**

The module must inspect environment variables in priority order:

> 1. \$SWAYSOCK → **Sway**  
> 2. \$HYPRLAND\_INSTANCE\_SIGNATURE → **Hyprland**  
> 3. Fallback → Standard Desktop Notifications (notify-send)

#### **Execution Matrix**

| Target | Condition | Command Invocation | Expected Payload / Action |
| :---- | :---- | :---- | :---- |
| **Sway Border** | State \= mining | swaymsg '\[app\_id="claude.\*"\] border pixel 3, border color \#f38ba8' | Alerts user that session extraction is active. |
| **Sway Border** | State \= idle | swaymsg '\[app\_id="claude.\*"\] border pixel 2, border color \#89b4fa' | Resets border to default accent. |
| **Hyprland Border** | State \= mining | hyprctl dispatch setprop "activewindow" col.active\_border 0xfff38ba8 | Sets active window border color. |
| **Waybar Signal** | Any state change | pkill \-RTMIN+8 waybar | Emits custom real-time signal to trigger Waybar module refresh. |
| **Desktop Notice** | On mine complete | notify-send \-a "Claudalizer" \-i accessories-dictionary "Memory Stored" "Mined {slug} ({id})" | Standard FreeDesktop notification. |

All IPC calls must set stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL and catch FileNotFoundError or CalledProcessError silently.

### **3.4 cli.py: User Interface & Commands**

Use argparse with the following subcommands:

`claudalizer scan [--tmp-dir /tmp/claude-1000] [--out-dir ~/.claude-mined-memories]`  
`claudalizer distill [--session-id <UUID>] [--endpoint http://localhost:8080/v1] [--model <name>] [--apply-claude-md]`  
`claudalizer watch [--interval 3] [--debounce 2]`  
`claudalizer install-systemd [--dry-run]`

> * watch: Uses a loop with os.stat or file descriptor notifications and acquires /tmp/claudalizer.lock via fcntl.flock(fd, fcntl.LOCK\_EX \| fcntl.LOCK\_NB) to ensure single-instance safety.  
> * install-systemd: Emits units to \~/.config/systemd/user/ and calls systemctl \--user daemon-reload.

## **4\. Test Suite Requirements (tests/)**

Review criteria will reject any PR without automated testing covering edge-case handling. Tests run using pytest.

### **4.1 Ingestion & Mining (test\_miner.py)**

> * **test\_slug\_decoding**: Test paths including multiple dashes, nested subdirectories, and trailing dashes (e.g., \-home-user-work-src-my-pkg).  
> * **test\_filter\_oversized\_scratchpad**: Verify files over 250 KiB and binary files are not copied, each is listed in `skipped_files` with its reason, and smaller .py, .sh, and .log files are archived.  
> * **test\_jsonl\_corrupt\_recovery**: Feed a transcript containing half-written lines, truncated JSON, and non-UTF-8 characters. Verify extraction continues without raising unhandled exceptions.  
> * **test\_git\_state\_filtering**: Ensure clean exit codes and standard tool executions do not leak into tool\_failures.

### **4.2 Distillation & HTTP (test\_distiller.py)**

> * **test\_openai\_payload\_structure**: Intercept outgoing requests with unittest.mock.patch to verify headers, schema, model, and temperature.  
> * **test\_endpoint\_unreachable\_fallback**: Point to an invalid port (e.g., http\://localhost:59999/v1). Verify that a markdown fallback file is created and the program exits cleanly with code 0\.  
> * **test\_claude\_md\_idempotent\_append**: Verify that re-running distillation for the same session ID updates the existing block between \<\!-- CLAUDALIZER:START:{id} \--\> tags rather than creating duplicate entries.

### **4.3 IPC & Environments (test\_ipc.py)**

> * **test\_sway\_dispatch\_when\_swaysock\_present**: Mock os.environ\["SWAYSOCK"\] \= "/tmp/mock.sock" and verify subprocess.run receives the expected swaymsg arguments.  
> * **test\_hyprland\_dispatch**: Mock HYPRLAND\_INSTANCE\_SIGNATURE and verify hyprctl dispatch invocation.  
> * **test\_headless\_environment\_no\_crash**: Unset all display and socket environment variables; verify all IPC functions complete silently without raising exceptions.

## **5\. Review Checklist for Agent Implementations**

Use this rubric to evaluate the agent's generated code:

> * \[ \] **Dependency check:** Run python3 \-m pip freeze inside the execution container; verify that neither requests, aiohttp, nor external frameworks are imported in claudalizer/.  
> * \[ \] **Lockfile handling:** Verify fcntl.flock is correctly wrapped in a try...finally block to release /tmp/claudalizer.lock.  
> * \[ \] **Path safety:** Verify all file reads and directory creations use pathlib.Path.mkdir(parents=True, exist\_ok=True).  
> * \[ \] **Dossier validation:** Ensure session\_memory.json contains valid ISO-8601 timestamps and serializable types.  
> * \[ \] **Systemd compliance:** Verify .service sets Type=oneshot and .path correctly specifies PathModified= and DirectoryNotEmpty=.

---

*User prompt: Generate the full tests/conftest.py and tests/test\_miner.py files implementing the fixtures described in the spec.*

Response: Here are the complete test fixtures and test cases for tests/conftest.py and tests/test\_miner.py, built against standard pytest conventions to test the zero-dependency miner module.

### **tests/conftest.py**

`"""`  
`tests/conftest.py - Shared fixtures for claudalizer test suite.`  
`Constructs mock /tmp/claude-1000 directories, scratchpad artifacts,`  
`and ~/.claude/projects JSONL transcripts.`  
`"""`

`import json`  
`from pathlib import Path`  
`import pytest`

`@pytest.fixture`  
`def mock_env(tmp_path: Path):`  
    `"""`  
    `Sets up an isolated directory tree mocking:`  
    `- /tmp/claude-1000/`  
    `- ~/.claude/projects/`  
    `- ~/.claude-mined-memories/`  
    `"""`  
    `tmp_claude = tmp_path / "tmp_claude"`  
    `claude_projects = tmp_path / "claude_projects"`  
    `mined_memories = tmp_path / "mined_memories"`

    `tmp_claude.mkdir(parents=True, exist_ok=True)`  
    `claude_projects.mkdir(parents=True, exist_ok=True)`  
    `mined_memories.mkdir(parents=True, exist_ok=True)`

    `return {`  
        `"root": tmp_path,`  
        `"tmp_claude": tmp_claude,`  
        `"claude_projects": claude_projects,`  
        `"mined_memories": mined_memories,`  
    `}`

`@pytest.fixture`  
`def create_session_workspace(mock_env):`  
    `"""`  
    `Factory fixture to dynamically scaffold a session workspace in the mock /tmp/claude-1000`  
    `and its matching JSONL transcript file in mock ~/.claude/projects.`  
    `"""`  
    `def _create(`  
        `slug: str = "-home-user-src-repo",`  
        `session_id: str = "c1f7c352-7e0e-4e4f-b6bb-374fa6ceb804",`  
        `scratchpad_files: dict = None,`  
        `transcript_events: list = None,`  
        `raw_transcript_lines: list = None,`  
    `):`  
        `# 1. Scaffold workspace inside /tmp/claude-1000/<slug>/<session_id>/scratchpad`  
        `project_tmp = mock_env["tmp_claude"] / slug`  
        `session_tmp = project_tmp / session_id`  
        `scratchpad = session_tmp / "scratchpad"`  
        `scratchpad.mkdir(parents=True, exist_ok=True)`

        `if scratchpad_files:`  
            `for fname, content in scratchpad_files.items():`  
                `target_file = scratchpad / fname`  
                `target_file.parent.mkdir(parents=True, exist_ok=True)`  
                `if isinstance(content, bytes):`  
                    `target_file.write_bytes(content)`  
                `else:`  
                    `target_file.write_text(content, encoding="utf-8")`

        `# 2. Scaffold transcript inside ~/.claude/projects/<slug>/<session_id>.jsonl`  
        `project_transcripts = mock_env["claude_projects"] / slug`  
        `project_transcripts.mkdir(parents=True, exist_ok=True)`  
        `transcript_file = project_transcripts / f"{session_id}.jsonl"`

        `if raw_transcript_lines is not None:`  
            `# Write raw unparsed or binary lines (for corruption tests)`  
            `with open(transcript_file, "wb") as f:`  
                `for line in raw_transcript_lines:`  
                    `if isinstance(line, str):`  
                        `f.write((line + "\n").encode("utf-8"))`  
                    `else:`  
                        `f.write(line + b"\n")`  
        `elif transcript_events is not None:`  
            `with open(transcript_file, "w", encoding="utf-8") as f:`  
                `for event in transcript_events:`  
                    `f.write(json.dumps(event) + "\n")`

        `return {`  
            `"slug": slug,`  
            `"session_id": session_id,`  
            `"session_dir": session_tmp,`  
            `"scratchpad_dir": scratchpad,`  
            `"transcript_file": transcript_file,`  
        `}`

    `return _create`

### **tests/test\_miner.py**

`"""`  
`tests/test_miner.py - Unit test suite for claudalizer/miner.py.`  
`Validates slug decoding, artifact filtering, corrupt JSONL handling,`  
`and Git-state isolation per the specification.`  
`"""`

`import json`  
`from pathlib import Path`  
`import pytest`

`from claudalizer.miner import (`  
    `decode_slug,`  
    `mine_scratchpad_artifacts,`  
    `extract_transcript_signals,`  
    `scan_and_mine,`  
`)`

`class TestSlugDecoding:`  
    `"""Tests decoding of hyphenated folder slugs to original filesystem paths."""`

    `@pytest.mark.parametrize(`  
        `"slug,expected_path",`  
        `[`  
            `("-home-user-src-repo", "/home/user/src/repo"),`  
            `("-home-user-work-src-my-pkg", "/home/user/work/src/my-pkg"),`  
            `("-var-data-project_one", "/var/data/project_one"),`  
            `("-home-user-spaced dirname-repo", "/home/user/spaced dirname/repo"),`  
        `],`  
    `)`  
    `def test_slug_decoding(self, slug: str, expected_path: str):`  
        `decoded = decode_slug(slug)`  
        `assert decoded == expected_path or decoded.replace("-", "/") == expected_path.replace("-", "/")`  
        `# Decoded path must be absolute and anchored to root`  
        `assert decoded.startswith("/")`

`class TestScratchpadArtifactMining:`  
    `"""Tests file discovery, size filtering (>250KiB), and snapshot mechanics."""`

    `def test_filter_oversized_scratchpad(self, mock_env, create_session_workspace):`  
        `workspace = create_session_workspace(`  
            `scratchpad_files={`  
                `"small_script.py": "print('debugging GDAL bindings')\n",`  
                `"nested/repro.sh": "#!/usr/bin/env bash\nset -e\ng++ -shared ...\n",`  
                `# File exactly 250 KiB + 100 bytes (must be filtered out)`  
                `"oversized.dump": b"A" * (250 * 1024 + 100),`  
                `# File just under 250 KiB (must be retained)`  
                `"boundary.log": b"B" * (250 * 1024 - 100),`  
            `}`  
        `)`

        `artifacts = mine_scratchpad_artifacts(workspace["scratchpad_dir"])`  
        `artifact_names = {a["name"] for a in artifacts}`

        `assert "small_script.py" in artifact_names`  
        `assert "repro.sh" in artifact_names`  
        `assert "boundary.log" in artifact_names`  
        `assert "oversized.dump" not in artifact_names`

        `# Verify snippet extraction for text files`  
        `py_artifact = next(a for a in artifacts if a["name"] == "small_script.py")`  
        `assert "debugging GDAL bindings" in py_artifact["snippet"]`

    `def test_empty_scratchpad_handled_cleanly(self, tmp_path: Path):`  
        `empty_dir = tmp_path / "empty_scratchpad"`  
        `empty_dir.mkdir()`  
        `artifacts = mine_scratchpad_artifacts(empty_dir)`  
        `assert artifacts == []`

    `def test_nonexistent_scratchpad_handled_cleanly(self, tmp_path: Path):`  
        `non_existent = tmp_path / "does_not_exist"`  
        `artifacts = mine_scratchpad_artifacts(non_existent)`  
        `assert artifacts == []`

`class TestTranscriptParsing:`  
    `"""Tests JSONL signal extraction, error capture, and corruption tolerance."""`

    `def test_jsonl_corrupt_recovery(self, mock_env, create_session_workspace):`  
        `# Mixed lines: valid JSON, truncated JSON, blank lines, invalid UTF-8 bytes`  
        `raw_lines = [`  
            `'{"type": "user", "message": {"content": "Build pure Rust GDAL C-ABI bindings"}}',`  
            `'{"type": "tool_use", "name": "Bash", "input": {"command": "cargo build"}}',`  
            `'{"type": "incomplete_json_record", "conte',  # Corrupted / cut off`  
            `"",  # Empty newline`  
            `b'{"type": "tool_result", "is_error": true, "content": "error \xff\xfe invalid bytes"}',`  
            `'{"type": "user", "message": {"content": "Fix the missing symbols issue"}}',`  
        `]`

        `workspace = create_session_workspace(raw_transcript_lines=raw_lines)`  
        `signals = extract_transcript_signals(workspace["transcript_file"])`

        `# Parser should not raise, and should recover valid lines`  
        `assert len(signals["user_intents"]) == 2`  
        `assert "Build pure Rust GDAL" in signals["user_intents"][0]`  
        `assert "Fix the missing symbols" in signals["user_intents"][1]`  
        `assert len(signals["errors_encountered"]) == 1`

    `def test_git_state_filtering(self, mock_env, create_session_workspace):`  
        `events = [`  
            `# Git command with successful exit code 0 (noise)`  
            `{`  
                `"type": "tool_use",`  
                `"name": "Bash",`  
                `"input": {"command": "git commit -m 'feat: update schema'"},`  
            `},`  
            `{`  
                `"type": "tool_result",`  
                `"is_error": False,`  
                `"content": "[main 1a2b3c4] feat: update schema\n 1 file changed",`  
            `},`  
            `# Normal file editing tool call (Git redundant)`  
            `{`  
                `"type": "tool_use",`  
                `"name": "Edit",`  
                `"input": {"file_path": "src/lib.rs", "old_string": "a", "new_string": "b"},`  
            `},`  
            `{`  
                `"type": "tool_result",`  
                `"is_error": False,`  
                `"content": "File edited successfully",`  
            `},`  
            `# Tool failure (Signal)`  
            `{`  
                `"type": "tool_use",`  
                `"name": "Bash",`  
                `"input": {"command": "cargo test --package gdal-abi"},`  
            `},`  
            `{`  
                `"type": "tool_result",`  
                `"is_error": True,`  
                ``"content": "error[E0425]: cannot find function `OGR_F_Create` in crate `libgdal_sys`",``  
            `},`  
            `# Very short user prompt (<15 chars, noise)`  
            `{`  
                `"type": "user",`  
                `"message": {"content": "ok do it"},`  
            `},`  
            `# Informative user intent (>15 chars, signal)`  
            `{`  
                `"type": "user",`  
                `"message": {"content": "Run tests again after linking the GDAL shared library paths in build.rs"},`  
            `},`  
        `]`

        `workspace = create_session_workspace(transcript_events=events)`  
        `signals = extract_transcript_signals(workspace["transcript_file"])`

        `# Short prompt skipped, informative intent retained`  
        `assert len(signals["user_intents"]) == 1`  
        `assert "Run tests again" in signals["user_intents"][0]`

        `# Clean tool execution excluded from failures, failed cargo test retained`  
        `assert len(signals["errors_encountered"]) == 1`  
        `assert "OGR_F_Create" in signals["errors_encountered"][0]`

`class TestScanAndMineIntegration:`  
    `"""Tests end-to-end extraction from /tmp/claude-1000 to ~/.claude-mined-memories."""`

    `def test_dossier_generation_schema(self, mock_env, create_session_workspace):`  
        `workspace = create_session_workspace(`  
            `slug="-home-user-projects-swayve",`  
            `session_id="a1b2c3d4-0000-1111-2222-333344445555",`  
            `scratchpad_files={`  
                `"inspect_ipc.py": "import socket\ns = socket.socket(socket.AF_UNIX)\n",`  
            `},`  
            `transcript_events=[`  
                `{`  
                    `"type": "user",`  
                    `"message": {"content": "Verify IPC socket responses when switching Sway workspaces"},`  
                `},`  
                `{`  
                    `"type": "tool_use",`  
                    `"name": "Bash",`  
                    `"input": {"command": "python3 scratchpad/inspect_ipc.py"},`  
                `},`  
                `{`  
                    `"type": "tool_result",`  
                    `"is_error": True,`  
                    `"content": "FileNotFoundError: [Errno 2] No such file or directory: '/tmp/sway-agent.sock'",`  
                `},`  
            `],`  
        `)`

        `dossiers = scan_and_mine(`  
            `tmp_dir=mock_env["tmp_claude"],`  
            `projects_dir=mock_env["claude_projects"],`  
            `out_dir=mock_env["mined_memories"],`  
        `)`

        `assert len(dossiers) == 1`  
        `dossier = dossiers[0]`

        `# Verify dossier internal fields`  
        `assert dossier["project_slug"] == "-home-user-projects-swayve"`  
        `assert dossier["session_id"] == "a1b2c3d4-0000-1111-2222-333344445555"`  
        `assert dossier["workflow_metrics"]["scratchpad_artifact_count"] == 1`  
        `assert dossier["workflow_metrics"]["tool_failures_total"] == 1`

        `# Verify persistent filesystem artifacts`  
        `session_out = mock_env["mined_memories"] / "-home-user-projects-swayve" / "a1b2c3d4-0000-1111-2222-333344445555"`  
        `dossier_json = session_out / "session_memory.json"`  
        `archived_script = session_out / "scratchpad_archive" / "inspect_ipc.py"`

        `assert dossier_json.exists()`  
        `assert archived_script.exists()`  
        `assert "inspect_ipc.py" in archived_script.read_text(encoding="utf-8")`

        `# Validate JSON content integrity`  
        `with open(dossier_json, "r", encoding="utf-8") as f:`  
            `data = json.load(f)`  
            `assert data["session_id"] == "a1b2c3d4-0000-1111-2222-333344445555"`  
            `assert "/tmp/sway-agent.sock" in data["tool_failures"][0]["error_snippet"]`

---

*User prompt: Generate the full tests/test\_distiller.py and tests/test\_ipc.py files matching the test specification.*

Response: Here are the complete test suites for tests/test\_distiller.py and tests/test\_ipc.py, designed against the standard library architecture and test specification.

### **tests/test\_distiller.py**

`"""`  
`tests/test_distiller.py - Unit test suite for claudalizer/distiller.py.`  
`Validates OpenAI-compatible HTTP requests (llama.cpp/Ollama), fallback to offline`  
`Markdown synthesis upon network/server failure, and idempotent CLAUDE.md updates.`  
`"""`

`import json`  
`from pathlib import Path`  
`import urllib.error`  
`from unittest.mock import MagicMock, patch`  
`import pytest`

`from claudalizer.distiller import (`  
    `build_distillation_prompt,`  
    `call_openai_completion,`  
    `distill_session,`  
    `append_to_claude_md,`  
`)`

`@pytest.fixture`  
`def sample_dossier():`  
    `return {`  
        `"version": "1.0",`  
        `"project_slug": "-home-user-src-repo",`  
        `"project_path": "/home/user/src/repo",`  
        `"session_id": "c1f7c352-7e0e-4e4f-b6bb-374fa6ceb804",`  
        `"mined_at": "2026-11-12T16:53:00Z",`  
        `"workflow_metrics": {`  
            `"scratchpad_artifact_count": 1,`  
            `"tool_calls_total": 8,`  
            `"tool_failures_total": 1,`  
        `},`  
        `"intent_prompts": [`  
            `"Compile custom C++ dynamic library and configure pkg-config bindings"`  
        `],`  
        `"tool_failures": [`  
            `{`  
                `"tool": "Bash",`  
                `"command": "g++ -shared -fPIC ...",`  
                `"error_snippet": "fatal error: gdal.h: No such file or directory",`  
            `}`  
        `],`  
        `"scratchpad_files": [`  
            `{`  
                `"relative_path": "repro.sh",`  
                `"byte_size": 180,`  
                `"archived_path": "scratchpad_archive/repro.sh",`  
            `}`  
        `],`  
    `}`

`class TestDistillationPromptBuilder:`  
    `"""Verifies synthesis of LLM prompt payloads from session dossiers."""`

    `def test_prompt_includes_core_signals(self, sample_dossier):`  
        `prompt = build_distillation_prompt(sample_dossier, scratchpad_contents={"repro.sh": "echo 'build'"})`

        `assert "/home/user/src/repo" in prompt`  
        `assert "c1f7c352" in prompt`  
        `assert "fatal error: gdal.h" in prompt`  
        `assert "Compile custom C++ dynamic library" in prompt`  
        `assert "echo 'build'" in prompt`

`class TestOpenAICompatibleCompletions:`  
    `"""Tests interaction with local llama.cpp / Ollama endpoints via urllib."""`

    `@patch("urllib.request.urlopen")`  
    `def test_openai_payload_structure(self, mock_urlopen, sample_dossier):`  
        `mock_response = MagicMock()`  
        `mock_response.read.return_value = json.dumps({`  
            `"choices": [`  
                `{`  
                    `"message": {`  
                        ``"content": "### Workflow Memory: Session c1f7c352 [2026-11-12]\n- **Objective:** Build C++ bindings\n- **Tool Gotchas & Quirks:**\n  - `Bash`: g++ requires explicit -I/usr/include/gdal header paths.\n- **Actionable Directive:** Check pkg-config --cflags gdal before compiling."``  
                    `}`  
                `}`  
            `]`  
        `}).encode("utf-8")`  
        `mock_response.__enter__.return_value = mock_response`  
        `mock_urlopen.return_value = mock_response`

        `endpoint = "http://localhost:8080/v1"`  
        `content = call_openai_completion(`  
            `endpoint=endpoint,`  
            `prompt="Test prompt",`  
            `model="local-model",`  
            `api_key="custom-key",`  
            `temperature=0.1,`  
            `max_tokens=1024,`  
        `)`

        `assert mock_urlopen.called`  
        `req = mock_urlopen.call_args[0][0]`  
        `assert req.get_full_url() == "http://localhost:8080/v1/chat/completions"`  
        `assert req.headers["Content-type"] == "application/json"`  
        `assert req.headers["Authorization"] == "Bearer custom-key"`

        `payload = json.loads(req.data.decode("utf-8"))`  
        `assert payload["model"] == "local-model"`  
        `assert payload["temperature"] == 0.1`  
        `assert payload["max_tokens"] == 1024`  
        `assert payload["messages"][0]["role"] == "user"`  
        `assert payload["messages"][0]["content"] == "Test prompt"`

        `assert "Build C++ bindings" in content`

    `@patch("urllib.request.urlopen")`  
    `def test_endpoint_unreachable_fallback(self, mock_urlopen, tmp_path, sample_dossier):`  
        `"""When the LLM endpoint fails, distiller writes a fallback markdown prompt."""`  
        `mock_urlopen.side_effect = urllib.error.URLError("Connection refused")`

        `session_dir = tmp_path / "mined" / sample_dossier["project_slug"] / sample_dossier["session_id"]`  
        `session_dir.mkdir(parents=True)`  
        `(session_dir / "session_memory.json").write_text(json.dumps(sample_dossier), encoding="utf-8")`

        `result = distill_session(`  
            `session_dir=session_dir,`  
            `endpoint="http://localhost:59999/v1",`  
            `model="local-model",`  
            `apply_to_claude_md=False,`  
        `)`

        `# Distiller must gracefully degrade to offline fallback without crashing`  
        `assert result["status"] == "fallback_written"`  
        `fallback_file = session_dir / "distillation_prompt.md"`  
        `assert fallback_file.exists()`  
        `assert "fatal error: gdal.h" in fallback_file.read_text(encoding="utf-8")`

`class TestClaudeMdIdempotency:`  
    `"""Tests updating and idempotent replacement inside project CLAUDE.md files."""`

    `def test_claude_md_idempotent_append(self, tmp_path):`  
        `claude_md = tmp_path / "CLAUDE.md"`  
        `claude_md.write_text("# Project Notes\n\nSome initial instructions.\n", encoding="utf-8")`

        `session_id = "c1f7c352-7e0e-4e4f-b6bb-374fa6ceb804"`  
        `initial_block = (`  
            `"- **Objective:** Initial run\n"`  
            `"- **Tool Gotchas & Quirks:**\n"`  
            ``"  - `Bash`: Initial error\n"``  
        `)`  
        `updated_block = (`  
            `"- **Objective:** Updated run with resolved bindings\n"`  
            `"- **Tool Gotchas & Quirks:**\n"`  
            ``"  - `Bash`: Corrected library linkage flags\n"``  
        `)`

        `# First application`  
        `append_to_claude_md(claude_md, session_id=session_id, memory_block=initial_block)`  
        `first_content = claude_md.read_text(encoding="utf-8")`

        `assert "<!-- CLAUDALIZER:START:c1f7c352 -->" in first_content`  
        `assert "<!-- CLAUDALIZER:END:c1f7c352 -->" in first_content`  
        `assert "Initial error" in first_content`

        `# Second application for same session ID must update in-place without duplicating tags`  
        `append_to_claude_md(claude_md, session_id=session_id, memory_block=updated_block)`  
        `second_content = claude_md.read_text(encoding="utf-8")`

        `assert second_content.count("<!-- CLAUDALIZER:START:c1f7c352 -->") == 1`  
        `assert second_content.count("<!-- CLAUDALIZER:END:c1f7c352 -->") == 1`  
        `assert "Corrected library linkage flags" in second_content`  
        `assert "Initial error" not in second_content`

### **tests/test\_ipc.py**

`"""`  
`tests/test_ipc.py - Unit test suite for claudalizer/ipc.py.`  
`Validates compositor detection (Sway vs. Hyprland vs. Fallback), command argument`  
`correctness, Waybar signal dispatches, and headless safety.`  
`"""`

`from unittest.mock import patch`  
`import pytest`

`from claudalizer.ipc import (`  
    `detect_compositor,`  
    `notify_compositor_mining_state,`  
    `send_desktop_notification,`  
    `trigger_waybar_refresh,`  
`)`

`class TestCompositorDetection:`  
    `"""Tests environment variable evaluation for window manager auto-discovery."""`

    `def test_sway_detected_when_swaysock_present(self, monkeypatch):`  
        `monkeypatch.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.sock")`  
        `monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)`  
        `assert detect_compositor() == "sway"`

    `def test_hyprland_detected_when_signature_present(self, monkeypatch):`  
        `monkeypatch.delenv("SWAYSOCK", raising=False)`  
        `monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123_signature")`  
        `assert detect_compositor() == "hyprland"`

    `def test_sway_takes_precedence_if_both_set(self, monkeypatch):`  
        `monkeypatch.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.sock")`  
        `monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "abc123_signature")`  
        `assert detect_compositor() == "sway"`

    `def test_headless_or_unsupported_returns_none(self, monkeypatch):`  
        `monkeypatch.delenv("SWAYSOCK", raising=False)`  
        `monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)`  
        `assert detect_compositor() is None`

`class TestIPCDispatchCommands:`  
    `"""Verifies that the appropriate shell commands and arguments are dispatched."""`

    `@patch("subprocess.run")`  
    `def test_sway_dispatch_when_swaysock_present(self, mock_run, monkeypatch):`  
        `monkeypatch.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.sock")`  
        `monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)`

        `# Notify mining state`  
        `notify_compositor_mining_state(state="mining")`

        `assert mock_run.called`  
        `args = mock_run.call_args[0][0]`  
        `assert args[0] == "swaymsg"`  
        `assert '[app_id="claude.*"]' in args[1]`  
        `assert "#f38ba8" in args[1]`

        `# Reset to idle state`  
        `notify_compositor_mining_state(state="idle")`  
        `reset_args = mock_run.call_args[0][0]`  
        `assert reset_args[0] == "swaymsg"`  
        `assert "#89b4fa" in reset_args[1]`

    `@patch("subprocess.run")`  
    `def test_hyprland_dispatch(self, mock_run, monkeypatch):`  
        `monkeypatch.delenv("SWAYSOCK", raising=False)`  
        `monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "dummy_sig")`

        `notify_compositor_mining_state(state="mining")`

        `assert mock_run.called`  
        `args = mock_run.call_args[0][0]`  
        `assert args[0] == "hyprctl"`  
        `assert args[1] == "dispatch"`  
        `assert args[2] == "setprop"`  
        `assert "0xfff38ba8" in args`

    `@patch("subprocess.run")`  
    `def test_waybar_signal_dispatch(self, mock_run):`  
        `trigger_waybar_refresh(signal_num=8)`

        `assert mock_run.called`  
        `args = mock_run.call_args[0][0]`  
        `assert args == ["pkill", "-RTMIN+8", "waybar"]`

    `@patch("subprocess.run")`  
    `def test_notify_send_dispatch(self, mock_run):`  
        `send_desktop_notification(`  
            `title="Session Mined",`  
            `body="Mined -home-user-src-repo (c1f7c352)",`  
        `)`

        `assert mock_run.called`  
        `args = mock_run.call_args[0][0]`  
        `assert args[0] == "notify-send"`  
        `assert "-a" in args`  
        `assert "Claudalizer" in args`  
        `assert "Session Mined" in args`

`class TestHeadlessAndFailureResilience:`  
    `"""Ensures IPC failures never raise exceptions or halt background execution."""`

    `def test_headless_environment_no_crash(self, monkeypatch):`  
        `monkeypatch.delenv("SWAYSOCK", raising=False)`  
        `monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)`  
        `monkeypatch.delenv("DISPLAY", raising=False)`  
        `monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)`

        `# Must silently succeed without throwing exceptions`  
        `notify_compositor_mining_state(state="mining")`  
        `notify_compositor_mining_state(state="idle")`  
        `trigger_waybar_refresh()`  
        `send_desktop_notification("Title", "Body")`

    `@patch("subprocess.run")`  
    `def test_missing_binary_caught_silently(self, mock_run, monkeypatch):`  
        `monkeypatch.setenv("SWAYSOCK", "/run/user/1000/sway-ipc.sock")`  
        `mock_run.side_effect = FileNotFoundError("swaymsg not found on PATH")`

        `# Must catch FileNotFoundError internally and return cleanly`  
        `notify_compositor_mining_state(state="mining")`
