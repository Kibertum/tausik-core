[English](../en/mcp.md) | **Русский**

# TAUSIK MCP — Справочник инструментов

**146 инструмента** для ИИ-агентов (актуальный счёт, проверено `len(TOOLS)`). MCP-surface покрывает всё, что агент делает день за днём. Несколько CLI-only команд намеренно не имеют MCP-аналога — это оператор/maintenance verbs, которым не место в agent-loop: `skill rebuild`, `skill bundle`, `fts optimize`, `db prune`, `audit vendors`/`research`, `config set`/`show`, `push-ok`, `run`, `doc extract`/`constants`, `hud`, `suggest-model`, `hygiene archive --confirm`. Для рабочего набора агента предпочитайте MCP-инструменты shell-вызовам — они атомарны, возвращают структурированные данные и держат контекст чище.

> **Опциональный сервер `codebase-rag`** добавляет 7 инструментов (search_code, find_symbol, etc.). Он включается отдельно через bootstrap и НЕ входит в основной счёт 152 — итого с ним 153 инструментов.

В проекте живут два MCP-сервера:

- `tausik-project` — project-scoped инструменты (146): tasks, sessions, knowledge, stacks, roles, gates, skills, exploration, audit, doctor, verify, usage logging, RENAR substrate (specs + adapts).

Опционально доступен `codebase-rag` сервер (документирован в конце).

## Verify-First Contract (v1.5)

Тяжёлые quality gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeconform, hadolint, ansible-lint) живут на отдельном триггере `verify`. MCP workflow:

```
tausik_task_start(slug=…)                    # QG-0
… работа над кодом …
tausik_verify(task_slug=…)                   # тяжёлое: subprocess-гейты → кеш green
tausik_task_done(slug=…, ac_verified=True)   # лёгкое: lookup в кеше
```

`tausik_task_done` откажется закрывать задачу, если verify-кеш отсутствует или устарел — возвращает структурированный failure с явной remediation. Opt-out для CI: установите `{"task_done": {"auto_verify": true}}` в `.tausik/config.json` — тогда heavy гейты выполнятся внутри `task_done` как в релизах до v1.5.

**Терминология:** [Глоссарий verify / QG](verify-glossary.md) — *поддерживаемый opt-out*, *обход QG* (для `task_done` недоступен), *обход verify-кеша* и pytest **test shim**.

## Status, Health, Metrics

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_health` | Health check: версия, DB, таблицы | — |
| `tausik_self_check` | Свежесть MCP-сервера: время старта, snapshot mtime watched-модулей vs текущие mtime на диске, флаг `drift_detected`, список stale-модулей с `delta_seconds`, число sibling MCP project-серверов. Вызывать из `/start` чтобы поймать предвестники тихих зависаний (gotchas #77/#79/#80). | — |
| `tausik_status` | Обзор проекта: задачи, сессия, эпики. `compact: true` → один JSON без изменения текстового режима по умолчанию. | `compact` (опционально) |
| `tausik_doctor` | 4-group health (venv + DB + MCP + skills + drift) | — |
| `tausik_metrics` | Метрики SENAR: Throughput, FPSR, DER, Dead End Rate, Cost/Task | — |
| `tausik_usage_event_log` | Ручная запись в `usage_events` (агрегаты сессии не трогает) | `tokens_input`, `tokens_output`, `tokens_total`, `cost_usd` |
| `tausik_search` | Полнотекстовый поиск по задачам, памяти, решениям | `query` |

## Задачи

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_task_add` | Создать задачу (опционально в стори) | `slug`, `title` |
| `tausik_task_quick` | Быстрое создание с auto-slug | `title` |
| `tausik_task_start` | Начать работу (QG-0: требует goal + AC + negative scenario) | `slug` |
| `tausik_task_done` | Завершить (QG-2: `ac_verified=true`, scoped pytest, verify cache). Возвращает structured JSON: `blocking_failures`, per-gate results, cache status. | `slug` |
| `tausik_task_show` | Полная информация | `slug` |
| `tausik_task_list` | Список с фильтрами (status enum: `planning,active,blocked,review,done`) | — |
| `tausik_task_update` | Обновить поля (title/goal/AC/scope/notes/stack/complexity/role/tier/call_budget) | `slug` |
| `tausik_task_plan` | Задать шаги плана | `slug`, `steps[]` |
| `tausik_task_step` | Отметить шаг выполненным | `slug`, `step_num` |
| `tausik_task_log` | Добавить запись в журнал | `slug`, `message` |
| `tausik_task_logs` | Чтение структурированных логов (фильтр по фазе) | `slug` |
| `tausik_reason_step` | RENAR шаг рассуждения (intent\|premise\|action\|verification) | `slug`, `kind`, `content` |
| `tausik_task_replay` | Хронологический таймлайн задачи (logs + reasoning + events + verification) | `slug` |
| `tausik_task_block` | Заблокировать | `slug` |
| `tausik_task_unblock` | Разблокировать | `slug` |
| `tausik_task_review` | Перевести в review | `slug` |
| `tausik_task_delete` | Удалить | `slug` |
| `tausik_task_move` | Переместить в другую стори | `slug`, `new_story_slug` |
| `tausik_task_next` | Выбрать следующую задачу по score | — |
| `tausik_task_claim` | Занять задачу (мульти-агент) | `slug`, `agent_id` |
| `tausik_task_unclaim` | Освободить | `slug` |

