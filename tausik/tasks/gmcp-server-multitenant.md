---
slug: gmcp-server-multitenant
title: "[P0] Multi-tenant server: резолв per-request вместо --project"
status: done
epic: v2-global-mcp
story: v2gm-core
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Резолв per-request и кэш ProjectService по project_dir в отдельном модуле tenancy рядом с сервером; server.py только подключает. --project остаётся явным override и ведёт себя как сегодня. resolve_project НЕ меняется — он уже параметризован."
scope_exclude: "scripts/gmcp_project_resolver.py (закрытая задача, первое звено уже параметр); handlers/* — переписывать их зависимость от cwd не в этом объёме, вместо этого tenancy держит cwd на время вызова и сериализует вызовы, когда проект резолвится по запросу."
relevant_files:
  - "harness/claude/mcp/project/tenancy.py"
  - "harness/claude/mcp/project/server.py"
  - "tests/test_mcp_tenancy.py"
scope_paths:
  - "harness/claude/mcp/project/tenancy.py"
  - "harness/claude/mcp/project/server.py"
  - "tests/test_mcp_tenancy.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T09:55:00Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#36"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
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

git revert плюс python bootstrap/bootstrap.py --ide all, потому что сервер запускается из развёрнутой копии. Поведение с --project не меняется, значит откат не трогает ни один работающий сеанс: путь по умолчанию в конфиге проекта — именно --project.

## Journal

- 2026-09-28T22:22:39Z [implementation] — AC-1: ✓ СМОУК НА НАСТОЯЩЕМ СЕРВЕРЕ без --project. Из корня проекта: 147 инструментов, tausik_status отдал живые данные (tasks_done 1659, session_id 277). Механизм в критерии не назван и в коде не зашит: primary_signal проходит насквозь в resolve_project, роль первичного сигнала играет cwd, как показал спайк. AC-2: ✓ tests/test_mcp_tenancy.py::TestTheCacheIsKeyedByProject — повтор того же каталога переиспользует инстанс (made==1), разные каталоги дают разные, ключ — абсолютный путь, а не написание. AC-6: ✓ ::TestPinnedModeIsUnchanged — с --project резолвер ВООБЩЕ не зовётся (подставлен взрывающийся), cwd не двигается, замок не берётся.
- 2026-09-28T22:22:39Z [implementation] — AC-3 НЕГАТИВНЫЙ: ✓ смоук из D:/tmp — те же 147 инструментов и понятное сообщение с обоими выходами (tausik init здесь / открыть проект), не traceback и не падение. Список инструментов продолжает отвечать намеренно: хост, не получивший список, читается как мёртвый сервер. AC-4 НЕГАТИВНЫЙ: ✓ ::test_a_resolved_path_without_dot_tausik_is_refused — сервис НЕ строится (made==0), потому что SQLiteBackend создал бы файл и успешно обслужил бы пустой проект. AC-5 НЕГАТИВНЫЙ: ✓ ::TestTwoProjectsInOneProcessDoNotSeeEachOther на НАСТОЯЩИХ ProjectService и двух базах: задача из alpha не видна в beta, на диске два файла, счёт строк через sqlite3 напрямую 1 и 1.
- 2026-09-28T22:22:39Z [implementation] — ЦЕНА НАЗВАНА, А НЕ СПРЯТАНА: рабочий каталог один на процесс, а часть обработчиков резолвит пути от него, поэтому режим по запросу держит cwd под замком на время вызова и пересекающиеся вызовы сериализуются — ::test_overlapping_calls_serialise_because_the_cwd_is_process_wide. Соседний тест проверяет, что замок отпускается при неудачной смене каталога, иначе один плохой запрос повесил бы все следующие. Лента: 12220 прошли, 30 пропущены (было 12197). Редеплой профилей выполнен до закрытия.
