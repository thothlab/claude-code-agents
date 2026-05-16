#!/usr/bin/env bash
# ~/.claude/sync.sh — bi-directional sync for Claude Code config repo.
#
# Strict: refuses to run if there are uncommitted tracked changes.
# Commit them yourself (with a meaningful message), then re-run.
# Untracked files are ignored — .gitignore handles machine-local data.

set -euo pipefail

REPO="$HOME/.claude"
cd "$REPO"

if [ ! -d "$REPO/.git" ]; then
  echo "✗ $REPO is not a git repository." >&2
  exit 1
fi

if ! git diff --quiet HEAD 2>/dev/null; then
  echo "✗ Uncommitted changes — commit or stash first, then re-run sync.sh:"
  git status --short
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "→ Branch: $CURRENT_BRANCH"

echo "→ Fetching..."
git fetch --quiet

LOCAL="$(git rev-parse @)"
REMOTE="$(git rev-parse '@{u}' 2>/dev/null || echo none)"
BASE="$(git merge-base @ '@{u}' 2>/dev/null || echo none)"

if [ "$REMOTE" = none ]; then
  echo "→ No upstream set; just pushing."
  git push -u origin "$CURRENT_BRANCH"
elif [ "$LOCAL" = "$REMOTE" ]; then
  echo "✓ Already in sync."
elif [ "$LOCAL" = "$BASE" ]; then
  echo "→ Pulling..."
  git pull --rebase
elif [ "$REMOTE" = "$BASE" ]; then
  echo "→ Pushing..."
  git push
else
  echo "→ Diverged — pulling with rebase, then pushing."
  git pull --rebase
  git push
fi

echo "✓ sync done"
