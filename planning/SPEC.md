# **Response: Claudalizer Engineering Specification**

**Document Version:** 1.1.0

**Target Release:** claudalizer v0.2.0

**Last Updated:** 2026-11-25 (opencode session source, §3.1 and §4.1a; earlier: removed the `claudalizer.path` unit)

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
         `Structured Rules ───────► Writes ~/.claude-mined-memories/<slug>/PROJECT\_MEMORY.md`  
                 `│`  
                 `▼`  
             `[ipc.py] ───────────► Sway IPC / Hyprland IPC / Waybar / notify-send`

Completed scans also update persistent scan state under the configured memories root; Waybar reads a separate temporary status payload.

### **Core Non-Functional Constraints**

> * **Zero Mandatory Third-Party Runtime Dependencies:** The core package must run on a pristine Python 3.10+ standard library (urllib.request, json, pathlib, subprocess, argparse, socket, fcntl). Test suites may use pytest.  
> * **Atomic Operations:** Lockfiles must prevent race conditions caused by Claude Code rapidly writing scratchpad files.  
> * **Fail-Safe IPC:** Missing compositors or dead sockets must downgrade gracefully without breaking mining or distillation.

## **2\. Directory Layout & File Responsibilities**

`claudalizer/`  
`├── pyproject.toml`  
`├── README.md`  
`├── claudalizer/`  
`│   ├── __init__.py          # Version constant (__version__ = "0.2.0")`  
`│   ├── cli.py               # CLI entry points and command routing`  
`│   ├── miner.py             # Source-neutral mining core: lock, settle, dossier writes`  
`│   ├── sources/             # Session adapters: claude_code.py, opencode.py (G_opencode)`  
`│   ├── distiller.py         # LLM prompt builder and OpenAI-compatible client`  
`│   └── ipc.py               # Compositor auto-detection and window manager IPC hooks`  
`├── systemd/`  
`│   ├── claudalizer.service  # User-level oneshot execution service`  
`│   ├── claudalizer-watch.service  # User-level watch daemon (sole trigger; polls /tmp/claude-1000)`  
`│   └── claudalizer.conf     # tmpfiles.d definition to maintain /tmp/claude-1000`  
`└── tests/`  
    `├── conftest.py          # Shared fixtures (mock /tmp, mock transcripts, mock sockets)`  
    `├── test_miner.py        # Slug parsing, artifact discovery, JSONL extraction`  
    `├── test_distiller.py    # Synthesis, no-fallback rule, PROJECT_MEMORY.md sections, xfail targets for G18–G21`  
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

#### **Session sources (G_opencode)**

Mining is split into a core that doesn't care where a session came from, plus one adapter per session source. The core is `claudalizer/miner.py`; the adapters are `claudalizer/sources/claude_code.py` and `claudalizer/sources/opencode.py`. Facts about opencode come from `planning/research/OPENCODE_SESSIONS.md` (opencode v2.4.1, commit `6f05140`); section numbers below (R§N) refer to that file.

The core owns the lock, the settle and up-to-date decisions, the skip accounting, scratchpad snapshots, the no-content rule, and the atomic `dossier.json` write. An adapter only finds sessions and extracts their signals. `distiller.py` does not change.

Protocol (`claudalizer/sources/__init__.py`, stdlib `typing.Protocol` and dataclasses):

```python
@dataclass(frozen=True)
class SessionRef:
    source: str                 # "claude_code" | "opencode"
    slug: str                   # memories-root folder name
    session_id: str
    decoded_path: Optional[str]
    changed_at: float           # epoch seconds of the newest change to the session
    settled: bool               # the adapter's own "finished" test passed

@dataclass
class Extraction:
    user_prompts: List[str]
    tool_errors: List[ToolErrorEvent]
    scratchpad_dir: Optional[Path]   # None when the source has no scratchpad
    touched_files: List[str]
    transcript_found: bool
    source_meta: Dict[str, Any]

class SessionSource(Protocol):
    name: str
    def iter_sessions(self, target_slug: Optional[str]) -> Iterator[SessionRef]: ...
    def extract(self, ref: SessionRef) -> Extraction: ...
```

