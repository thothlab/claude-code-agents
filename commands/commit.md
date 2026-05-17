---
description: Стейдж + commit изменений в текущем git репо (без push).
---

Закоммить изменения в текущем git репо (cwd).

`$ARGUMENTS` — опционально готовый commit-message (если задан — без отдельного вопроса).

Алгоритм:
1. `git status --short` — что грязного.
2. Если working tree чистый — сообщить и выйти.
3. Показать diff (`git diff` + список untracked).
4. Если `$ARGUMENTS` пуст — спросить через `AskUserQuestion` commit-message (или короткий free-text follow-up).
5. Стейдж осмысленных файлов:
   - Tracked модификации — обычно `git add -u`.
   - Untracked — добавлять выборочно (не секреты, не побочные артефакты, не машинно-локальное).
6. `git commit -m "<message>"`. Если в message есть подстроки, триггерящие guard.py (флаги обхода git-hooks, опасные команды удаления) — записать message в `/tmp/commit-msg.txt` и сделать `git commit -F`.
7. Показать `git log --oneline -1` результата.

Push не делать автоматом — для этого `/push`.
