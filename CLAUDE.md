# Глобальные правила работы

## Отчётность по проектам

После выполнения проекта (или значимого этапа) обязательно составить отчёт и сохранить в Obsidian vault.

**Obsidian vault:** клон репо `thothlab/openclaw_obsidian_vault` где-то под `~/Documents/` (точное имя папки различается по машинам: `openclaw_obsidian_vault`, `Obsidian Vault`, etc.). Если не уверен — `find ~/Documents -maxdepth 3 -name .obsidian -type d` покажет все локальные vault'ы; проверь `git -C <path> remote -v` и выбери тот, где origin = `thothlab/openclaw_obsidian_vault`.
**GitHub:** https://github.com/thothlab/openclaw_obsidian_vault

### Куда записывать (относительно корня vault):
- Проекты, относящиеся к **OpenClaw** → `OpenClaw/Projects/<проект>/`
- Все остальные проекты → `Projects/<проект>/`

### Что фиксировать (одна папка на проект):

1. **Идея и постановка.md** — исходная идея, требования, ссылки
2. **Техническое задание.md** — ТЗ, архитектура, зависимости
3. **План задач и отчёты.md** — план задач + по каждой: запланированное, выполненное, результат
4. **Правки.md** — если были изменения/правки по ходу: суть правки, что изменено, результат
5. **Итоговый отчёт.md** — суть задачи, запланированные работы, выполненные работы, результаты, итоги и резюме

### После записи:
- Коммит и пуш в GitHub (thothlab/openclaw_obsidian_vault)
- Файлы связывать через Obsidian-ссылки `[[...]]`

---

## Agentmemory — общая память для всех проектов

Плагин `agentmemory@agentmemory` установлен глобально (user-scope, MCP-сервер на :3111, auto-capture хуки активны). Это основной слой долговременной памяти **во всех проектах** — поверх file-based auto memory.

**Когда сохранять (`/agentmemory:remember`):**
- Состояние работы — на чём остановились, что выбрали, почему. Перед концом сессии или после значимого этапа.
- Решения и trade-offs, которые не очевидны из кода/git-истории.
- Факты про предпочтения пользователя и устоявшиеся паттерны работы.
- Делать это проактивно, без напоминаний. Если есть, что зафиксировать — фиксируй.

**Когда вспоминать (`/agentmemory:recall`):**
- **В начале каждой задачи** — делать quick recall по ключевым словам темы (имя фичи, технология, тип бага). Цель — не пропустить релевантный generalized-урок из других проектов.
- Также: когда пользователь говорит «вспомни / на чём остановились / что мы делали».

**Дополнительно:** `/agentmemory:session-history` — обзор недавних сессий, `/agentmemory:forget` — удалить запись.

**Разделение слоёв:**
- file-based MEMORY.md (`~/.claude/projects/<…>/memory/`) — project-локальная, всегда подгружается в контекст.
- agentmemory — cross-project, операционные снимки, semantic recall по запросу.
- Не дублировать одно и то же в обоих слоях.

**Scope-маркировка в agentmemory (обязательно при `memory_save`):**

API agentmemory не имеет встроенного фильтра по проекту, поэтому маркировка делается вручную, чтобы избежать утечек «совет из проекта A применился в проекте B».

*Что есть в API для маркировки:*
- `concepts` — comma-separated теги (используем как scope-метки)
- `type` — фиксированный enum: `pattern` / `preference` / `architecture` / `bug` / `workflow` / `fact`
- `files` — пути файлов (тоже scope-signal по cwd)
- Каждое наблюдение автоматически привязывается к проекту по cwd (видно в колонке `PROJECT` на дашборде)

*Чего нет:*
- Параметра `project` / `scope` в `memory_save`
- Фильтра по проекту в `memory_recall` / `memory_smart_search` — поиск возвращает результаты из всех проектов

*Соглашение (обязательное при сохранении):*

