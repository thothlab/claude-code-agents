#!/usr/bin/env python3
"""Mechanical invariants for Claude Code.

Reads hook payload (JSON) from stdin. Blocks via exit-code 2 + stderr reason.
Registered in ~/.claude/settings.json under hooks.PreToolUse / PostToolUse.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import sys


def read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def block(reason: str) -> None:
    print(f"BLOCKED by ~/.claude/hooks/guard.py: {reason}", file=sys.stderr)
    sys.exit(2)


def last_user_messages(transcript_path: str, n: int | None = 3) -> str:
    """Concatenated text of user messages from the session transcript.

    n=None returns the whole session; n=N returns only the last N user messages.
    Use last-N for "what is the user talking about *right now*" checks (Write
    on new .md). Use whole-session for commit/push: a single explicit "commit"/
    "push" anywhere in the session is enough — otherwise we burn tokens
    re-asking every few steps in a long workflow.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    texts: list[str] = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "user":
                    continue
                if d.get("isSidechain") is True:
                    continue
                msg = d.get("message", {})
                if not isinstance(msg, dict):
                    continue
                if msg.get("role") != "user":
                    continue
                content = msg.get("content")
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for p in content:
                        if not isinstance(p, dict):
                            continue
                        ptype = p.get("type")
                        if ptype == "text":
                            texts.append(p.get("text", "") or "")
                        elif ptype == "tool_result":
                            # Most tool_results are machine output (Bash stdout etc.) —
                            # ignore those. AskUserQuestion answers have a recognisable
                            # marker; include them as authorized user input.
                            tc = p.get("content")
                            collected = ""
                            if isinstance(tc, str):
                                collected = tc
                            elif isinstance(tc, list):
                                buf: list[str] = []
                                for x in tc:
                                    if isinstance(x, dict) and x.get("type") == "text":
                                        buf.append(x.get("text", "") or "")
                                collected = "\n".join(buf)
                            if "User has answered" in collected and len(collected) < 4000:
                                texts.append(collected)
    except Exception:
        return ""
    return "\n".join(texts if n is None else texts[-n:]).lower()


COMMIT_KEYWORDS = [
    r"закоммит",                                                    # закоммить/закоммитить/закоммить-те
    r"зафиксируй",
    r"зачекинь",
    r"\bgit\s+commit\b",                                            # user сам набрал команду
    r"(сделай|сделать|создай|оформи|оформить|нужен|нужно|можно|давай|подготовь|подготовить|хочу|хочется|надо)[^.!?\n]{0,40}\b(commit|коммит)",
    r"\b(let'?s|please|now|do|make|go\s+ahead\s+and|please\s+do|want\s+to|i\s+want)\s+(a\s+|to\s+)?commit\b",
    r"\bcommit\s+(this|it|that|these|those|the\s+\w+|changes|now|please|all|the\s+code)\b",
]

PUSH_KEYWORDS = [
    r"запушь",
    r"запушить",
    r"\bgit\s+push\b",
    r"\b(пушни|пушнем|пушним)\b",
    r"(сделай|сделать|оформи|оформить|нужен|нужно|можно|давай|хочу|хочется|надо)[^.!?\n]{0,40}\b(push|пуш)\b",
    r"\b(let'?s|please|now|do|make|go\s+ahead\s+and|want\s+to|i\s+want)\s+(a\s+|to\s+)?push\b",
    r"\bpush\s+(this|it|that|these|those|the\s+\w+|now|please|to\s+\w+|up)\b",
    r"залей\s+(на|в)\s+(remote|origin|github|удал[её]н)",
    r"отправь[^.!?\n]{0,40}(remote|origin|github|удал[её]н)",
]

NEW_MD_KEYWORDS = [
    r"\b(readme|notes|summary|changelog|todo|claude\.md|memory\.md|onboarding|spec|prd|architecture|install|contributing|license)\b",
    r"(создай|напиши|сделай|create|write|make|generate|draft|add)\s+[^.]{0,40}(\.md|документ|markdown|readme|notes|summary|changelog|memo|install|инструкц)",
    r"\b(документац|markdown|документ\b|инструкц)",
]


