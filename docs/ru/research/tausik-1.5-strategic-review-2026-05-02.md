---
title: "TAUSIK 1.5 — стратегический ревью v1.4 и приоритеты"
subtitle: "Артефакт задачи v14-strategic-review-10-1-4"
lang: ru
date: 2026-05-02
status: review-decided
---

# TAUSIK 1.5 — стратегический ревью v1.4

**Контекст:** перед началом работ по 1.5 проведён комплексный ревью качества реализации десяти эпиков `v14-*` плюс известного бага `task_done hang`. Все эпики помечены `done` в `.tausik/tausik.db`, но без публичного ревью. Цель документа — зафиксировать gaps, сформулировать видение по каждой теме и согласовать приоритеты для v1.5 backlog.

## Сводный verdict

| # | Эпик | Реализация | Качество | Главный gap |
|---|------|------------|----------|-------------|
| 1 | brain-snippets | 5/5 tasks, ~660 LOC + EN/RU docs | средне-хорошее | нет CLI `propose_artifact`, taxonomy не в Notion как column |
| 2 | model-prompts | 4/4 done, но «бумажно» | слабое | `model_routing.py` нигде не вызывается, hint в `task_next` не интегрирован |
| 3 | verify-integrity | 3/3 + glossary, conftest shim | хорошее | doctor warning не доходит до output, security-paths не enumerated |
| 4 | cost-telemetry | 5/5, schema + pricing + rollup real | хорошее | прайс хардкод в hook, нет epic/story rollup, нет TTL |
| 5 | project-hygiene | 4/4 (+1 retro), только spec + dry-run | слабое | нет реального archive/dedupe action, --confirm зарезервирован |
| 6 | test-philosophy | 3/3, doc + dedupe-script, без enforcement | среднее | 480 дубль-тестов в suite, AGENTS-секция 9 строк |
| 7 | doc-automation | 3/3, gen_doc_constants + CI drift | хорошее | gaps минимальны |
| 8 | dead-code-audit | 3/3, инструменты есть, чистка частичная | среднее | результаты audit'ов не превращены в чистку |
| 9 | skill-store | 3/3, one-pager + deep dive + security | хорошее | gaps минимальны |
| 10 | framework-lean | 3/3, context_tier работает в bootstrap | хорошее | нет авто-regen при смене tier в config |

**TL;DR:** «фундамент» (verify, cost, doc-automation, lean, skill-store) в живом виде. «Бумажные» эпики — model-prompts, project-hygiene, частично test-philosophy и dead-code-audit. В `.tausik/config.json` HEAD нет следов `auto_verify=false` — обхода в текущем коммите нет.

## Bug `task_done hang` — решён в v1.4

`verify --task <slug>` → запись в `verification_runs` (TTL 600s) → `task done` читает cache. Hang возможен только в намеренных случаях:

