---
slug: gmcp-server-multitenant
title: "[P0] Multi-tenant server: резолв per-request вместо --project"
status: planning
epic: v2-global-mcp
story: v2gm-core
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "harness/claude/mcp/project/server.py"
  - "harness/cursor/mcp/project/server.py"
  - "scripts/resolve_project.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Переделать mcp/project/server.py: вместо единственного svc, привязанного к --project на старте, резолвить проект через resolve_project и держать кэш ProjectService по project_dir (lazy, по запросу). --project остаётся как явный override для headless/cron.  ПРЕМИСА ПОПРАВЛЕНА в сессии #121 задачей l26-roots-premise-fix. Прежний текст говорил: «если спайк показал process-per-window — допускается one-root-per-process через session roots», то есть называл депрекированный примитив источником резолва. Спека MCP от 2026-07-28 депрекирует roots (SEP-2577).  СТАЛО: при process-per-window допускается one-project-per-process через ТОТ ЖЕ первичный сигнал, что выбрал спайк gmcp-spike-roots, — он приходит параметром primary_signal в resolve_project, а не читается сервером самостоятельно. Если спайк оставил roots переходным путём, сюда это попадает через тот же параметр и НИЧЕГО здесь не меняет.  ПОЧЕМУ ЭТО ВАЖНО ИМЕННО ЗДЕСЬ. Эта задача — единственный потребитель resolve_project. Резолвер, у которого первое звено параметризовано, и его вызывающий, у которого roots зашиты в критерий приёмки, дали бы отмену правки в точке интеграции: модуль гибкий, а тест требует жёсткого. Поэтому формулировка приведена в соответствие ЗДЕСЬ, а не оставлена «мелочью в соседней карточке».  Депрекация annotation-only, гарантия не менее 12 месяцев — срочности нет. Мигрировать нечего: аудит l26-mcp-deprecation-audit замерил 0 обращений к депрекируемому API на 19 файлах MCP-треда.

## Acceptance Criteria

1. Сервер без --project поднимается и обслуживает запросы, резолвя проект через resolve_project по первичному сигналу, выбранному спайком. Критерий НЕ называет конкретный механизм: он приходит параметром, и жёсткое имя здесь отменило бы параметризацию резолвера.
2. ProjectService кэшируется по project_dir, повторные вызовы того же проекта переиспользуют инстанс.
3. НЕГАТИВНЫЙ: проект не резолвится -> tool возвращает понятную ошибку, а не traceback и не падение сервера, с подсказкой про tausik init / открыть проект.
4. НЕГАТИВНЫЙ: резолв вернул путь, которого нет или в котором нет .tausik/ -> та же понятная ошибка, а не попытка работать с мёртвым каталогом. Мёртвый project_dir опаснее отсутствия: сервер примет его за рабочий и создаст пустую БД рядом.
5. НЕГАТИВНЫЙ: два разных проекта в одном процессе не видят данных друг друга — проверяется тестом на двух project_dir с разными БД. Без этого кэш по project_dir остаётся утверждением, а не свойством.
6. Обратная совместимость: запуск с --project ведёт себя как сегодня.
7. pytest: резолв-кэш, ошибка-без-проекта, мёртвый путь, изоляция двух проектов, --project override; harness/* и .claude-копия пересобираются bootstrap без дрейфа.

## Plan

## Rollback

git revert + re-bootstrap возвращает launch-time --project сервер

## Journal
