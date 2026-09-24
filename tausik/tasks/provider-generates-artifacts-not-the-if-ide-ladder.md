---
slug: provider-generates-artifacts-not-the-if-ide-ladder
title: "Генерация артефактов IDE идёт через провайдера, а не через лестницу if ide=="
status: planning
epic: v2-global-mcp
story: v2gm-surfaces
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

РАСЩЕПЛЕНИЕ ext-p1-provider-refactor (цель G3), выполнено в #189: исходная задача несла ЧЕТЫРЕ разные цели, не имела ни одного критерия приёмки и блокировала четыре задачи — то есть была самым рискованным узлом плана именно потому, что была неделима.
ЧТО ДЕЛАЕТСЯ: вся генерация артефактов IDE идёт через provider.generate_settings() / generate_commands() вместо лестницы `if ide == "claude" ... elif ide == "cursor" ...` в bootstrap/bootstrap.py (замер #189: лестница живёт на строках 191-217). Это доделывает незавершённый рефакторинг v1.5.5.
ПОЧЕМУ ЭТО ПЕРВОЕ: без единой точки генерации нельзя добавить генерацию хуков для Cursor (.cursor/hooks.json с failClosed) — она ляжет пятой веткой в ту же лестницу, и следующий хост потребует шестую. Провайдеры уже есть для claude, cursor, kilo, qwen; у opencode модуля нет, хотя профиль раскладывается — это входит сюда.
НЕГАТИВНОЕ: рефакторинг не имеет права менять то, ЧТО раскладывается. Проверять двусторонне: развёрнутые профили до и после рефакторинга совпадают побайтово (bootstrap.py --check уже умеет сверять), и при этом новая ветка хоста добавляется БЕЗ правки bootstrap.py.

## Acceptance Criteria

## Plan

## Rollback

Рефакторинг без изменения выхода; откат git revert, сверка bootstrap --check показывает совпадение.

## Journal

- 2026-08-29T14:22:54Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
