# Mining opencode sessions in claudalizer

Researched: 2026-11-24. Question: how could claudalizer mine opencode sessions as well as Claude Code sessions?

Sections 1 to 6 hold facts, each with a link to a primary source. Section 7 is a recommendation and is labelled as one. Anything that a primary source does not confirm is marked **UNVERIFIED**.

Short link prefix used below: `OC` = `https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96` (tag `v2.4.1`).

## Summary

- opencode 2.x keeps every session in **one SQLite database**, `~/.local/share/opencode/opencode.db` (WAL mode). There are no per-session files. Python's stdlib `sqlite3` can read it in read-only mode, so the stdlib-only rule still holds.
- The tables that matter are `session_v2` (one row per session, holding `directory`, `project_id`, `parent_id` and `time_busy`/`time_idle`/`idle_outcome`), `session_message` (typed JSON `data` per message) and `session_part` (assistant content split into rows). **Assistant content can be in either place**: inline in `session_message.data.content` (older rows, 32,037 of them here) or in `session_part` rows. A reader has to merge the two the way opencode's own `withParts` does.
- User prompts are `session_message.type = 'user'` and `data.text`. Tool calls are assistant content items with `type: "tool"`, `name`, `state.input` and `state.status`. A tool error is `state.status = "error"` with `state.error.{type,message}`. **A failed shell command is not an error status**: it is `status: "completed"` with a non-zero `state.metadata.exit`.
- There is **no per-session scratchpad**. The nearest things are global or per-project: `tool-output/` (large tool results, 7-day retention), `shell/<projectID>/` (shell output), `snapshot/<projectID>/<hash>` (a git object store of the work tree) and `worktree/`.
- A good "finished" signal is in the data: `session_v2.time_idle >= time_busy`, set when an execution succeeds, fails or is interrupted. Each turn also ends with a `session_message` row of `type = 'idle'`. An SSE stream (`GET /api/event`) exists, but its spec calls it volatile, and using it needs the background service and its password.
- None of the access paths is a stable contract. The HTTP API calls itself "Experimental HttpApi surface", and export sits under `/api/experimental/`. The database had about 64 migrations in 2026, including one that reset session state and one that moved assistant content into a new table (2026-10-29).
- Project identity is a hash of the normalised git `origin` URL, then a cached ID in `.git/opencode`, then the root commit SHA, then `"global"`. It is **not** a path. To match claudalizer's path-based slugs, use `session_v2.directory`.
- opencode 2.4.1 is installed on this machine, with 716 sessions (597 of them subagent sessions), 38,582 messages and 34 projects. The v1 legacy tables are empty, so the v1 to v2 migration has finished.

## Sources examined

| Source | Version / ref | Use |
|---|---|---|
| `github.com/anomalyco/opencode` (the `sst/opencode` name redirects here; default branch `dev`) | tag **v2.4.1** = commit `6f0514052a3c859894ad01bb14cc14dda1e44b96`, released 2026-11-23. `dev` HEAD at research time: `3e858dfc11a4` (2026-11-25T01:41Z, not used) | All source citations |
| `packages/protocol/openapi.json` (OpenAPI 3.1.0, `info.version` 0.0.1) | v2.4.1 | HTTP API |
| Official docs source (`services/site/src/docs/content/*.mdx`, published at opencode.ai/docs) | v2.4.1 | Paths, CLI, migration notes |
| Older tags `v1.0.0` (`b9a39b8`) and `v1.2.0` (`ffc000d`) | | Storage format history |
| Local install `~/.opencode/bin/opencode` | `opencode v2.4.1` | Section 6 (read-only, keys only) |

How the sources were read: through the GitHub API (`gh api .../contents?ref=<sha>`). A local clone failed because `/tmp` (tmpfs, 55G) is **100% full**. That matters for claudalizer too (see Open questions).

## 1. Where opencode stores sessions on disk