### `tausik_task_done` параметры

- `ac_verified` — **обязательно** для QG-2
- `evidence` — inline AC verification log (заменяет отдельный `task_log` вызов)
- `no_knowledge` — подтвердить отсутствие знаний для фиксации (подавляет warning)
- `relevant_files[]` — изменённые файлы; драйвят **scoped** pytest gate (basename match → `tests/test_<file>.py`). Empty list при non-empty original → gate skipped (нет ложных срабатываний на full suite). Verify cache (10 min TTL) пропускает re-run при том же `files_hash`.

`task_done` **не имеет `--force`** — QG-2 нельзя байпаснуть. У `task_start` `--force` есть для байпаса session capacity, с audit trail.

### `tausik_task_done` structured response

`tausik_task_done` возвращает JSON для агентных сценариев:
- stage-флаги (`plan_complete`, `ac_verified`, `gates_passed`)
- результаты по каждому gate (`gates[]`)
- `blocking_failures[]` с `gate`, `files`, `output`, `remediation`
- `warnings[]`, `cache_status` и итоговый `ok`

До v1.5 был параллельный alias `tausik_task_done_v2` для structured-JSON варианта. **v14b-task-done-rename-drop-v2 объединил оба в один `tausik_task_done` со structured JSON выше** — суффикса `_v2` больше нет. Verify-First Contract соблюдается на всех путях.

## Сессии

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_session_start` | Начать сессию | — |
| `tausik_session_end` | Завершить сессию | — |
| `tausik_session_extend` | Продлить active-time лимит сверх 180 мин | — |
| `tausik_session_current` | Текущая активная сессия | — |
| `tausik_session_list` | Список сессий | — |
| `tausik_session_handoff` | Сохранить handoff data | `handoff` (object) |
| `tausik_session_last_handoff` | Получить handoff из предыдущей сессии | — |
| `tausik_session_open` (v1.5) | Compound RPC: session start + status + handoff + active/blocked задачи + self_check в одном envelope. Питает Phase 1 в `/start`. Секции `session` и `self_check` спроецированы только до рендерящихся полей (без `watched_modules`/`current_mtimes`, без дубля хендоффа) — полная телеметрия через `tausik_self_check`. | — |

Лимит сессии — gap-based **active time** (паузится после 10-min idle gap), не wall clock. См. `session-active-time.md`.

## Иерархия (эпики и стори)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_epic_add` | Создать эпик | `slug`, `title` |
| `tausik_epic_list` | Список эпиков; `(stale: N)` — задач создано после последней правки описания (отчёт, не гейт) | — |
| `tausik_epic_update` | Изменить title и/или description эпика — замысел группы задач; хотя бы одно поле | `slug` |
| `tausik_epic_done` | Завершить эпик | `slug` |
| `tausik_epic_delete` | Удалить (cascade: стори + задачи) | `slug` |
| `tausik_story_add` | Создать стори в эпике | `epic_slug`, `slug`, `title` |
| `tausik_story_list` | Список стори; `(stale: N)` как у эпиков | — |
| `tausik_story_update` | Изменить title и/или description стори; хотя бы одно поле | `slug` |
| `tausik_story_done` | Завершить стори | `slug` |
| `tausik_story_delete` | Удалить (cascade: задачи) | `slug` |
| `tausik_roadmap` | Дерево: epic → story → task | — |

## RENAR substrate — SPEC + ADAPT (17 инструментов)