1. **Первая строка `content`** всегда начинается со scope-маркера в одном из форматов:
   - `[scope: project:<имя-проекта>]` — только этот проект.  
     Примеры: `[scope: project:itrack-tsd]`, `[scope: project:my-bruno]`.
   - `[scope: cross-project / <стек или категория>]` — применимо к группе проектов.  
     Примеры: `[scope: cross-project / android / kmp]`, `[scope: cross-project / web]`, `[scope: cross-project / debugging / ui-state-restore]`.
   - `[scope: universal]` — применимо везде, независимо от стека.

2. **В `concepts`** обязательно добавлять scope-теги в kebab-case:
   - Для project-локального: `scope-project-<name>` (например `scope-project-itrack-tsd`).
   - Для cross-project: `scope-cross-project` плюс теги категории/стека (`android`, `kmp`, `debugging`, `ui-state-restore`).
   - Для универсального: `scope-universal`.

3. **Generalized vs project-specific формулировки в content:**
   - Безопасно cross-project: «сначала логи, потом фикс», «при async listener'ах проверять timing через post».
   - Опасно cross-project (использовать только в project-scope): конкретные имена классов, тегов, путей, токенов («тег `SSH` в Timber», `OperationHistoryController`, `ru.frosteye.itrack`).
   - Если правило универсальное, но опирается на проектный пример — выносить пример в комментарий, не в правило.

*При `memory_recall` / `memory_smart_search`:*

- Перед применением результата **прочитать первую строку `content`** и сравнить scope с текущим проектом.
- Если scope = `project:<X>` и текущий проект ≠ X — **игнорировать результат**, не применять, не упоминать пользователю как релевантный.
- Если scope = `cross-project / <stack>` — проверить, что текущий стек входит в указанные категории. Если нет — игнорировать.
- Если scope = `universal` — применимо всегда.
- При неоднозначности (scope не указан, нет первой строки с маркером) — обращаться с записью как с `project:<source-project>` по умолчанию (наиболее безопасный fallback).

## Реакция на block от `~/.claude/hooks/guard.py`

Когда tool-result содержит строку `BLOCKED by ~/.claude/hooks/guard.py` — **не** писать многословное объяснение про несматчившийся keyword. Сразу `AskUserQuestion` с одним вопросом и двумя короткими опциями:

- commit/push: question="Сделать <commit|push>?", options=["Да","Нет"]
- Write на новый .md: question="Создать <file>?", options=["Да","Нет"]

После "Да" — повторить ту же команду один раз (guard теперь пропустит: `user_authorized` читает tool_result с маркером "User has answered" и обновляет session-wide authorization). После "Нет" — переключиться на альтернативу.

Срабатывает **только** на guard.py block. На других tool-errors (permission denied, file not found, syntax) — обычная диагностика и объяснение.

Полная версия правила: agentmemory `mem_mp9ebq1g_db771c77f8d1` (`[scope: universal]`).

---

# Behavioral guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Techniques

### Video bug reports — extract frames with ffmpeg

`Read` не открывает бинарные `.mp4`. Когда юзер прикладывает скринрекордер, не сдаваться с «не могу прочитать видео» — пилить через `ffmpeg` (есть в `~/homebrew/bin/`), потом `Read` каждый PNG.

Базовый рецепт:
```bash
mkdir -p /tmp/frames
ffmpeg -y -i video.mp4 -vf "fps=5,scale=432:-1" /tmp/frames/f_%03d.png
```

- `fps=5` хватает для типичных UI-багов длительностью 10-30 сек. Для тонких анимаций — `fps=10`.
- `scale=432:-1` ускоряет извлечение и чтение. Для мелкого текста (превью recents и т.п.) — `scale=864:-1` или больше.
- Перед извлечением полезно: `ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration,nb_frames -of default=noprint_wrappers=1 video.mp4`.

Тактика поиска ключевых моментов: `ls -la /tmp/frames/` — скачок размера PNG означает анимацию/переход. Удобно для поиска моментов сворачивания/восстановления, нажатий и т.п.