**Paths.** opencode uses XDG roots for app name `opencode`: `data`, `cache`, `config`, `state`, `tmp`, plus `log = data/log`, `repos = data/repos`, `bin = cache/bin` ([OC/packages/util/src/global.ts#L12-L27](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/util/src/global.ts#L12-L27)). On Linux that is `~/.local/share/opencode`, `~/.local/state/opencode`, `~/.config/opencode` and `~/.cache/opencode`. The docs give the database as `~/.local/share/opencode/opencode.db`, overridable with `OPENCODE_DB`. They also list the service registration `~/.local/state/opencode/service.json`, the private service config `~/.config/opencode/service.json`, and the warning "Do not delete or edit service files or the database" ([OC/services/site/src/docs/content/troubleshooting.mdx#L202-L227](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/troubleshooting.mdx#L202-L227)).

**Database filename depends on the release channel.** It is `opencode.db` for the `latest`/`dev`/`beta`/`next`/`prod` channels, and `opencode-<channel>.db` for any other channel, unless `OPENCODE_DB` or `OPENCODE_DISABLE_CHANNEL_DB` is set ([OC/packages/cli/src/database-path.ts#L4-L13](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/cli/src/database-path.ts#L4-L13)).

**Format.** SQLite through Drizzle. The schema is in `packages/core/src/session/sql.ts`, and every row carries `time_created`/`time_updated` as epoch milliseconds (`Date.now()`) ([OC/packages/core/src/database/schema.sql.ts#L3-L10](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/database/schema.sql.ts#L3-L10)). The local database is in WAL mode (section 6).

**Layout (tables):**
- `session_v2`: `id`, `project_id` (FK `project.id`), `workspace_id`, `parent_id` (subagent parent), `fork_session_id`, `slug` (a short human slug, **not** a path), `directory` (absolute path), `path`, `title`, `version` (the opencode version that wrote it), cost and token columns, `agent`, `model` (JSON), `time_created`, `time_updated`, `time_busy`, `time_idle`, `time_viewed`, `idle_outcome`, `time_compacting`, `time_archived`, `time_suspended` ([OC/packages/core/src/session/sql.ts#L28-L84](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/sql.ts#L28-L84)).
- `session_message`: `id`, `session_id`, `type`, `seq` (unique per session), timestamps, `data` JSON ([#L86-L105](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/sql.ts#L86-L105)).
- `session_part`: PK (`message_id`, `ordinal`), `session_id`, `type`, `call_id` (the tool call id), timestamps, `data` JSON ([#L107-L128](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/sql.ts#L107-L128)).
- `blob` / `blob_ref`: binary attachments that messages reference as `media:<sha256>` ([#L185-L215](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/sql.ts#L185-L215); [OC/packages/core/src/session/stored.ts#L10-L21](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/stored.ts#L10-L21)).
- `project`: `id`, `worktree` (canonical absolute directory), `vcs`, `name`, timestamps, `sandboxes` ([OC/packages/core/src/project/sql.ts#L12-L29](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/project/sql.ts#L12-L29)).

**IDs.** Session IDs start with `ses_` ([OC/packages/schema/src/session-id.ts#L5-L11](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-id.ts#L5-L11)) and message IDs with `msg_` ([OC/packages/schema/src/session-message.ts#L21-L28](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L21-L28)). Neither can collide with a Claude Code UUID.

**Project ID derivation** (for git: [OC/packages/core/src/project.ts#L309-L383](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/project.ts#L309-L383)), in this order:
1. `Hash.fast("git-remote:" + host/path)` of the normalised `origin` URL.
2. Otherwise a cached ID read from the file `opencode` in the git common directory (`.git/opencode`).
3. Otherwise the first root commit SHA.
4. Otherwise `"global"` ([OC/packages/schema/src/project-id.ts#L4-L8](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/project-id.ts#L4-L8)).

Mercurial uses the cached ID or the first root changeset ([project.ts#L391-L420](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/project.ts#L391-L420)). Clones and worktrees of the same repository therefore **share one project ID** (the comment at [#L156](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/project.ts#L156) says so). The working directory of each session is in `session_v2.directory`.

**Storage migrations (history):**
- **v1.0.0: JSON files** under `~/.local/share/opencode/storage/`, keyed paths such as `session/<projectID>/<id>.json`, `message/<sessionID>/<id>.json`, `part/<messageID>/<id>.json`, with a `storage/migration` counter ([OC@v1.0.0 packages/opencode/src/storage/storage.ts#L76-L134](https://github.com/anomalyco/opencode/blob/b9a39b816c92592e824c68cdc9a48acf7717e2a2/packages/opencode/src/storage/storage.ts#L76-L134)).
- **By v1.2.0: SQLite**, with a one-shot JSON to SQLite import that scans `project/*.json`, `session/*/*.json`, `message/*/*.json` and `part/*/*.json` into the tables `session`, `message` and `part` ([OC@v1.2.0 packages/opencode/src/storage/json-migration.ts#L25-L120](https://github.com/anomalyco/opencode/blob/ffc000de8e446c63d41a2e352d119d9ff43530d0/packages/opencode/src/storage/json-migration.ts#L25-L120)).
- **v2.x: `session_v2` / `session_message` / `session_part`.** A v1 to v2 migration copies the legacy `session`/`message`/`part` rows into the new tables ([OC/packages/core/src/database/v1-migration.bun.ts#L500-L510, L611-L725](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/database/v1-migration.bun.ts#L500-L725)). It can also import from `opencode-next.db` ([#L799-L803](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/database/v1-migration.bun.ts#L799-L803)).
- **Within 2.x the schema keeps changing**: there are about 90 migration files under `packages/core/src/database/migration/` (2026-01-27 to 2026-11-20). They include `20260622170816_reset_v2_session_state`, `20261029002625_session_part` (which creates `session_part`, [link](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/database/migration/20261029002625_session_part.ts#L8-L25)) and `20261029073502_session_time_busy`.
- The v2 docs say the upgrade has "breaking changes to plugins, the server API, and terminal client configuration" ([OC/services/site/src/docs/content/migrate-v1.mdx#L3](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/migrate-v1.mdx#L3)).

## 2. Schema: sessions, messages, parts

Message variants come from `SessionMessage.Info`. They are `agent-switched`, `model-switched`, `location-switched`, `user`, `synthetic`, `system`, `skill`, `shell`, `assistant`, `compaction` and `idle` ([OC/packages/schema/src/session-message.ts#L311-L323](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L311-L323)). In the database, the variant tag is the `session_message.type` column. `id` and `type` are removed from `data` ([OC/packages/core/src/session/sql.ts#L21-L25](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/sql.ts#L21-L25)).

| What claudalizer needs | opencode location and field names |
|---|---|
| **User prompt** | `session_message.type='user'`; `data.text`, plus `data.files`, `data.agents`, `data.skills`, `data.time.created` ([session-message.ts#L76-L85](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L76-L85)) |
| Injected, non-user text (exclude) | `type='synthetic'` (`text`, `description`), `type='system'` (`text`, `description`) ([#L94-L110](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L94-L110)) |
| **Assistant message** | `type='assistant'`; `data.agent`, `data.model`, `data.content[]`, `data.snapshot.{start,end,files[]}`, `data.finish`, `data.error`, `data.time.{created,completed}` ([#L222-L252](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L222-L252)) |
| Assistant text | content item `{type:"text", text}` ([#L186-L192](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L186-L192)); reasoning is `{type:"reasoning", text}` ([#L194-L203](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L194-L203)) |
| **Tool call** | content item `{type:"tool", id, name, executed?, state, time:{created,ran?,completed?}}` ([#L171-L184](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L171-L184)). The call and its result are **the same object**: there is no separate result block to match by ID, unlike Claude Code's `tool_use`/`tool_result`. |
| **Tool result** | `state.status` is one of `streaming` / `running` / `completed` / `error`. A completed call has `state.input` (object), `state.content[]` (`{type:"text",text}` or `{type:"file",uri,mime,name?}`) and `state.metadata` ([#L136-L169](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L136-L169); [OC/packages/schema/src/tool.ts#L90-L106](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/tool.ts#L90-L106)) |
| **Tool error** | `state.status="error"`, `state.error: {type, message, status?, response?.body?, retryAfterMs?}` ([OC/packages/schema/src/session-error.ts#L6-L14](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-error.ts#L6-L14)) |
| **Failed shell command** | The `shell` tool returns `metadata.status` plus `ShellResult.metadata(output)`, and the model-facing output has `exitCode` ([OC/packages/core/src/tool/plugin/shell.ts#L86-L88, L120-L135](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/tool/plugin/shell.ts#L86-L135)). The notice text is `Exit code: N` **with a colon**, emitted for a non-zero exit, a signal or a timeout ([OC/packages/core/src/shell/result.ts#L51-L57](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/shell/result.ts#L51-L57)). claudalizer's `EXIT_CODE_PATTERN = r"Exit code (\d+)"` does **not** match that text. |
| User `!` shell | `type='shell'`; `command`, `status`, `exit?`, `output?` ([#L121-L134](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L121-L134)) |
| Turn end | `type='idle'`; `outcome` is `succeeded`, `failed` or `interrupted`, plus `error?` ([#L298-L309](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-message.ts#L298-L309)) |

**Where assistant content lives.** The projector writes assistant content to `session_part` rows when `experimental.part_rows` is not `false`. That is the default. It then stores `content: []` in the message envelope ([OC/packages/core/src/session/projector.ts#L320-L324, L507-L558](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/projector.ts#L320-L558)). Legacy rows keep their content inline. The reader `withParts` puts the part rows, in `ordinal` order, into `data.content`, followed by any inline content ([OC/packages/core/src/session/history.ts#L90-L122](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/history.ts#L90-L122)). Part rows also go through `SessionLegacy.part(...)` before decoding ([#L133-L134](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/history.ts#L133-L134)), which means some stored part shapes are older than the current schema.

## 3. Analogue of the Claude Code scratchpad

The source has **no per-session scratch directory**. These are the nearest equivalents, all under `~/.local/share/opencode/`:

- `tool-output/tool_<id>`: tool results too large to send inline (over 2,000 lines or 50 KiB), kept 7 days. The directory is global, not per-session ([OC/packages/core/src/tool-output.ts#L13-L16, L40-L63](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/tool-output.ts#L13-L63)).
- `shell/<projectID>/`: shell command output files, kept 7 days ([OC/packages/core/src/shell.ts#L49, L192, L355](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/shell.ts#L49)).
- `snapshot/<projectID>/<Hash.fast(worktree)>`: a separate git repository holding work-tree snapshots ([OC/packages/core/src/snapshot.ts#L92-L98](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/snapshot.ts#L92-L98)). Each assistant message points to it through `data.snapshot.start` / `end` / `files[]` (the files touched in that step).
- `worktree/`: git worktrees that opencode manages (strategies in `packages/core/src/worktree/`).

For a dossier, the closest "files the session produced" signal is the union of `assistant.data.snapshot.files[]` plus the inputs of `write`/`edit`/`patch` tool calls. Mapping a `tool-output/` file back to a session is **UNVERIFIED**: the file name is an ID, and I did not trace where the session records that path.

## 4. Liveness and "session finished" signals

- **Database columns.** `session.execution.started` sets `time_busy`. `succeeded`, `failed` and `interrupted` set `time_idle` (strictly increasing) and `idle_outcome`. A shutdown interruption does **not** set idle. Neither handler bumps `time_updated` ([OC/packages/core/src/session/projector.ts#L840-L866, L1066-L1074](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/projector.ts#L840-L1074)). `touch` sets `session_v2.time_updated` ([#L86-L88](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/projector.ts#L86-L88)), but it runs only for some events: inbox enqueue, step started, and some step failures ([#L1041-L1080](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/projector.ts#L1041-L1080)). It does not run on every text, tool or part update. Each `session_message` and `session_part` row has its own `time_updated`. Interrupt reasons are `user`, `shutdown`, `superseded` and `inactivity` ([OC/packages/schema/src/session-event.ts#L244-L264](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-event.ts#L244-L264)).
- **Idle marker message.** Each turn ends with a `session_message` row of `type='idle'` (section 2).
- **Ephemeral bus events.** `session.status`, with `status.type` of `idle`, `busy` or `retry`, and the deprecated `session.idle` ([OC/packages/schema/src/session-status-event.ts#L9-L53](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/schema/src/session-status-event.ts#L9-L53)).
- **SSE.** `GET /api/event?types=...` returns `text/event-stream` with a heartbeat comment every 15 s ([OC/packages/server/src/handlers/event.ts#L18-L27](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/server/src/handlers/event.ts#L18-L27)). The spec says: "Volatile by contract: a slow consumer overflows and fails the stream, and events during disconnection are missed" ([OC/packages/protocol/openapi.json#L10244](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/protocol/openapi.json#L10244)). `GET /api/session/active` lists sessions that this process is currently running ([openapi.json#L1427](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/protocol/openapi.json#L1427)). `POST /api/experimental/session/{id}/wait` also exists.
- **Plugins.** v2 plugins subscribe with `ctx.event.subscribe()`, which replaces the v1 `event` hook ([OC/services/site/src/docs/content/build/plugins/migrate-v1.mdx#L92, L149](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/build/plugins/migrate-v1.mdx#L92)). V1 plugins do not run in v2 ([migrate-v1.mdx#L601](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/migrate-v1.mdx#L601)). A plugin would be TypeScript running inside opencode.
- **Stdlib fit.** SSE over `urllib.request` is just reading lines from a long response, so it adds no dependency. It does require the service to be running, plus HTTP Basic auth: username `opencode`, password from `OPENCODE_PASSWORD` or the registration file ([migrate-v1.mdx#L615-L628](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/migrate-v1.mdx#L615-L628); [OC/packages/client/src/service.ts#L1-L57](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/client/src/service.ts#L1-L57)). The registration file is `$XDG_STATE_HOME/opencode/service.json` ([OC/packages/client/src/service-probe.ts#L40](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/client/src/service-probe.ts#L40)). Polling the database read-only with stdlib `sqlite3` needs none of that.

## 5. Official programmatic access

- **CLI.** The documented commands are `opencode session list [--max-count N] [--format json]` and `opencode session export <id> [--sanitize]` ([OC/services/site/src/docs/content/cli/commands.mdx#L126-L150](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/cli/commands.mdx#L126-L150)), plus `opencode serve` and `opencode api GET /api/session` ([#L379-L397, L510-L534](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/cli/commands.mdx#L379-L534)).
  - Both session commands connect to the server (`ServerConnection.resolve()`).
  - `list` is scoped to the project of the current directory. Its JSON output has `id`, `title`, `updated`, `created`, `projectId` and `directory` ([OC/packages/cli/src/commands/handlers/session/list.ts#L13-L43](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/cli/src/commands/handlers/session/list.ts#L13-L43)).
  - `export` calls `client.experimental.session.export` ([export.ts#L70-L74](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/cli/src/commands/handlers/session/export.ts#L70-L74)), which returns `{data: SessionTransfer.Data{info, messages}}`.
- **HTTP API** (`openapi.json`, whose `info.description` reads "Experimental HttpApi surface for selected instance routes"):
  - `GET /api/session` takes `limit`, `order`, `search`, `parentID`, `archived`, `directory`, `project`, `subpath` and `cursor` ([#L856](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/protocol/openapi.json#L856)).
  - `GET /api/session/{id}/message` returns projected messages and takes a `type` filter and a cursor ([#L4770](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/protocol/openapi.json#L4770)).
  - `GET /api/experimental/session/{id}/export` ([#L1340](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/protocol/openapi.json#L1340)).
  - `GET /api/project` and `GET /api/event`.
- **SDK.** The docs say to use `@opencode/client` for "the released V2 API" ([migrate-v1.mdx#L607-L613](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/migrate-v1.mdx#L607-L613)). It is TypeScript, so claudalizer cannot use it.
- **Stability.** No source promises a stable contract:
  - The HTTP surface is labelled experimental, and export sits under `/experimental/`.
  - The v1 to v2 change broke the server API on purpose ([migrate-v1.mdx#L609-L610](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/services/site/src/docs/content/migrate-v1.mdx#L609-L610)).
  - The database schema has changed repeatedly (section 1), and the docs say not to *edit* it (reading it is not addressed).
  - The typed message schema (`SessionMessage.Info`) is the shape shared by the database `data` column and the API's projected messages, so a parser written against it should work on either source. **UNVERIFIED**: I did not diff the API response schema against the stored JSON field by field.

## 6. Local install (read-only check, keys only)

- `which opencode` gives `/home/andrew/.opencode/bin/opencode`; `opencode --version` gives `opencode v2.4.1`.
- `~/.local/share/opencode/` holds `opencode.db` (about 406 MB, plus `-wal` about 17 MB and `-shm`), `log/`, `repos/` (empty), `shell/` (32 project dirs), `snapshot/` (25), `tool-output/` (34 files), `worktree/` (5). There is no `storage/` directory, so no v1.0 JSON era data remains.
- `~/.local/state/opencode/` holds `service.json`, `prompt-history.jsonl` (keys: `agents`, `files`, `mode`, `pasted`, `skills`, `text`), `frecency.jsonl`, `model.json`, `locks/` and `pty/`.
- `~/.config/opencode/` holds `opencode.jsonc`, `service.json` (mode 600, not opened), `package.json` and `node_modules/`.
- Database (opened with `?mode=ro` from Python stdlib `sqlite3` 3.45.1, journal mode `wal`):

  | Item | Value |
  |---|---|
  | Rows | `session_v2` 716, `session_message` 38,582, `session_part` 1,822, `project` 34, `worktree` 162 |
  | Legacy tables | `session`/`message`/`part` 0 rows; `kv` has `migration.v1-v2` |
  | Last applied migration (`migration` table, 64 rows) | `20261120004954_machine-key`, the last migration file in v2.4.1 |
  | Message types | assistant 33,074; idle 2,363; user 2,324; synthetic 592; system 143; compaction 50; shell 14; model-switched 12; location-switched 10 |
  | Assistant content | 32,037 assistant rows still hold **inline** content; part rows: tool 1,252, reasoning 365, text 205 |
  | Tool states | Mostly `completed`. Errors (`state.error.type`): `tool.execution` 91, `unknown` 18, `aborted` 9, `provider.invalid-output` 2 (inline sample of 5,000 rows) |
  | Shell tool | `state.metadata` keys `status`, `truncated`, `exit`, `shellID`, `timeout`, `signal`; `state.input` keys `command`, `timeout`, `workdir`, `background` |
  | Sessions | `idle_outcome`: succeeded 691, failed 15, interrupted 8, null 2. No session had `time_busy > time_idle` at check time. **597 of 716 sessions have a `parent_id`** (subagents). Session `version` values range from 2.0.18 to 2.4.1. |

- Schema drift shows in the stored rows. The keys of a stored `compaction` message include `providerState` and `recent`, which `SessionMessage.Compaction` at v2.4.1 does not define. (The history reader carries a comment about `providerContext` rows from before v2.1: [history.ts#L73-L74](https://github.com/anomalyco/opencode/blob/6f0514052a3c859894ad01bb14cc14dda1e44b96/packages/core/src/session/history.ts#L73-L74).)
- `~/.local/state/opencode/service.json` has keys `id`, `password`, `pid`, `url`, `version`. Its permissions are `-rw-rw-r--` (mode 664), so other local users can read it, and it holds the service password. I did not read the values.

## 7. Recommendation (not sourced fact)

**Read the database in read-only mode.** Do not depend on the HTTP API or the CLI.
- This keeps the current design (poll local files, no running service, no secrets) and works when opencode is not running.
- `sqlite3.connect("file:...opencode.db?mode=ro", uri=True)` reads WAL databases safely while opencode writes. Do not use `immutable=1`, because that ignores the WAL.
- Set a busy timeout. Run one bounded transaction per scan.
- Keep an optional HTTP backend (urllib) only as a fallback if the schema guard fails.

**Module boundaries.**
- Split `miner.py` into a source-neutral core and source adapters. The shared parts stay in the core: the lock, dossier writing, `is_git_discernable`, `SessionDossier`, the skip accounting and the snapshot copying.
- Add a small `SessionSource` protocol: `iter_sessions() -> (slug, session_id, decoded_path, changed_marker)`, `is_settled(session)`, and `extract(session) -> (prompts, tool_errors, files)`.
- Move today's code into `sources/claude_code.py` and add `sources/opencode.py`.
- `SessionMiner.scan_and_mine` loops over the enabled sources. CLI flags would be `--source claude,opencode` and `--opencode-db` (default `$OPENCODE_DB`, else `$XDG_DATA_HOME/opencode/opencode.db`).
- `distiller.py` needs no change, because it only reads the dossier fields.

**Identity and slugs.** Build claudalizer's slug from `session_v2.directory` with the Claude Code rule (`/` becomes `-`, leading `-`). opencode and Claude Code sessions in the same repository then land in the same `~/.claude-mined-memories/<slug>/` folder and feed one `PROJECT_MEMORY.md`. Keep `session_id` as the `ses_...` ID (it cannot collide). Add `source: "opencode"`, `project_id` and `opencode_version` to the dossier. Do not use opencode's `project_id` or `slug` as claudalizer's slug: `project_id` is remote-hash based and shared across clones, and opencode's `slug` is a short display name.

**Extraction rules.**
- `user_prompts`: `session_message` rows with `type='user'`, ordered by `seq`, taking `data.text`. Apply the existing `MIN_PROMPT_LENGTH` filter. Skip `synthetic` and `system`.
- `tool_errors`: assistant content after the merge (part rows by `ordinal`, then inline `data.content`). Take each `type=='tool'` item where:
  - `state.status=='error'`, with `error_output` set to `state.error.message`; or
  - `name=='shell'` and `state.metadata.exit` is non-zero (or `signal` or `timeout` is set), with `exit_code` set to `metadata.exit`.

  Map `tool_use_id` to `id`, `tool_name` to `name`, `command_or_input` to `state.input.command` (or `filePath` or a JSON dump), and `timestamp` to `time.completed`. Extend `EXIT_CODE_PATTERN` to `Exit code:? (\d+)` for any text fallback.
- Treat `idle` messages with `outcome='failed'` as session-level errors.
- `scratchpad_files`: no direct equivalent. Record `touched_files` (the union of `snapshot.files[]` and the paths of edit, write and patch calls) as a list, without copying content. Copying from the snapshot git repository would bring back the G13 problem.

**Subagents.** Fold child sessions (`parent_id` set) into their root session's dossier, or skip them. They are 83% of sessions here and would flood `PROJECT_MEMORY.md` with dossiers that hold no human prompts.

**Settle and re-mine rule.**
- A session is settled when `time_idle IS NOT NULL AND time_idle >= coalesce(time_busy, 0)` and `now - marker >= SETTLE_DEBOUNCE_SECONDS`, where `marker` is the change marker defined below.
- A session interrupted by shutdown has no idle mark, so fall back to quiet time: no `time_updated` change for N minutes.
- Re-mine when the change marker is newer than the `dossier.json` mtime. The marker is `max(session_v2.time_updated, time_idle, max(session_message.time_updated), max(session_part.time_updated))` for that session. `session_v2.time_updated` alone misses tool and part updates (section 4). Use one `SELECT` per scan instead of statting files.
- The DB `-wal` file mtime is a cheap "anything changed" pre-check for the watch loop.
- The settle window value itself is ask-first under AGENTS.md. This rule only changes what the window is compared against.

**Schema guard.** At open, read `SELECT id FROM migration ORDER BY id DESC LIMIT 1` and check that the tables and columns the adapter uses exist (`pragma table_info`).
- On an unknown newer migration, still try to read, but log a warning.
- On missing columns, skip the opencode source with a clear message. Do not crash the watch loop.
- Pin fixtures from a sanitised real database for the tests (build them with `sqlite3` in `tmp_path`; never touch the live database).

**Risks.**
- The schema changes fast (the part split was four weeks before this research).
- The channel-specific database filename.
- The large database (406 MB): always query by index (`session_message_session_seq_idx`, `session_part_session_message_idx`) and never scan full tables.
- Legacy part shapes that opencode normalises with `SessionLegacy.part`: read fields defensively with `.get`.
- WAL growth while a long read transaction is open: keep transactions short.
- The AGENTS.md rule "never modify `~/.claude-mined-memories` directly" still holds, and the new source must never write to `opencode.db`.

## Open questions

The design decisions are recorded in `planning/SPEC.md` §3.1 (*Session sources*, *opencode source*) and §4.1a.

- ~~`/tmp` is a 55G tmpfs at 100% use.~~ Resolved 2026-11-25: `/tmp` is at 1% use; the full disk was transient.
- Does `GET /api/session/{id}/message` return exactly the stored `data` shapes, or a projection? (**UNVERIFIED**; see section 5.)
- Can a `tool-output/tool_*` file be traced to its session, by a path recorded in tool metadata (`outputPath`)? Not traced.
- How does `opencode session export --sanitize` redact data? It could be a safer input for LLM distillation. Not read.
- Should claudalizer's distilled memories ever be injected back into opencode (instructions or skills)? That is outside this question, but relevant to deferred goal G22.
- Changing the `~/.local/state/opencode/service.json` permissions (664, holds a password) is the user's decision and outside claudalizer.
