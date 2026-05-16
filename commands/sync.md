---
description: Pull/push Claude Code config repo (~/.claude → thothlab/claude-code-agents)
---

Run `~/.claude/sync.sh` via Bash and report the result.

If it fails with "Uncommitted changes":
1. Show `git -C ~/.claude status --short` so the user sees what's dirty.
2. Ask whether to commit (and with what message), stash, or abort.
3. After the user decides, act and re-run `~/.claude/sync.sh`.

Do not auto-commit without an explicit user instruction.