RENAR-подложка: формальные требования (**SPEC**) и интерпретация ТЗ (**ADAPT**, §7) с forward-интерпретациями, backward-findings и подписью архитектора (§7.5). Используется QG-0 для substantial/deep задач и `tausik renar export`/`conformance`. См. также `tausik_reason_step` (RENAR trace) в разделе «Задачи».

### SPEC (8)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_spec_add` | Создать SPEC-артефакт. `type` — закрытый список 11 (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS/TEST/DOC); новый тип = поправка к стандарту, не free-text | `slug`, `type`, `title`, `version` |
| `tausik_spec_list` | Список SPEC, опц. фильтр по типу (JSON) | — |
| `tausik_spec_show` | SPEC + связанные задачи (JSON) | `slug` |
| `tausik_spec_update` | Патч изменяемых полей (title/version/content_ref/status); `type`+`slug` иммутабельны | `slug` |
| `tausik_spec_delete` | Удалить SPEC (cascade: task-линки) | `slug` |
| `tausik_spec_link` | Связать задачу со SPEC (оба должны существовать — нет тихих dangling-линков) | `task_slug`, `spec_slug` |
| `tausik_spec_unlink` | Снять связь задача↔SPEC | `task_slug`, `spec_slug` |
| `tausik_spec_search` | FTS5 по slug/title/content_ref (JSON) | `query` |

### ADAPT (9)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_adapt_create` | Создать заголовок ADAPT (§7); `tz_ref` (исходное ТЗ) обязателен; старт в `draft` | `slug`, `title`, `tz_ref` |
| `tausik_adapt_interpret` | Forward-интерпретация (§7.4.3); tz_ref/citation/interpretation/scope_in/scope_out обязательны | `tz_ref`, `citation`, `interpretation`, `scope_in`, `scope_out` (+ adapt) |
| `tausik_adapt_finding` | Backward-finding; `category` — закрытый список 7 (contradiction/gap/hidden-assumption/feasibility/regulatory/terminology/scope) | `adapt_slug`, `category`, `description` |
| `tausik_adapt_sign` | Подпись architect (§7.5): подписывает тело ed25519-ключом проекта ⇒ `approved` (§13.3.3 стр.77 — статус и подпись разные факты). `role=client` ОТКЛОНЯЕТСЯ — ADR-011 отозвал подпись клиента под ADAPT; то, что одобряет клиент, теперь живёт в ACTZ | `adapt_slug`, `role`, `signed_by` |
| `tausik_adapt_show` | ADAPT + forward-интерпретации, findings, подписи, линки (JSON) | `slug` |
| `tausik_adapt_list` | Список ADAPT, опц. фильтр по статусу (закрытый перечень §7.8.1: draft/review/asked/answered/approved/frozen/superseded) | — |
| `tausik_adapt_delta` | Delta-ADAPT, замещающий родителя (§7.6); родитель → `superseded`, поздний линк к нему = FATAL dangling (§7.6.4) | `parent_slug`, `new_slug`, `title`, `tz_ref` |
| `tausik_adapt_link` | Связать ADAPT с задачей/SPEC; target должен существовать; линк к superseded ADAPT = FATAL (§7.6.4) | `adapt_slug`, `target_type`, `target_slug` |
| `tausik_adapt_search` | FTS5 по slug/title/tz_ref (JSON) | `query` |

### ACTZ (15)

