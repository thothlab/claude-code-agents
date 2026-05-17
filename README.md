# claude-code-agents

**Язык:** Русский · [English](README.en.md)

Синхронизированная конфигурация `~/.claude/` для [Claude Code](https://claude.com/claude-code): hooks, slash-команды, skills, глобальные инструкции.

Один и тот же агент-config на всех машинах. Машинно-локальные данные (сессии, история, телеметрия, IDE-state, кеш плагинов) исключены через `.gitignore`.

## Быстрый старт

```bash
git clone git@github.com:thothlab/claude-code-agents.git ~/.claude
```

Всё, установка завершена — пути используют `$HOME`, ничего править под конкретную машину не нужно. Полная инструкция установки в [INSTALL.md](INSTALL.md).

Ежедневная синхронизация (сначала локальный commit, потом pull/push):

```bash
~/.claude/sync.sh        # либо  /sync  внутри Claude Code
```

## Что внутри

| Путь | Назначение |
|---|---|
| `hooks/guard.py` | Mechanical invariants на каждом Bash/Write — блокирует опасные операции и неавторизованные commit/push. См. [Hooks](#hooks). |
| `commands/` | Slash-команды, доступные как `/<name>` в Claude Code. См. [Команды](#команды). |
| `skills/` | Skills, подгружаемые Claude Code по требованию. |
| `CLAUDE.md` | Глобальные инструкции: workflow отчётности по проектам (Obsidian), behavioral guidelines, техники. |
| `INSTALL.md` | Установка на новой машине. |
| `settings.json` | Permissions, регистрация hooks, статусная строка, конфиг marketplace плагинов. |
| `sync.sh` | Strict pull+push обёртка, используется `/sync`. |
| `statusline-command.sh` | Рендерер статусной строки. |

## Hooks

`hooks/guard.py` запускается на каждом `Bash` и `Write` (PreToolUse), а также на результатах Bash/Read/Glob/Grep/WebFetch (PostToolUse).

**Защитные** — блокируются всегда:
- Обход pre-commit hooks (`--no-verify`, `--no-gpg-sign`)
- Force-push на `main`/`master`
- Рекурсивное удаление через `rm -rf`, wildcard'ы в `rm`, абсолютные пути вне `/tmp`
- Поиск по файловой системе от корня (`find /`)
- Интерактивные флаги, требующие TTY, на `rebase`/`add`
- `--no-edit` на rebase, `-uall` на status

**Поведенческие** — блокируются, если пользователь явно не разрешил в этой сессии:
- `git commit` — нужно ключевое слово вроде `commit`/`коммит`/`закоммить`/`зафиксируй` или любой push-keyword где-то в сессии
- `git push` — нужно `push`/`пуш`/`запушь`/`залей` или `git push` в сессии
- Создание нового `*.md` через `Write` — нужно явное упоминание имени файла или doc-creation keyword в последних 5 user-сообщениях

Bypass-resistant: команда разбивается по `;`, `&&`, `||`, `|`, backticks, `$()`; формы `git -C path commit` и подобные глобальные опции отлавливаются.

Fail-open: любая внутренняя ошибка guard'а пропускает операцию — сломанный hook не должен блокировать пользователя в Claude Code.

Observability: размер ответа каждого tool-call дописывается в `hooks/tool-size.log` (gitignored).

## Команды

| Команда | Назначение |
|---|---|
| `/sync` | Pull/push текущего репо через `sync.sh`; спрашивает перед авто-коммитом. |
| `/clean-arch` | Правила Clean Architecture для Android / KMP / Compose Multiplatform. |
| `/mvvm-udf` | Правила MVVM + Unidirectional Data Flow. |
| `/mvvm-udf-kmp` | MVVM + UDF, адаптированные под KMP/CMP. |

Дополнительно вспомогательные скрипты, не оформленные как slash-команды:
- `commands/checkpoint-manager.sh`, `commands/standard-checkpoint-hooks.sh` — утилиты checkpoint'ов.
- `commands/github-safe.js` — обёртка с защитой над GitHub-операциями.

## Skills

| Skill | Назначение |
|---|---|
| `prd` | Создание подробного PRD и декомпозиция инициативы на task-файлы + отчёты выполнения (`tasks/prd_XX_*`). |
| `skill-builder` | Создание новых skills для Claude Code с правильным YAML-frontmatter, прогрессивным раскрытием и полной структурой директории. |

## Что **не** синхронизируется

`.gitignore` оставляет машинно-локальное и эфемерное за бортом: `sessions/`, `history.jsonl`, `cache/`, `telemetry/`, `statsig/`, `ide/`, `config/`, `plugins/`, `agents/`, `projects/`, `todos/`, `tasks/`, `plans/`, `debug/`, `file-history/`, `checkpoints/`, `downloads/`, `backups/`, `paste-cache/`, `shell-snapshots/`, `session-env/`, `settings.local.json`, `stats-cache.json`, `mcp-needs-auth-cache.json`, `.last-cleanup`, `hooks/tool-size.log`, `hooks/__pycache__/`, `image-cache/`.

Если на машине появляется новый локальный артефакт, который не должен синкаться — добавь в `.gitignore`.

## Ветки

`main` — общая база, всё в ней должно иметь смысл на любой машине. Личные правки под конкретную машину (выбор модели, хардкод username'а, экспериментальные настройки) живут в ветках `<hostname>-personal`, которые периодически мерджат `main` и остаются вне него.

## Лицензия

MIT — см. [LICENSE](LICENSE).