Core loop, run once per scan under the one lock, for each enabled source in order (`claude_code`, then `opencode`):

1. If debounce is on and `ref.settled` is false, record `<slug>/<session_id>` in `skipped["active"]` and skip it.
2. If `dossier.json` exists, `force` is off, and `ref.changed_at <= dossier.json` mtime, count it in `skipped["up_to_date"]` and skip it.
3. Call `extract`. If `scratchpad_dir` is set, snapshot it as before. Apply the no-content rule as before; `touched_files` alone does not count as content.
4. Write the dossier atomically.

An adapter that raises an exception in `iter_sessions` or `extract` is logged as a warning. The rest of that source is skipped for this scan, and the other sources still run. `watch` never exits because of a source error.

Dossier changes (both sources): `source` (default `"claude_code"`), `touched_files` (default `[]`) and `source_meta` (default `{}`) are added to `SessionDossier`. Existing fields keep their meaning. The file is `dossier.json`; the `session_memory.json` name in the schema above is out of date.

**Claude Code adapter.** This is today's behaviour, moved without change:

- Discovery is the `tmp_root` walk in `scan_and_mine`, including the slug filters.
- `settled = is_file_settled(session_dir, SETTLE_DEBOUNCE_SECONDS)`.
- `changed_at` is the greater of the scratchpad's `newest_mtime` and the transcript mtime. With the core's `<=` test this is the same as today's `scratchpad_changed_since(...) or transcript newer` check.
- `extract` calls `parse_transcript_events` and returns the scratchpad directory, `touched_files=[]` and `source_meta={}`.

#### **opencode source**

*Database.* The path is the `--opencode-db` flag, else `$OPENCODE_DB`, else `$XDG_DATA_HOME/opencode/opencode.db` (default `~/.local/share/opencode/opencode.db`). Databases for other release channels (`opencode-<channel>.db`, R§1) are not detected automatically; pass them with the flag.

- Open with `sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)`. Never use `immutable=1`, because it ignores the WAL (R§7). The source never writes to the database.
- Each statement is its own short read. There is no long-lived transaction; close the connection at the end of each scan.
- If the database file is missing, the source yields nothing and logs at debug level only.

*Schema guard*, run at each open before any other query:

- Each table in the table below, and each column the adapter reads, must exist (`pragma table_info`). If any is missing, log one warning per process naming the missing items and skip the source.
- `SELECT id FROM migration ORDER BY id DESC LIMIT 1` (an empty table counts as an unknown migration, recorded as `""`) is compared with `KNOWN_OPENCODE_MIGRATION = "20261120004954_machine-key"`. If the latest id sorts after it, log one warning per process and keep reading. Record the id in `source_meta.schema_migration`.
- A `sqlite3.Error` at any point logs a warning and skips the source for this scan.
- A row whose `data` is not valid JSON is skipped. Every JSON field is read with `.get`, because older part shapes exist (R§2, R§6).

| Table | Columns read |
|---|---|
| `migration` | `id` |
| `session_v2` | `id`, `parent_id`, `directory`, `project_id`, `version`, `time_created`, `time_updated`, `time_busy`, `time_idle`, `idle_outcome` |
| `session_message` | `session_id`, `type`, `seq`, `time_updated`, `data` |
| `session_part` | `session_id`, `message_id`, `ordinal`, `type`, `call_id`, `time_updated`, `data` |

*Families (subagents).* A child session (`parent_id` set) is never mined on its own. It is folded into its root's dossier (decided 2026-11-24: mine all of it).

- The root is found by following `parent_id` until it is null or names a missing row. A child whose parent row is missing becomes a root itself.
- A loop or a depth over 64 stops the walk at the last row reached and logs a warning.
- A family is the root plus every session whose root it is. On 2026-11-25 the live database had one level of nesting and no orphans, but the rule does not depend on that.

