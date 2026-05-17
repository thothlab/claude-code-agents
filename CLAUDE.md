# Глобальные правила работы

## Отчётность по проектам

После выполнения проекта (или значимого этапа) обязательно составить отчёт и сохранить в Obsidian vault.

**Obsidian vault:** `/Users/shaukat/Documents/Projects/Obsidian Vault/`
**GitHub:** https://github.com/thothlab/openclaw_obsidian_vault

### Куда записывать:
- Проекты, относящиеся к **OpenClaw** → `Obsidian Vault/OpenClaw/Projects/<проект>/`
- Все остальные проекты → `Obsidian Vault/Projects/<проект>/`

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