Контрактный протокол уточнения ТЗ (§5A, ADR-011) — в отличие от ADAPT обращён к клиенту:
то, что клиент утверждает, живёт здесь. Жизненный цикл `draft` → `sent` → `signed` →
`superseded`, вычисляется по покрытию ролей подписи. В проекте один ed25519-ключ, не по
сторонам: `architect` подписывает по-настоящему; `client` записывает только
`signed_by`+`signed_at`, без имитации независимой подписи. `final_tz`/`orphans` (§5A.4) —
read-only проекции над подписанными пунктами ниже: производный эталон приёмки, а не
третья копия текста.

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_actz_create` | Создать заголовок ACTZ (§5A); `tz_ref` обязателен; старт в `draft` | `slug`, `title`, `tz_ref` |
| `tausik_actz_point` | Добавить нумерованный пункт; только пока `draft` (заморожено после первой подписи). `tz_ref` называет пункт исходного ТЗ (или предыдущего пункта ACTZ), который уточняется | `actz_slug`, `point_no`, `tz_ref`, `text` |
| `tausik_actz_sign` | Записать подпись (§5.5.3): `architect` подписывает тело ed25519-ключом проекта; `client` — только `signed_by`+`signed_at`. Первая подпись ⇒ `sent`; обе роли ⇒ `signed` | `actz_slug`, `role`, `signed_by` |
| `tausik_actz_verify` | Проверить подпись architect (ed25519) против текущего тела | `slug` |
| `tausik_actz_show` | ACTZ + пункты, подписи, линки (JSON) | `slug` |
| `tausik_actz_list` | Список ACTZ, опц. фильтр по статусу (draft/sent/signed/superseded) | — |
| `tausik_actz_delta` | Delta-ACTZ, замещающий родителя; родитель → `superseded`, поздний линк к нему отклоняется | `parent_slug`, `new_slug`, `title`, `tz_ref`, `supersession_rationale` |
| `tausik_actz_link` | Связать ACTZ с задачей/SPEC; target должен существовать; линк к superseded ACTZ отклоняется | `actz_slug`, `target_type`, `target_slug` |
| `tausik_actz_unlink` | Снять связь ACTZ↔задача/SPEC | `actz_slug`, `target_type`, `target_slug` |
| `tausik_actz_delete` | Удалить ACTZ (cascade: пункты/подписи/линки/decided-in) | `slug` |
| `tausik_actz_search` | FTS5 по slug/title/tz_ref (JSON) | `query` |
| `tausik_actz_decided_in` | Записать: backward-finding ADAPT решён в пункте ПОДПИСАННОГО ACTZ, с provenance (`linked_by`); отклоняет неподписанную цель | `adapt_slug`, `finding_id`, `actz_slug`, `actz_point_no`, `linked_by` |
| `tausik_actz_decided_in_remove` | Удалить decided-in ребро | `adapt_slug`, `finding_id`, `actz_slug`, `actz_point_no` |
| `tausik_actz_final_tz` | Производный эталон приёмки (§5A.4): по каждому пункту ТЗ — последний обеими сторонами подписанный пункт, с указанием, что он перекрыл. `as_of` (ISO-8601) — на прошлый момент | — |
| `tausik_actz_orphans` | Подписанные пункты, которые не отражены ни в одном ADAPT — обязательство вне требований (§5A.4, fatal), находится запросом | — |

### AT (9)

Приёмочные тесты (§8A, ADR-012) — единственная проверка, которую трассируемость
(TC → SR → ADAPT → ТЗ) структурно дать не может: неверная интерпретация
проходит все TC. Эти инструменты ЗАПИСЫВАЮТ результат процедуры изолированной
генерации (docs/en/at-generation-procedure.md) — ни один не генерирует ничего
сам. `tz_text` (дословная цитата контракта) и `generated_by` обязательны при
создании; `check_freshness` сравнивает с ЖИВЫМ `final_tz_snapshot` по `tz_ref`
каждой записи и называет, что изменилось (§8A.2 — перегенерировать перед
каждым испытанием). См. также warn-гейт `at_freshness`.

`record_result`/`diagnose`/`release_readiness` реализуют матрицу маршрутизации
§8A.4/§10.4.3. У TAUSIK нет TC как самостоятельной сущности (открытая отдельная
задача) — `diagnose` сам pytest/verification_runs не читает; `tc_outcome`
передаёт вызывающий явно. `release_readiness` не требует TC вовсе: готовность
наступает только когда исход каждого AT зелёный и свежий — отдельно от QG-4,
который необязателен и меряет бизнес-результат.

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_at_create` | Записать AT — результат процедуры изолированной генерации, не генератор | `slug`, `tz_ref`, `tz_text`, `scenario`, `source_as_of`, `generated_by` |
| `tausik_at_show` | Показать запись AT (JSON) | `slug` |
| `tausik_at_list` | Список AT, опц. фильтр по tz_ref (JSON) | — |
| `tausik_at_delete` | Удалить запись AT | `slug` |
| `tausik_at_search` | FTS5 по slug/tz_ref/tz_text/scenario (JSON) | `query` |
| `tausik_at_check_freshness` | Какие AT устарели против текущего итогового ТЗ (§8A.2); без slug — проверка всех | — |
| `tausik_at_record_result` | Записать один наблюдённый исход испытания (только добавление — повтор — новая строка) | `slug`, `outcome` |
| `tausik_at_diagnose` | Маршрутизировать последний исход AT против переданного вызывающим `tc_outcome` (§8A.4/§10.4.3) | `slug`, `tc_outcome` |
| `tausik_at_release_readiness` | Релизный гейт §8A.4: готовность только когда каждый AT зелёный и свежий | — |

