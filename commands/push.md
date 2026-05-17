---
description: Push текущей ветки на upstream.
---

Push текущей ветки на её upstream remote.

Алгоритм:
1. `git status --short` — что не закоммичено.
2. Если есть uncommitted tracked changes — спросить через `AskUserQuestion`: коммитить через `/commit`, пушить только закоммиченное, или отменить.
3. `git push`. Если upstream не настроен — `git push -u origin <current-branch>`.
4. Показать `git log --oneline @{u}..HEAD` после успеха (или сообщить "already in sync").

Принудительный push без явного запроса не делать. Guard.py всё равно заблокирует force-вариант на `main`/`master`.