1. `task done` без предварительного `verify` — intentional block, не hang;
2. `auto_verify=true` в config — legacy CI-only path, документирован в [`scripts/service_gates.py`](https://github.com/Kibertum/tausik-core/blob/main/scripts/service_gates.py) lines 425-620;
3. Security-sensitive файлы + cache miss — re-verify по дизайну.

Регрессия покрыта 9 тестами в [`tests/test_verify_first_contract.py`](https://github.com/Kibertum/tausik-core/blob/main/tests/test_verify_first_contract.py) + 61 в [`tests/test_service_verification.py`](https://github.com/Kibertum/tausik-core/blob/main/tests/test_service_verification.py). **Gap:** нет timeout-теста, который проверяет, что `verify` с симулированным виснущим pytest даст явную ошибку «aborted, run separately», а не молча висит.

## Auto_verify bypass — статус и политика

* `.tausik/config.json` сейчас чистый (gates pytest+mypy enabled, никакого `auto_verify` в коммитах HEAD).
* `auto_verify` в коде — **легитимная legacy опция** для CI ([`service_gates.py:425-620`](https://github.com/Kibertum/tausik-core/blob/main/scripts/service_gates.py)), задокументирована.
* «Обход» = **локально включить `auto_verify=true`, чтобы `task done` не падал** — таких следов в текущем checkpoint нет.

**Convention** (TAUSIK memory #71, ru): никогда не правим `auto_verify`/`gates_disable` в `config.json` ради скорости локальной разработки фреймворка. Если task_done медленный — заводим defect-задачу на `service_verification.py` / `gate_runner.py` / verify cache.

## Видение по 10 темам

### 1. Shared Brain — сниппеты и артефакты

**Видение:** Notion как первичное хранилище — правильный выбор: метаданные + cross-project поиск + удобный UI для ревью. Git-репо как опциональный «низший слой» только для самого кода (`code_url` поле в карточке), без обязательной синхронизации. Human gate (через `propose → review → publish`) обязателен — модели путают «универсальное» с «случайным».

**Рекомендация:** добавить CLI команду `tausik artifact propose <slug>` с draft-flow и ревью «руками» через одобрение в Notion. Артефакт классифицируется по полю `kind` (rbac, auth, payment-pipe, migration-pattern), не свободным текстом. Tradeoff: чем строже схема — тем меньше артефактов будет публиковаться, но выше доверие.

### 2. Мульти-модельные промпты

**Видение:** один SKILL.md с YAML frontmatter `model_variants:` (а не отдельные `variants/<model>.md`) — тогда core инструкция общая, а 5-10 строк правок под GPT/Gemini/etc живут рядом. Auto-switch модели по типу задачи опасен — модель и агент не одно и то же. Лучше **подсказывать**: `task plan` советует «эта задача deep — рекомендуется Opus/Sonnet 4.6+», но финальное слово за пользователем.

**Рекомендация:** довести `model_routing.py` до реальной интеграции в `task_next` (строка `recommend: <model>`) + 1-2 демо-skill с `model_variants` в frontmatter. Auto-switch — отложить. Tradeoff: глубокая правка skills под каждую модель быстро превращается в ад поддержки — лучше общее ядро + точечные variants там где замеряли деградацию.

### 3. Целостность Verify-First

**Видение:** усилить doctor — если в `.tausik/config.json` найден `auto_verify=true` И не CI environment, doctor должен предупреждать жёлтым и логировать в `events`. Сейчас warning есть в коде ([`project_cli_doctor.py:45`](https://github.com/Kibertum/tausik-core/blob/main/scripts/project_cli_doctor.py)), но не показывается в реальном выводе.

**Рекомендация:** P0 — surface auto_verify warning в doctor + audit event в events. Tradeoff: жёсткий запрет auto_verify сломает CI-пайплайны где это нужно, поэтому warning + audit, не block.

### 4. Бюджет (токены и доллары)

**Видение:** дашборд по 3 разрезам (task / story / epic / session) важнее веб-UI. Прайс должен браться из `.tausik/config.json` (поле `llm_pricing_usd_per_million`), хук уже **проверяет** этот ключ — нужно сделать его первичным источником, а хардкод — fallback. Не пытаться измерить точно (провайдеры дают разный shape), достаточно «±20% оценки».

**Рекомендация:** P1 — `tausik metrics --cost --by epic|story|task|model` с одним общим ranking-кодом. Anomaly hint — если task потратила >2× медианы по своему tier, флагнуть в task_log. Tradeoff: хуков ±20%, точный — потребует billing API провайдеров; для self-management ±20% достаточно.

### 5. Гигиена долгоживущего проекта

**Видение:** вместо удалений — «холодное хранилище». Done-задачи >90 дней переходят в read-only `tasks_archive` таблицу + FTS5 индекс, убираются из стандартных list/next/metrics, но доступны через `--include-archived`. То же для memory: `pattern`/`convention` стареют в `_cold` категорию через 180 дней. Никаких физических удалений.

**Рекомендация:** P1 — `tausik archive run --confirm` (move, не delete). Memory dedupe — отдельным шагом, через классификатор «дубль/частичный/уникальный» с человеческим apply. Tradeoff: автоматический dedupe модели легко склеит две разные памяти в одну — поэтому «предлагает 5 кандидатов на merge, юзер apply» а не «удалил сам».

### 6. Философия тестов

**Видение:** проблема не в количестве тестов, а в отсутствии правил подачи. У TAUSIK сейчас 2300+ тестов — реальная польза от ~60% (boundary, security, contract), 40% — повторы того же сценария на разных входах. Вместо удаления — параметризация: 12 одинаковых тестов на bash firewall в [`tests/test_hooks.py`](https://github.com/Kibertum/tausik-core/blob/main/tests/test_hooks.py) → 1 параметризованный с 12 кейсами.

**Рекомендация:** P0 — расширить AGENTS test-discipline до 30-40 строк с конкретными правилами. P1 — пройтись по top-10 групп из dedupe report и сконсолидировать руками (~60 тестов уйдёт в ~6 параметризованных). Tradeoff: агрессивный dedupe скрывает регрессии — поэтому только структурные дубли, не семантические.

### 7. Автоматизация документации

**Видение:** расширить генератор на ещё 3 факта: количество skill-плагинов, число задействованных стэков, статусы quality gates. Добавить link-check для внутренних `[text](path)` ссылок (mkdocs-стиля, без MkDocs самого). Это уберёт 90% «правок числа везде». EN/RU mirror check — есть в `audit_stale_docs.py`, можно довести до warning в `doctor`.

**Рекомендация:** P1 — расширить `gen_doc_constants.py` + `doc_link_check.py` в pre-commit. Tradeoff: генерируемые блоки в markdown тяжелы для агента (нужны маркеры `<!-- generated:start -->`), но без них первый же агент перепишет константы вручную.

### 8. Аудит мусорного/мёртвого кода

**Видение:** один раз в релиз — `tausik audit cleanup --apply` собирает кандидатов из всех 3 аудитов, генерит PR-плейн со списком файлов/функций к удалению, юзер ревьюит и применяет. Без human gate автоудаления нельзя.

**Рекомендация:** P3 — между релизами batch-проход (~раз в 2 месяца). Параллельно — allowlist в каждом audit-script (`# audit:keep` декоратор/комментарий) для известных false-positives. Tradeoff: рефлекс «удалить если orphan» убил у меня код в одном из проектов с lazy-import'ами — поэтому 3 ревьюера + dry-run обязательны.

### 9. Магазин скиллов

**Видение:** нынешний UX командный, как `pip` — нормально для разработчика, но новичку непонятно «active vs installed vs available». Решение — один экран `tausik skill list` с ASCII-таблицей: name | status | repo | trust-level (official/community/--force). Команды install/activate — логировать trust-level в events.

**Рекомендация:** P3 — улучшить UX `skill list` (читабельность) + `tausik skill explain <name>` (что делает + где код + триггеры). Security модель уже есть. Tradeoff: «магазин» в смысле Marketplace потребовал бы централизованный реестр и модерацию — federated подход self-hosted фреймворку правильнее.

### 10. Прожорливость по токенам

**Видение:** главный пожиратель — `/start` (memory_block + status + handoff + brain searches + audit_check). Один `/start` в сессии #42 потратил >50 tool calls. Решение — lazy /start: загружать только status+handoff, memory_block и brain primer — по запросу (`/recall`). Второй пожиратель — handoff'ы и task_log'и тянут весь markdown целиком; для длинных — пагинация (последние 20 строк).

**Рекомендация:** P0 — сделать `/start --tier minimal` стандартом и переименовать текущий в `/start --full`. MCP tools должны иметь `compact: bool` (как у `tausik_status`) — одна строка JSON по умолчанию, человеческий текст по флагу. Третий шаг — `tausik_help <tool>` и убрать large list-of-tools при старте. Tradeoff: агрессивный trim ломает «cold start» юзера — `context_tier=standard` дефолт, явный переключатель для опытных.

## Приоритеты v1.5 backlog

| Prio | Эпик | Slug-кандидат | Эпик-источник |
|------|------|--------------|----------------|
| **P0** | `/start --minimal` дефолт + lazy memory_block | `v15-lean-start` | 10 |
| **P0** | doctor auto_verify warning surfacing + audit event | `v15-doctor-autoverify` | 3 |
| **P0** | AGENTS test-discipline → 30+ строк с конкретикой | `v15-test-discipline` | 6 |
| **P1** | model_routing.py интеграция в `task_next` + hint | `v15-model-routing` | 2 |
| **P1** | `tausik archive run --confirm` (real move, not dry) | `v15-archive-real` | 5 |
| **P1** | `metrics --cost --by epic\|story\|task\|model` | `v15-cost-rollup` | 4 |
| **P1** | doc_link_check.py + EN/RU mirror в doctor warning | `v15-doc-link-check` | 7 |
| **P2** | `tausik artifact propose <slug>` CLI flow + classifier | `v15-artifact-propose` | 1 |
| **P2** | task_done timeout-тест + abort message | `v15-verify-timeout` | bug 11 |
| **P3** | top-10 dedupe groups → параметризация | `v15-dedupe-batch` | 6 |
| **P3** | `tausik skill list` UX (table + trust column) | `v15-skill-list-ux` | 9 |
| **P3** | audit cleanup — ручной batch с allowlist | `v15-cleanup-batch` | 8 |

## Связь с предыдущими документами

* Мастер-план v1.4 — `tausik-1.4-epics-master-plan-2026-05-01.md` (не вошёл в репозиторий)
* Readiness audit — `tausik-1.4-readiness-audit-v2-2026-05-01.md` (не вошёл в репозиторий)
* Composer retro — [`tausik-1.4-composer-retro-2026-05-02.md`](tausik-1.4-composer-retro-2026-05-02.md)
* Pytest dedupe — [`tausik-1.4-pytest-dedupe-2026-05-02.md`](tausik-1.4-pytest-dedupe-2026-05-02.md)

## Versioning

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-05-02 | Первый комплексный ревью v1.4 + приоритеты v1.5 |