## Знания

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_add` | Сохранить в проектную память | `type`, `title`, `content` |
| `tausik_memory_search` | Полнотекстовый поиск | `query` |
| `tausik_memory_list` | Список (фильтр по типу) | — |
| `tausik_memory_show` | Показать запись по ID | `id` |
| `tausik_memory_delete` | Удалить запись | `id` |
| `tausik_memory_block` | Compact markdown: recent decisions + conventions + dead ends (для /start re-injection) | — |
| `tausik_memory_compact` | Aggregate recent task_logs (phases + top words + top files) | — |
| `tausik_memory_archive` (v1.5) | Soft-archive памяти старше duration (90d / 12w / 2m / 1y). Dry-run если нет `confirm: true`. | `before` (string), `confirm` (bool, опционально) |
| `tausik_memory_dedupe` (v1.5) | Список near-duplicate memory-пар выше порога similarity (read-only). | `threshold` (float, опц.), `limit` (int, опц.) |
| `tausik_decide` | Записать архитектурное решение | `decision` |
| `tausik_decisions_list` | Список решений | — |

Типы памяти: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.

## Графовая память

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_link` | Создать связь между узлами | `source_type`, `source_id`, `target_type`, `target_id`, `relation` |
| `tausik_memory_unlink` | Soft-invalidate связь (никогда не удаляет) | `edge_id` |
| `tausik_memory_related` | Найти связанные узлы (1–3 hops) | `node_type`, `node_id` |
| `tausik_memory_graph` | Список связей с фильтрами | — |

Типы связей: `supersedes`, `caused_by`, `relates_to`, `contradicts`.

## Тупики и исследования

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_dead_end` | Документировать неудачный подход | `approach`, `reason` |
| `tausik_explore_start` | Начать time-boxed исследование | `title` |
| `tausik_explore_end` | Завершить исследование | — |
| `tausik_explore_current` | Текущее исследование | — |

## Шлюзы качества и верификация

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_gates_status` | Статус всех gates (по стеку) | — |
| `tausik_gates_enable` | Включить gate | `name` |
| `tausik_gates_disable` | Выключить gate | `name` |
| `tausik_verify` | v1.5 Verify-First: запустить heavy gates (pytest, tsc, …) и закешировать green в `verification_runs`. После этого `tausik_task_done` использует кеш и закрывается мгновенно. | `task_slug` |

Доступные gates: `pytest`, `ruff`, `mypy`, `bandit`, `tsc`, `eslint`, `go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`, `filesize`, `class_surface`, `tdd_order`. Stack-scoped gates авто-включаются по обнаруженному стеку; universal gates (`filesize`, `class_surface`, `tdd_order`) применяются ко всем стекам. `class_surface` работает по всему репозиторию, а не по скоупу: он ограничивает составную публичную поверхность класса после наследования, которую пофайловый строковый лимит видеть не может.

`tdd_order` отключён по умолчанию. Включите через `tausik_gates_enable name=tdd_order`.

## Стеки

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_stack_list` | Список встроенных + custom стеков | — |
| `tausik_stack_show` | Резолвленный стек: gates per language + override info | `stack` |
| `tausik_stack_export` | Экспорт резолвленной декларации как JSON | `stack` |
| `tausik_stack_diff` | Diff между built-in и user override | `stack` |
| `tausik_stack_reset` | Удалить user override в `.tausik/stacks/<stack>/` | `stack` |
| `tausik_stack_lint` | Валидировать user-override `stack.json` | — |
| `tausik_stack_scaffold` | Создать `.tausik/stacks/<name>/{stack.json,guide.md}` skeleton | `name` |

DEFAULT_STACKS: 25 записей (python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker). Custom-стеки через `.tausik/config.json` → `custom_stacks`.

## Роли

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_role_list` | Список ролей | — |
| `tausik_role_show` | Профиль роли | `slug` |
| `tausik_role_create` | Создать роль (опционально `extends` базовый профиль) | `slug`, `title` |
| `tausik_role_update` | Обновить метаданные | `slug` |
| `tausik_role_delete` | Удалить роль | `slug` |
| `tausik_role_seed` | Bootstrap из `harness/roles/*.md` + использования в задачах | — |

Хранение ролей гибридное: SQLite-метаданные + markdown-профиль `harness/roles/{role}.md`. Роли в задачах остаются свободным текстом.

