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

## What is *not* synced

The `.gitignore` keeps machine-local and ephemeral data out: `sessions/`, `history.jsonl`, `cache/`, `telemetry/`, `statsig/`, `ide/`, `config/`, `plugins/`, `agents/`, `projects/`, `todos/`, `tasks/`, `plans/`, `debug/`, `file-history/`, `checkpoints/`, `downloads/`, `backups/`, `paste-cache/`, `shell-snapshots/`, `session-env/`, `settings.local.json`, `stats-cache.json`, `mcp-needs-auth-cache.json`, `.last-cleanup`, `hooks/tool-size.log`, `hooks/__pycache__/`, `image-cache/`.

If a machine grows a new local artefact that doesn't deserve syncing, add it to `.gitignore`.

## Branches

`main` is the shared base — everything in it should make sense on every machine. Per-machine personal tweaks (model preference, hardcoded usernames, experimental settings) can live in `<hostname>-personal` branches that periodically merge `main` and stay outside it.

## License

MIT — see [LICENSE](LICENSE).
