# Setup on a new machine

Global Claude Code config synced via this repo.

## First-time install

If `~/.claude` already exists, back it up:

```bash
mv ~/.claude ~/.claude.backup
```

Clone the repo into `~/.claude`:

```bash
git clone git@github.com:thothlab/claude-code-agents.git ~/.claude
```

No further configuration is needed — `settings.json` uses `$HOME` paths so
hooks and skills work regardless of username.

Restore any machine-specific files you need from the backup (typically
nothing — everything machine-local is in `.gitignore`).

## Daily sync

```bash
~/.claude/sync.sh
```

Or inside Claude Code:

```
/sync
```

`sync.sh` is **strict** — it refuses to run if you have uncommitted
changes to tracked files. Commit them with a meaningful message first.
Untracked files are fine (they're either ignored or new artifacts).

## Conflicts

`sync.sh` uses `git pull --rebase`. On a conflict, resolve in `~/.claude`
like any git repo, then:

```bash
git rebase --continue
git push
```

## What's synced vs. machine-local

Synced (committed): `CLAUDE.md`, `LICENSE`, `INSTALL.md`, `settings.json`,
`statusline-command.sh`, `sync.sh`, and the `commands/`, `skills/`,
`hooks/` directories.

Machine-local (in `.gitignore`): `sessions/`, `history.jsonl`, `cache/`,
`telemetry/`, `statsig/`, `ide/`, `config/`, `plugins/`, `agents/`,
`projects/`, `todos/`, `tasks/`, `plans/`, `debug/`, `file-history/`,
`checkpoints/`, `downloads/`, `backups/`, `paste-cache/`,
`shell-snapshots/`, `session-env/`, `settings.local.json`,
`stats-cache.json`, `mcp-needs-auth-cache.json`, `.last-cleanup`,
`hooks/tool-size.log`, `hooks/__pycache__/`.

## What the hooks do

See `hooks/guard.py` — mechanical invariants that block known-dangerous
commands and unauthorized commits/pushes. Errors fail open (the hook
never locks you out of Claude Code).