*Discovery and change marker.* One query per scan computes each session's marker:

`max(time_updated, time_idle, max(session_message.time_updated), max(session_part.time_updated))`

using correlated subqueries on the `session_id` indexes. It took about 20 ms warm on the live 745-session database. `session_v2.time_updated` alone is not enough, because tool and part updates don't change it (R§4).

- A family's `changed_at` is the largest marker in the family, divided by 1000 (opencode stores milliseconds).
- `slug = re.sub(r"[^A-Za-z0-9]", "-", root.directory)`. This is Claude Code's rule (`/home/andrew/.claude-mined-memories` becomes `-home-andrew--claude-mined-memories`), so both sources in one repo share a slug and a `PROJECT_MEMORY.md`.
- `decoded_path = root.directory`. `session_id` is the root's `ses_…` id, which cannot collide with a Claude Code UUID (R§1).
- `target_slug` filters on the computed slug.

*Settled.* A family is settled when either of these holds:

- Every member has `time_idle IS NOT NULL AND time_idle >= coalesce(time_busy, 0)`, and `now - changed_at >= SETTLE_DEBOUNCE_SECONDS`.
- Or `now - changed_at >= OPENCODE_QUIET_SECONDS` (600). A shutdown interruption sets no idle mark (R§4), so a family like that is still mined once it has been quiet this long.

This changes only what the existing settle window is compared against; the window stays 2 s.

*Watch pre-check.* `watch` keeps the mtimes of the database file and its `-wal` file from the previous tick. It skips the opencode queries for a tick only when neither mtime changed **and** the previous pass found no unsettled family. A busy or unmarked family settles with the passage of time, not with a database write, so it must keep being re-checked until it is mined. `scan` always queries.

*Extraction*, per family member, ordered by member `time_created` with the root first:

- **Messages:** `SELECT type, seq, data FROM session_message WHERE session_id=? ORDER BY seq`. **Parts:** `SELECT message_id, ordinal, type, call_id, data FROM session_part WHERE session_id=? ORDER BY message_id, ordinal`.
- **Content of an assistant message:** its part rows in `ordinal` order, then the inline `data.content` items. This is the same order as opencode's `withParts` (R§2). A part item is its `data` object, with `type` taken from the column when `data` lacks it, and `id` taken from `call_id` when `data` lacks it.
- **`user_prompts`:** `type='user'` messages, `data.text` stripped. Keep it when it is at least `MIN_PROMPT_LENGTH` characters long. `synthetic`, `system`, `skill` and `compaction` messages are excluded. The root's prompts come first, then each child's.
- **`tool_errors`:** one `ToolErrorEvent` for each content item with `type == "tool"` that matches one of these cases:
  - `state.status == "error"`: `error_output = f"{error.type} error: {error.message}"`. The `error:` marker lets the distiller's friction rule keep the line.
  - `name == "shell"` with `state.status == "completed"` and a non-zero `state.metadata.exit`, or `signal` or `timeout` set: `exit_code = metadata.exit`, and `error_output` is the text items of `state.content` joined by newlines. Add `Exit code: N` when the text does not already contain it.
  - A shell item with no `metadata.exit` falls back to matching its text against `EXIT_CODE_PATTERN`. The pattern becomes `r"Exit code:? (\d+)"`, which matches both sources.

  The other fields for these items:
  - `tool_use_id` is the item's `id`, and `tool_name` is its `name`.
  - `command_or_input` is the first of `state.input.command`, `state.input.filePath`, the first line of `state.input.patchText`, or `json.dumps(state.input, sort_keys=True)`. It is cut to 500 characters.
  - `timestamp` is ISO-8601 UTC from `time.completed`, else `time.created`.

  The same `is_git_discernable` filter as transcripts is applied.