def session_authorized(transcript_path: str, patterns: list[str]) -> bool:
    """Whole-session keyword check. Used for commit/push: one explicit
    keyword anywhere in the session is enough — avoids re-asking the user
    every few steps in a long workflow."""
    text = last_user_messages(transcript_path, n=None)
    if not text:
        return False
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def user_authorized(transcript_path: str, patterns: list[str]) -> bool:
    text = last_user_messages(transcript_path, 3)
    if not text:
        return False
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def iter_subcommands(c: str):
    """Yield individual shell subcommands split by separators (;, &&, ||, |, ``).

    This is intentionally a coarse split — false positives (e.g. text inside
    "echo ...") are preferred over false negatives that miss real commands.
    """
    parts = re.split(r"[;&|`]+", c)
    for p in parts:
        # Treat $(subshell) content as its own chunk
        p = re.sub(r"\$\(([^()]*)\)", r" ; \1 ; ", p)
        for q in re.split(r"[;&|`]+", p):
            q = q.strip()
            if q:
                yield q


def has_git_subcommand(sub: str, name: str) -> bool:
    """Check whether `sub` is a git invocation calling subcommand `name`.

    Tolerates global git options between `git` and the subcommand
    (e.g. `git -C path commit`, `git -c user.name=x commit`).
    """
    return bool(re.search(rf"\bgit\b.{{0,200}}\b{re.escape(name)}\b", sub))


def guard_bash(tool_input: dict, transcript_path: str) -> None:
    cmd = tool_input.get("command", "") or ""
    if not cmd:
        return
    c = cmd

    # Subcommand-aware checks (git options can appear between `git` and the verb)
    for sub in iter_subcommands(c):
        # --- protective: dangerous flags ---
        if re.search(r"\bgit\b.{0,200}--no-verify\b", sub):
            block(
                "git --no-verify запрещён. Pre-commit/pre-push хуки существуют намеренно — "
                "обходить их нельзя без явного разрешения пользователя."
            )
        if re.search(r"\bgit\b.{0,200}--no-gpg-sign\b", sub):
            block("git --no-gpg-sign запрещён без явного разрешения пользователя.")

        # force-push на main/master
        if has_git_subcommand(sub, "push") and \
           re.search(r"(--force\b|\s-f\b|--force-with-lease\b)", sub) and \
           re.search(r"\b(main|master|origin/main|origin/master)\b", sub):
            block(
                "force-push на main/master запрещён. Используй обычный push "
                "или работай в feature-ветке."
            )

        # git rebase|add -i / --interactive (TTY required)
        if (has_git_subcommand(sub, "rebase") or has_git_subcommand(sub, "add")) and \
           re.search(r"(?:\s|^)(-i\b|--interactive\b)", sub):
            block("git -i / --interactive не работает в неинтерактивной среде.")

        # git rebase --no-edit — невалидная опция
        if has_git_subcommand(sub, "rebase") and re.search(r"--no-edit\b", sub):
            block("--no-edit не валидная опция для git rebase.")

        # git status -uall — раздувает контекст
        if has_git_subcommand(sub, "status") and re.search(r"\s-uall\b", sub):
            block("git status -uall запрещён — раздувает контекст на больших репозиториях.")

        # --- behavioral: commit/push only with session-wide user authorization ---
        # Session-wide (not last-N): once user said "commit" or "push" anywhere
        # in this session, subsequent commits/pushes are allowed. This avoids
        # token-burning re-asks during long workflows (cherry-pick chains, etc.).
        # Push authorization implies commit authorization (push needs a commit first).
        if has_git_subcommand(sub, "commit"):
            if not (session_authorized(transcript_path, COMMIT_KEYWORDS)
                    or session_authorized(transcript_path, PUSH_KEYWORDS)):
                block(
                    "git commit без явной авторизации в этой сессии. Скажи 'закоммить' "
                    "(или 'commit'/'пуш'/'push' где-то в этой сессии) и hook пропустит "
                    "все последующие commit'ы."
                )

        if has_git_subcommand(sub, "push"):
            if not session_authorized(transcript_path, PUSH_KEYWORDS):
                block(
                    "git push без явной авторизации в этой сессии. Скажи 'запушь' "
                    "(или 'push') и hook пропустит все последующие push'ы."
                )

    # rm -rf (любая комбинация флагов содержащая r и f)
    if re.search(r"(^|[\s;&|`(])rm\s+[^|;&]*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\b", c) or \
       re.search(r"(^|[\s;&|`(])rm\s+[^|;&]*-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\b", c):
        block(
            "rm -rf запрещён. Удаляй конкретные файлы по именам. "
            "Если действительно нужен rm -rf — попроси пользователя одобрить вручную."
        )
    # rm с wildcard
    if re.search(r"(^|[\s;&|`(])rm\s+[^|;&]*\*", c):
        block("rm с wildcard запрещён. Перечисли конкретные файлы.")
    # rm по абсолютному / ~ пути (кроме /tmp, /var/folders, /var/tmp, /private/tmp)
    for m in re.finditer(r"(^|[\s;&|`(])rm\s+([^|;&]+)", c):
        args = m.group(2)
        for tok in args.split():
            if tok.startswith("-"):
                continue
            if tok.startswith("~"):
                block(f"rm по пути в ~ ('{tok}') запрещён. Используй относительный путь.")
            if tok.startswith("/") and not re.match(
                r"^(/tmp(/|$)|/private/tmp(/|$)|/var/folders(/|$)|/var/tmp(/|$))", tok
            ):
                block(
                    f"rm по абсолютному пути '{tok}' запрещён. "
                    "Используй относительный путь или попроси одобрение пользователя."
                )

    # find / от корня (с исключениями для /tmp, /var, /Users, /private)
    if re.search(r"(^|[\s;&|`(])find\s+/", c):
        if not re.search(
            r"(^|[\s;&|`(])find\s+/(tmp|private|var|Users|opt|home)(\b|/)", c
        ):
            block("find от корня запрещён — выжирает ресурсы на больших FS. Ищи от конкретного пути.")