## Периодический аудит (SENAR Rule 9.5)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_audit_check` | Просрочен ли аудит | — |
| `tausik_audit_mark` | Отметить аудит выполненным | — |

## Навыки

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_skill_list` | Список навыков: активные, vendored, доступные | — |
| `tausik_skill_install` | Установить из репо (clone + copy + deps) | `name` |
| `tausik_skill_uninstall` | Удалить полностью | `name` |
| `tausik_skill_activate` | Активировать установленный | `name` |
| `tausik_skill_deactivate` | Деактивировать (файлы остаются) | `name` |
| `tausik_skill_repo_add` | Добавить TAUSIK-совместимый репо (сторонний URL — `force`) | `url`, опционально `force` |
| `tausik_skill_repo_remove` | Удалить репо | `name` |
| `tausik_skill_repo_list` | Список репозиториев и доступных skills | — |
| `tausik_skill_catalog` | Discovery: список skills из настроенных/клонированных repos (name, category, description) | опц. `repo`, опц. `as_json` |

## Cross-Project Queue (CQ)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_cq_publish` | Опубликовать cross-project event | `payload` |
| `tausik_cq_query` | Query cross-project queue | — |

## Мульти-агент и обслуживание

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_team` | Задачи сгруппированные по агентам | — |
| `tausik_events` | Audit log (events) | — |
| `tausik_update_claudemd` | Обновить динамическую секцию в CLAUDE.md | — |
| `tausik_fts_optimize` | Оптимизировать FTS5 индексы | — |

## Codebase RAG (отдельный опциональный MCP-сервер)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `search_code` | Поиск кода через RAG-индекс | `query` |
| `search_knowledge` | Поиск в knowledge base | `query` |
| `reindex` | Реиндексация кодбазы | `mode` (incremental/full), `max_seconds` (soft limit, только для full). v1.5: stderr-прогресс каждые 100 файлов; truncated=true при таймауте. |
| `rag_status` | Статус RAG-индекса | — |
| `archive_done` | Архивировать выполненные задачи | — |
| `cache_web_result` | Кешировать web-результат | `query`, `content` |
| `search_web_cache` | Поиск кешированных web-результатов | `query` |

Эти не входят в основной счёт 146 — принадлежат опциональному `codebase-rag` серверу.

## Область tool-поверхности (`mcp.scope_tools_exposure`)

Выключено по умолчанию. Когда вы ставите `mcp.scope_tools_exposure: true` в
`config.json`, сервер сужает рекламируемый tool-list до того, что разрешено
**активной задаче**: объединение объявленных задачей `scope_tools` (ACL SENAR
Rule 2) и всегда-безопасного ядра — целиком семейства `tausik_task_*` и
`tausik_session_*` плюс `tausik_status`, `tausik_verify`, `tausik_doctor`,
`tausik_self_check`, `tausik_update_claudemd` и тулы `*_search`. Прочие тулы
скрыты из списка, что сокращает и токен-стоимость определений тулов, и
поверхность атаки.

Это **fail-open**: все тулы экспонируются, когда нет активной задачи, ни одна
активная задача не объявила непустой `scope_tools`, или область не резолвится —
включение никогда не оставляет без тулов проект, который не объявлял область.
Сокрытие — это UX/токен-оптимизация, а **не** барьер безопасности: скрытый тул,
вызванный напрямую, всё равно проходит существующий scope-энфорсмент, а
write-гейт не тронут. Область пересчитывается каждый раз, когда хост запрашивает
`list_tools` — то есть при каждом подключении к серверу с уже активной задачей.

**Замер стоимости.** Полная авторская поверхность — 146 тула ~ 62 КБ определений
(~15.9k оценочных токенов; `tests/test_mcp_tool_token_cost.py` фиксирует это и
держит храповиком). При отложенной загрузке Claude Code (`ENABLE_TOOL_SEARCH`)
эагерно грузятся только имена, а каждое описание обрезается до 2 КБ — храповой
тест держит каждое описание TAUSIK под этим лимитом, чтобы ничего не срезалось
молча, и проверяет, что имена остаются уникальными и искомыми, чтобы диспетчер по
имени по-прежнему находил нужный тул.

## Запуск Tausik MCP-сервера

Bootstrap-шаг генерирует IDE-specific MCP-launchers под `harness/<ide>/mcp/`. Claude Code читает `.claude/settings.json` (auto-generated). Для регенерации запустите `python .tausik-lib/bootstrap/bootstrap.py --refresh`.