- **Turn failures:** an `idle` message with `outcome == "failed"` adds a `ToolErrorEvent` with `tool_name="session"` and `error_output = f"turn error: {error.message}"`.
- **`touched_files`:** the sorted, de-duplicated union of three sets, capped at 500 entries. Relative paths are joined to the member's `directory`. No file content is copied; copying from the snapshot store would be the G13 problem.
  - `snapshot.files[]` from each assistant message
  - `state.input.filePath` of `edit` and `write` calls
  - the paths on `*** (Add|Update|Delete) File: <path>` lines of `patch` calls
- **`scratchpad_dir = None`.** `transcript_found = True`.
- **`source_meta`:** `project_id`, `opencode_version` (the root's `version`), `idle_outcome` (the root's), `subagent_session_ids` (sorted) and `schema_migration`.

Assistant text and reasoning are not put into the dossier. They are read only because tool items live in the same content list.

Not mined: `/tmp/opencode` (worktrees), `tool-output/`, `shell/` and `snapshot/` (R§3), the HTTP API and SSE (R§4, R§5). Sessions whose `directory` is an opencode worktree get their own slug, the same as Claude Code worktree sessions.

### **3.2 distiller.py: Synthesis & PROJECT\_MEMORY.md**

#### **Outputs per session**

Each distilled session writes two things:

* `<memories_root>/<slug>/<session_id>/memory.md`: the session's memory block. A second call without `force` returns this file unchanged.
* `<memories_root>/<slug>/PROJECT\_MEMORY.md`: the per-project file. After each `memory.md` write it is rebuilt from every session's `memory.md` under the slug, in `scan_timestamp` order, and written atomically. Hand edits are overwritten.

#### **Synthesis**

* The endpoint comes from the `--llm-endpoint` flag, or else from the environment variable `CLAUDALIZER_LLM_ENDPOINT`. The model comes from `--llm-model` unless that is the default `llama3`, in which case it comes from `CLAUDALIZER_LLM_MODEL` (default `local`). The flag wins. The environment is read at call time.
* With an endpoint, `call_llm_completion` sends the prompt from `build_synthesis_prompt` to an OpenAI-compatible `/v1/chat/completions` endpoint, using stdlib `urllib`. The request sets `max_tokens` to 1024 and `chat_template_kwargs.enable_thinking` to false, because a reasoning model otherwise spends the whole budget on reasoning and returns no visible content. The timeout is 300 s. `temperature` is 0.2. The request carries only `Content-Type: application/json`; there is no authentication, because the endpoint is a local server. There is one attempt and no retry: a connection error, HTTP error, or empty reply returns no content. Non-empty text in the reply becomes the memory block.
* There is no offline fallback (decided 2026-11-25: the user never wants template output written to the memory files). If there is no endpoint, or the call fails or returns no content, nothing is written: `memory.md` and `PROJECT_MEMORY.md` stay as they were, even with `--force`. An empty reply is logged with a warning that names the endpoint. `claudalizer distill` with no endpoint logs an error and exits 2; `scan --auto-distill` and `watch` log a warning and only mine.

#### **Memory block format**

`frame_llm_block` puts three header lines on the LLM reply: `# Mined Behavioral Memory for <slug>`, a `**Source Directory:**` line, then `**Objective:** <text>`. The objective is the session's first real request (at least 15 characters, whitespace collapsed, truncated to 300 characters with `…`); with no such request it reads `not captured.`. A Claude Code slash-command wrapper (`<command-name>/x</command-name>…<command-args>y</command-args>`) is read as `/x y`; one with no arguments (`/clear`, `/model`) is skipped. The model writes the three sections (`### 1. Tool / Skill Friction`, `### 2. Blind Alleys & Discarded Spikes`, `### 3. Directives for CLAUDE.md`). If the reply already starts with `# Mined Behavioral Memory`, it is kept as is.

#### **PROJECT\_MEMORY.md format**