def guard_write(tool_input: dict, transcript_path: str) -> None:
    path = tool_input.get("file_path", "") or ""
    if not path:
        return
    if not path.lower().endswith(".md"):
        return
    if os.path.exists(path):
        return  # редактирование существующего .md разрешено

    # Разрешения по содержимому последних 5 сообщений
    text = last_user_messages(transcript_path, 5)
    name = os.path.basename(path).lower()
    base_no_ext = re.sub(r"\.md$", "", name)

    # Если упомянуто само имя файла или базовое имя — разрешаем
    if name and re.search(re.escape(name), text):
        return
    if base_no_ext and re.search(rf"\b{re.escape(base_no_ext)}\b", text):
        return
    # Тематические ключевые слова, разрешающие создание .md
    for pat in NEW_MD_KEYWORDS:
        if re.search(pat, text, re.IGNORECASE):
            return

    block(
        f"Создание нового {path} запрещено без явного запроса пользователя. "
        "Если документация действительно нужна — спроси и тогда создавай. "
        "По умолчанию работай через код/комментарии в существующих файлах."
    )


def log_tool_size(payload: dict) -> None:
    tool_name = payload.get("tool_name", "")
    tool_response = payload.get("tool_response")
    if isinstance(tool_response, str):
        size = len(tool_response)
    elif tool_response is None:
        size = 0
    else:
        try:
            size = len(json.dumps(tool_response, ensure_ascii=False))
        except Exception:
            size = -1
    session = str(payload.get("session_id", "?"))[:8]
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    log_path = pathlib.Path.home() / ".claude" / "hooks" / "tool-size.log"
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{ts}\t{session}\t{tool_name}\t{size}\n")
    except Exception:
        pass


def main() -> None:
    payload = read_payload()
    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    transcript_path = payload.get("transcript_path", "") or ""

    try:
        if event == "PreToolUse":
            if tool == "Bash":
                guard_bash(tool_input, transcript_path)
            elif tool == "Write":
                guard_write(tool_input, transcript_path)
        elif event == "PostToolUse":
            log_tool_size(payload)
    except SystemExit:
        raise
    except Exception as exc:
        # Защитное правило: при внутренней ошибке хука НЕ блокируем работу.
        print(f"guard.py internal error (allowing): {exc}", file=sys.stderr)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
