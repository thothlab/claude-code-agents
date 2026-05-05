#!/bin/sh
# Claude Code status line — based on robbyrussell Oh My Zsh theme

input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
dir=$(basename "$cwd")
model=$(echo "$input" | jq -r '.model.display_name // ""')
used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
five_hour=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
seven_day=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

# ANSI colors
green='\033[1;32m'
cyan='\033[0;36m'
blue='\033[1;34m'
red='\033[0;31m'
yellow='\033[0;33m'
reset='\033[0m'

# Git branch and dirty state
branch=""
dirty=""
if git_branch=$(GIT_OPTIONAL_LOCKS=0 git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null); then
  branch="$git_branch"
  if [ -n "$(GIT_OPTIONAL_LOCKS=0 git -C "$cwd" status --porcelain 2>/dev/null)" ]; then
    dirty=" ✗"
  fi
fi

# Context usage indicator
ctx_part=""
if [ -n "$used" ]; then
  used_int=$(printf "%.0f" "$used")
  ctx_part=" | ctx: ${used_int}%"
fi

# 5-hour (daily session) limit
five_hour_part=""
if [ -n "$five_hour" ]; then
  five_hour_int=$(printf "%.0f" "$five_hour")
  five_hour_part=" | 5h: ${five_hour_int}%"
fi

# 7-day (weekly) limit
seven_day_part=""
if [ -n "$seven_day" ]; then
  seven_day_int=$(printf "%.0f" "$seven_day")
  seven_day_part=" | 7d: ${seven_day_int}%"
fi

# Model part
model_part=""
if [ -n "$model" ]; then
  model_part=" | ${model}"
fi

# Assemble
if [ -n "$branch" ]; then
  printf "${green}➜${reset}  ${cyan}%s${reset} ${blue}git:(${red}%s${blue})${yellow}%s${reset}${model_part}${ctx_part}${five_hour_part}${seven_day_part}\n" \
    "$dir" "$branch" "$dirty"
else
  printf "${green}➜${reset}  ${cyan}%s${reset}${model_part}${ctx_part}${five_hour_part}${seven_day_part}\n" \
    "$dir"
fi