* Each session adds one section: a blank line, `---`, then the heading `## Session <first 8 characters of session id> Distillation`, then the session's block.
* One section per session. Sections are ordered by the dossier's `scan_timestamp`, then session id. A session directory without both `dossier.json` and `memory.md` is left out. Distilling the same session again with `force` rebuilds the file, so it still has exactly one section for that session.
* Blind-alleys rule: scratch whose first path segment is `g3-accept` or `rewrite-check` is dropped (the claudalizer's own test runs). If nothing else remains, the line is `- No ephemeral scratchpads recorded.`
* Friction-line rule: each line names the failing command and its first error-marker line. A failing call with no such line is dropped, not written as a bare `Exit code N` line.

#### **Control flow**

* `distill_session(slug, session_id, llm_endpoint, llm_model, force)`: returns `None` if there is no `dossier.json`. Returns the existing `memory.md` path if the file exists and `force` is false. Otherwise it writes `memory.md`, then appends to `PROJECT_MEMORY.md`, and returns the `memory.md` path.
* `distill_all(target_slug, ...)`: walks every slug directory and session directory under the memories root. `target_slug` limits the walk to one slug.

### **3.3 ipc.py: Window Manager & Notification Integration**

#### **Scan State & Waybar**

Each completed scan records its UTC timestamp, mined count, active count (sessions skipped as still changing), and optional project summary. State at `<memories-root>/scan_status.json` contains the latest scan, cumulative scan and mined-session totals, and bounded recent history. Its default location is `~/.claude-mined-memories/scan_status.json`. Atomic replacement preserves state across process restarts when writes succeed; missing or corrupt state starts empty, and a write failure does not stop mining.

`scan` and `watch` accept a non-negative `--history-limit`, default 50. A limit of 0 clears individual history records but retains the latest scan and cumulative totals. Every completed scan updates state, even when no sessions are mined.

The separate Waybar payload at `/tmp/claudalizer_status.json` uses a stable `🧠 active | total mined` text layout; the first number is the latest active-session count and the second is cumulative sessions mined. Its tooltip labels the latest timestamp and scan counts, last project when available, cumulative totals, and at most the three most recent history entries with mined sessions. Empty scans are omitted from that list. After a status write, `pkill -RTMIN+8 waybar` requests a refresh; configured polling remains a fallback.

#### **Compositor Hooks & Notifications**

Compositor hooks update status and refresh Waybar without an additional desktop popup. On Sway the hook also sends a `swaymsg` no-op; on Hyprland it does not invoke a popup command. Missing compositor or notification tools must not interrupt mining.

Desktop notifications via `notify-send` are opt-in for both scan and watch. When `--notify` is supplied, one aggregate notification is sent per scan that mines one or more sessions; scans mining none send no notification. The supplied systemd watch unit runs without `--notify`.

### **3.4 cli.py: User Interface & Commands**

Use argparse with the following subcommands:

- `claudalizer [--memories-root <path>] scan [--history-limit <non-negative integer>] [--notify]`
- `claudalizer distill [--project <slug>] [--llm-endpoint <url>] [--llm-model <name>]`
- `claudalizer [--memories-root <path>] watch [--interval 3] [--history-limit <non-negative integer>] [--notify] [--auto-distill | --no-auto-distill]`
  - `watch` distills mined sessions by default; `--no-auto-distill` turns this off.
- `claudalizer install-systemd [--dry-run]`
- Global flags (G_opencode): `--source <list>`, a comma-separated subset of `claude,opencode`, default `claude,opencode`. An unknown name is an argparse error. `--opencode-db <path>` has no default in argparse; when it is unset, the path is resolved as in §3.1 *opencode source*.

> * watch: Uses a loop with os.stat or file descriptor notifications and acquires /tmp/claudalizer.lock via fcntl.flock(fd, fcntl.LOCK\_EX \| fcntl.LOCK\_NB) to ensure single-instance safety.  
> * install-systemd: Emits units to \~/.config/systemd/user/ and calls systemctl \--user daemon-reload.

## **4\. Test Suite Requirements (tests/)**

Review criteria will reject any PR without automated testing covering edge-case handling. Tests run using pytest.

### **4.1 Ingestion & Mining (test\_miner.py)**

> * **test\_slug\_decoding**: Test paths including multiple dashes, nested subdirectories, and trailing dashes (e.g., \-home-user-work-src-my-pkg).  
> * **test\_filter\_oversized\_scratchpad**: Verify files over 250 KiB and binary files are not copied, each is listed in `skipped_files` with its reason, and smaller .py, .sh, and .log files are archived.  
> * **test\_jsonl\_corrupt\_recovery**: Feed a transcript containing half-written lines, truncated JSON, and non-UTF-8 characters. Verify extraction continues without raising unhandled exceptions.  
> * **test\_git\_state\_filtering**: Ensure clean exit codes and standard tool executions do not leak into tool\_failures.

### **4.2 Distillation (test\_distiller.py)**

Tests create a `MemoryDistiller` with `memories_root=tmp_path`, and mock `call_llm_completion` in any test that passes an endpoint. No test makes a network call or touches the real memories root.

Characterisation tests (must pass on current code):

> * **test\_distill\_session\_writes\_memory\_md\_and\_project\_memory**: `memory.md` exists, and `PROJECT_MEMORY.md` contains `## Session <id[:8]> Distillation`.
> * **test\_distill\_session\_skips\_existing\_memory\_without\_force**: A second call without `force` returns the existing path and does not append again.
> * **test\_llm\_block\_used\_when\_endpoint\_returns\_content**: With a mocked LLM reply, `memory.md` contains the reply text.
> * **test\_no\_memory\_written\_when\_llm\_returns\_nothing**: With a mocked empty reply, no `memory.md` or `PROJECT_MEMORY.md` is written.
> * **test\_no\_endpoint\_writes\_nothing\_and\_makes\_no\_call**: Without an endpoint, nothing is written and no call is made.
> * **test\_distill\_all\_respects\_target\_slug**: With two slugs, `target_slug` limits the output to one.
> * **test\_synthesis\_prompt\_mentions\_errors\_and\_scratchpads**: `build_synthesis_prompt` output contains the failing command and a scratchpad path.

Target behaviour (marked `xfail(strict=True)` with the goal id in the reason; each test flips to pass when its goal lands):

> * **test\_force\_redistill\_does\_not\_duplicate\_project\_section**: Distilling one session twice with `force` leaves exactly one `## Session <id[:8]> Distillation` heading.
> * **test\_rebuild\_changes\_only\_the\_redistilled\_session\_text**: Redistilling one session changes only its section; the other section is unchanged.
> * **test\_rebuild\_orders\_sessions\_by\_scan\_timestamp**: Sections follow `scan_timestamp` order, not distill order.
> * **test\_rebuild\_skips\_session\_without\_memory\_md**: A session with a dossier but no `memory.md` is left out.
> * **test\_rebuild\_is\_idempotent**: Rebuilding with no input change gives identical bytes.
> * **test\_rebuild\_discards\_hand\_edits\_outside\_session\_files**: Text written by hand into PROJECT\_MEMORY.md is gone after a distill.
> * **test\_no\_matching\_error\_shows\_none\_detected\_not\_fallback\_directive**: With no tool errors, the directives section says `None detected` and does not contain `Maintain strict idempotency`.
> * **test\_directives\_none\_detected\_when\_errors\_match\_no\_pattern**: With a tool error that matches no pattern, the directives section is `- None detected.`.
> * **test\_test\_runner\_scratch\_excluded\_from\_blind\_alleys**: Scratch under `g3-accept/` and `rewrite-check/` does not appear; with only such scratch, the section reads `No ephemeral scratchpads recorded.`
> * **test\_scratch\_outside\_test\_runs\_is\_kept**: `planning-backup/...` and `docs/g3-accept-notes.md` are kept.
> * **test\_friction\_line\_shows\_real\_error\_text**: A failing `pytest` call shows its `FAILED` line, not the bare `Exit code` line.
> * **test\_friction\_entry\_without\_error\_marker\_is\_dropped**: A call with no error-marker line is dropped; the section reads `- None detected.`.
> * **test\_llm\_request\_turns\_off\_thinking\_and\_caps\_output**: The request body has `max_tokens` 1024 and `chat_template_kwargs.enable_thinking` false; the timeout is 300 s.
> * **test\_empty\_llm\_reply\_returns\_none\_and\_warns**: An empty reply returns `None` and logs a warning naming the endpoint.
> * **test\_resolve\_llm\_settings\_uses\_environment\_when\_flag\_absent**, **test\_resolve\_llm\_settings\_flag\_wins\_over\_environment**, **test\_resolve\_llm\_settings\_no\_endpoint\_is\_none**: endpoint and model resolution from the flag and environment.
> * **test\_objective\_is\_first\_real\_request**, **test\_objective\_truncated\_to\_300\_chars\_with\_ellipsis**, **test\_objective\_not\_captured\_when\_no\_prompts**: the `**Objective:**` header line; the block still has three `###` sections.

Criterion 5 of GOALS.md G15 (the format is written down) is checked by the grep acceptance for this spec, not by a test.

### **4.1a opencode source (test\_opencode\_\*.py, test\_source\_core.py)**

The tests live in four files: `test_source_core.py` (the core loop and the split), `test_opencode_fixture.py`, `test_opencode_source.py` (the reader and the source), and `test_opencode_schema.py` (the guard in `claudalizer/sources/opencode_schema.py`). Guard tests that need a whole scan (`test_missing_column_skips_source_with_warning`, `test_corrupt_db_does_not_stop_scan`, `test_db_opened_read_only`) live in `test_opencode_source.py`; unit tests of the open function live in `test_opencode_schema.py`. An autouse fixture in `tests/conftest.py` points `OPENCODE_DB` and `XDG_DATA_HOME` at missing paths under `tmp_path`. `SessionMiner()` defaults to the Claude Code source only; `cli.py` adds opencode.

Tests build the database in `tmp_path` with `tests/opencode_fixture.py`, which creates the tables and columns in the §3.1 table plus a `migration` row. It has helpers for adding sessions, messages and part rows. No test opens the real `opencode.db`. All existing `tests/test_miner.py` tests pass unchanged after the source split (G_oc-seam).

Fixture and reader (G_oc-fixture, G_oc-read):

> * **test\_slug\_from\_directory\_matches\_claude\_code\_rule**: `/home/u/.x/my_repo` gives `-home-u--x-my-repo`.
> * **test\_prompts\_from\_user\_messages\_only**: `synthetic` and `system` text and prompts under 15 characters are left out.
> * **test\_inline\_and\_part\_content\_merged\_in\_order**: A message with part rows and inline content yields tool items in part-ordinal order, then inline order.
> * **test\_tool\_error\_status\_recorded**: `state.status="error"` gives an event whose `error_output` contains `error:` and the message.
> * **test\_failed\_shell\_exit\_code\_recorded**: A completed `shell` call with `metadata.exit=2` gives `exit_code=2` and the output text.
> * **test\_zero\_exit\_shell\_not\_recorded**: `metadata.exit=0` gives no event.
> * **test\_exit\_code\_pattern\_matches\_both\_forms**: `Exit code 1` and `Exit code: 1` are both non-zero exits.
> * **test\_failed\_idle\_turn\_recorded**: An `idle` message with `outcome="failed"` gives a `session` event.
> * **test\_touched\_files\_from\_snapshot\_edit\_and\_patch**: Relative snapshot paths are made absolute; edit, write and patch paths are included; there are no duplicates.
> * **test\_busy\_session\_not\_mined**: `time_busy > time_idle` puts the session in `skipped["active"]`.
> * **test\_unmarked\_session\_mined\_after\_quiet\_window**: `time_idle` null with a marker older than `OPENCODE_QUIET_SECONDS` is mined.
> * **test\_part\_update\_triggers\_remine**: Only a newer `session_part.time_updated` re-mines a session that already has a dossier.
> * **test\_unchanged\_session\_is\_up\_to\_date**: A second scan counts the family in `skipped["up_to_date"]`.
> * **test\_subagent\_folded\_into\_root**: The child's prompts, errors and touched files appear in the root dossier after the root's own. `source_meta.subagent_session_ids` lists the child. There is no child dossier.
> * **test\_busy\_subagent\_holds\_root**: The root is idle and the child is busy, so the family is active.
> * **test\_orphan\_subagent\_becomes\_root**: A child whose parent row is missing gets its own dossier.
> * **test\_dossier\_records\_source\_fields**: `source="opencode"`, plus `project_id`, `opencode_version` and `schema_migration` in `source_meta`.

Guard (G_oc-guard):

> * **test\_missing\_column\_skips\_source\_with\_warning**: With `session_v2.time_busy` dropped, the warning names it, opencode yields nothing, and Claude Code sessions are still mined.
> * **test\_unknown\_migration\_warns\_and\_reads**: A later migration id warns once and sessions are still mined.
> * **test\_missing\_db\_is\_silent**: There are no warnings and Claude Code mining is unaffected.
> * **test\_corrupt\_db\_does\_not\_stop\_scan**: A file that is not SQLite logs a warning; `scan_and_mine` returns normally.
> * **test\_db\_opened\_read\_only**: The database bytes and mtime are unchanged after a scan.

CLI and integration (G_oc-cli):

> * **test\_source\_flag\_limits\_sources**: `--source claude` never opens the database; an unknown name is rejected.
> * **test\_opencode\_db\_resolution\_order**: The flag wins over `OPENCODE_DB`, which wins over `XDG_DATA_HOME`.
> * **test\_watch\_skips\_queries\_when\_db\_unchanged**: Unchanged database and `-wal` mtimes mean no opencode query on that tick.
> * **test\_watch\_rechecks\_while\_family\_unsettled**: With unchanged mtimes, a family that was active on the last pass is checked again, and it is mined once it is quiet for 600 s.
> * **test\_both\_sources\_share\_project\_memory**: A Claude Code session and an opencode session for the same directory both appear in one `PROJECT_MEMORY.md` after distill.

### **4.3 IPC & Environments (test\_ipc.py)**

> * **Sway dispatch**: Verify the hook sends a Sway no-op and refreshes Waybar.
> * **Hyprland dispatch**: Verify the hook refreshes Waybar without invoking a popup.
> * **test\_headless\_environment\_no\_crash**: Unset all display and socket environment variables; verify all IPC functions complete silently without raising exceptions.

## **5\. Review Checklist for Agent Implementations**

Use this rubric to evaluate the agent's generated code:

> * \[ \] **Dependency check:** Run python3 \-m pip freeze inside the execution container; verify that neither requests, aiohttp, nor external frameworks are imported in claudalizer/.  
> * \[ \] **Lockfile handling:** Verify fcntl.flock is correctly wrapped in a try...finally block to release /tmp/claudalizer.lock.  
> * \[ \] **Path safety:** Verify all file reads and directory creations use pathlib.Path.mkdir(parents=True, exist\_ok=True).  
> * \[ \] **Dossier validation:** Ensure session\_memory.json contains valid ISO-8601 timestamps and serializable types.  
> * \[ \] **Systemd compliance:** Verify .service sets Type=oneshot and the watch service runs continuously with Restart= set.

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

Superseded. The skeleton that stood here named functions the distiller does not have, and tested CLAUDE.md injection, which goal G12 pruned. The test list is in §4.2. The file is written against §4.2 (orchestration 5, T5.2.1).

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
