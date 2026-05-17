# claude-code-agents

**Language:** [Русский](README.md) · English

Synchronised `~/.claude/` config for [Claude Code](https://claude.com/claude-code): hooks, slash-commands, skills, global instructions.

Mirrored across machines so the same agent behaviour follows you everywhere. Machine-local data (sessions, history, telemetry, IDE state, plugin cache) is `.gitignore`d.

## Quick start

```bash
git clone git@github.com:thothlab/claude-code-agents.git ~/.claude
```

That's the whole install — paths use `$HOME` so no per-machine patching needed. Full setup walkthrough in [INSTALL.md](INSTALL.md).

Daily sync (commit-locally-first, then pull/push):

```bash
~/.claude/sync.sh        # or  /sync  inside Claude Code
```

## What's inside

| Path | Purpose |
|---|---|
| `hooks/guard.py` | Mechanical invariants on every Bash/Write — blocks dangerous ops and unauthorised commit/push. See [Hooks](#hooks). |
| `commands/` | Slash-commands available as `/<name>` inside Claude Code. See [Commands](#commands). |
| `skills/` | Skills loaded by Claude Code on demand. |
| `CLAUDE.md` | Global instructions: project-reporting workflow (Obsidian), behavioural guidelines, techniques. |
| `INSTALL.md` | Setup on a fresh machine. |
| `settings.json` | Permissions, hook registration, status line, plugin marketplace config. |
| `sync.sh` | Strict pull+push helper used by `/sync`. |
| `statusline-command.sh` | Status line renderer. |

## Hooks

`hooks/guard.py` runs on every `Bash` and `Write` (PreToolUse) and on Bash/Read/Glob/Grep/WebFetch results (PostToolUse).

**Protective** — blocked unconditionally:
- Bypassing pre-commit hooks (`--no-verify`, `--no-gpg-sign`)
- Force-push on `main`/`master`
- Recursive deletion via `rm -rf`, wildcards in `rm`, absolute paths outside `/tmp`
- Filesystem search from the root (`find /`)
- Interactive flags requiring a TTY on `rebase`/`add`
- `--no-edit` on rebase, `-uall` on status

**Behavioural** — blocked unless the user explicitly authorised in this session:
- `git commit` — needs a keyword like `commit`/`коммит`/`закоммить`/`зафиксируй` or any push keyword anywhere in the session
- `git push` — needs `push`/`пуш`/`запушь`/`залей` or `git push` in the session
- Creating a new `*.md` via `Write` — needs an explicit doc-creation keyword in the last 5 user messages

Bypass-resistant: command is split on `;`, `&&`, `||`, `|`, backticks, `$()`; `git -C path commit` and similar global-option forms are caught.

Fail-open: any internal hook error allows the operation (a broken guard must not lock the user out of Claude Code).

Observability: every tool response size is appended to `hooks/tool-size.log` (gitignored).

## Commands

| Command | Purpose |
|---|---|
| `/sync` | Pull/push this repo via `sync.sh`; asks before auto-committing. |
| `/clean-arch` | Clean Architecture rules for Android / KMP / Compose Multiplatform. |
| `/mvvm-udf` | MVVM + Unidirectional Data Flow rules. |
| `/mvvm-udf-kmp` | MVVM + UDF tailored for KMP/CMP. |

Plus helper scripts not directly exposed as slash-commands:
- `commands/checkpoint-manager.sh`, `commands/standard-checkpoint-hooks.sh` — checkpoint utilities.
- `commands/github-safe.js` — guarded GitHub helper.

## Skills

| Skill | Purpose |
|---|---|
| `prd` | Create a detailed PRD and decompose a large initiative into task files + completion reports (`tasks/prd_XX_*`). |
| `skill-builder` | Build new Claude Code skills with proper YAML frontmatter, progressive disclosure, and complete directory layout. |

## Memory: agentmemory

Memory infrastructure is wired in via the MCP shim `@agentmemory/mcp`, declared in `~/.claude.json` (not in this repo — that file holds personal paths and tokens). Once installed, Claude Code gains tools `mcp__agentmemory__memory_save`, `memory_recall`, `memory_smart_search`, `memory_sessions`.

> ⚠️ **Do not confuse with the `rohitg00/agentmemory` plugin** (same name, GitHub repo). That plugin variant ships 12 hooks and is known to loop via the Stop hook ([issue #149](https://github.com/rohitg00/agentmemory/issues/149)) and burn API tokens. **Do not install it.** `settings.json` deliberately carries no `enabledPlugins`/`extraKnownMarketplaces` entries for it.

### Architecture (central server + tunnel)

1. **Server** `@agentmemory/agentmemory@0.9.4` on one machine (typically the home Mac mini under launchd `dev.agentmemory.server`):
   ```bash
   npx -y @agentmemory/agentmemory
   ```
   Listens on 3111/3112/3113. DB at `~/.agentmemory-server/data/`.

2. **Tunnel** on each client via autossh (under launchd `dev.agentmemory.tunnel`):
   ```bash
   autossh -M 0 -N -L 3111:127.0.0.1:3111 -L 3112:127.0.0.1:3112 -L 3113:127.0.0.1:3113 <ssh-alias-to-server>
   ```
   On this machine: `~/Library/LaunchAgents/dev.agentmemory.tunnel.plist`, target host `mac` (ProxyJump through VPS, see `~/.ssh/config`).

3. **MCP shim** in `~/.claude.json` (global or per-project):
   ```json
   "mcpServers": {
     "agentmemory": {
       "type": "stdio",
       "command": "npx",
       "args": ["-y", "@agentmemory/mcp"],
       "env": {}
     }
   }
   ```

### Scope marking (mandatory for `memory_save`)

agentmemory has no built-in per-project filter — every memory is visible through recall from every project. To prevent memories from project A leaking as advice into project B, each `memory_save` must begin its `content` with a scope marker on the first line:

- `[scope: project:<name>]` — this project only
- `[scope: cross-project / <stack>]` — for a group (`cross-project / android / kmp`)
- `[scope: universal]` — everywhere

Plus a scope tag in `concepts` (`scope-project-<name>` / `scope-cross-project` / `scope-universal`). Full rules in [CLAUDE.md, "Память" section](CLAUDE.md). Operational details (launchd plists, tunnel troubleshooting, REST API) live in the Obsidian notes under `Projects/AgentMemory/`.

### Local fallback

If you don't have a central server, you can run the server on the same machine as the MCP shim (no tunnel needed, MCP hits localhost). **Don't use this as a "temporary solution while the central server is unavailable"** — it creates DB divergence between machines.

## What is *not* synced

The `.gitignore` keeps machine-local and ephemeral data out: `sessions/`, `history.jsonl`, `cache/`, `telemetry/`, `statsig/`, `ide/`, `config/`, `plugins/`, `agents/`, `projects/`, `todos/`, `tasks/`, `plans/`, `debug/`, `file-history/`, `checkpoints/`, `downloads/`, `backups/`, `paste-cache/`, `shell-snapshots/`, `session-env/`, `settings.local.json`, `stats-cache.json`, `mcp-needs-auth-cache.json`, `.last-cleanup`, `hooks/tool-size.log`, `hooks/__pycache__/`, `image-cache/`.

If a machine grows a new local artefact that doesn't deserve syncing, add it to `.gitignore`.

## Branches

`main` is the shared base — everything in it should make sense on every machine. Per-machine personal tweaks (model preference, hardcoded usernames, experimental settings) can live in `<hostname>-personal` branches that periodically merge `main` and stay outside it.

## License

MIT — see [LICENSE](LICENSE).
