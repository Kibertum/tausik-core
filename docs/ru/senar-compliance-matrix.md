[English](../en/senar-compliance-matrix.md) | **Русский**

# SENAR v1.3 Core — Матрица соответствия

**Дата:** 2026-04-26 | **Аудиторы:** 6+ независимых review-циклов | **Фреймворк:** TAUSIK v1.3.0

## Quality Gates

| Gate | Требование | Статус | Enforcement | Evidence |
|------|-----------|--------|-------------|----------|
| QG-0 | Цель обязательна | ✅ Реализовано | Hard block | `service_gates.py` `_check_qg0_start()` — ServiceError |
| QG-0 | AC обязательны | ✅ Реализовано | Hard block | `service_gates.py` `_check_qg0_start()` — ServiceError |
| QG-0 | Негативный сценарий в AC | ✅ Реализовано | Hard block | `service_gates.py` `NEGATIVE_SCENARIO_KEYWORDS` (30+ en+ru) |
| QG-0 | Предупреждение о scope | ✅ Реализовано | Warning | `service_gates.py` — scope + scope_exclude в stderr |
| QG-0 | Обнаружение security surface | ✅ Реализовано | Warning | `service_gates.py` `SECURITY_KEYWORDS` + `SECURITY_AC_KEYWORDS` |
| QG-2 | AC проверены с evidence | ✅ Реализовано | Hard block | `service_gates.py` `_verify_ac()` — flag + notes + per-criterion. НЕТ `--force` байпаса. |
| QG-2 | Шаги плана выполнены | ✅ Реализовано | Hard block | `service_gates.py` `_verify_plan_complete()` — JSON план |
| QG-2 | Scoped pytest gate | ✅ Реализовано | Hard block | `service_verification.py` — basename match `tests/test_<file>.py` per `relevant_files` (нет fallback на full suite, когда files supplied) |
| QG-2 | Verify cache (10 min TTL) | ✅ Реализовано | Skip-on-hit | таблица `verification_runs` — same `files_hash` + green = skip; security paths байпасят cache |
| QG-2 | Quality gates (pytest/ruff) | ✅ Реализовано | Hard block | `gate_runner.py` + `service_gates.py` `_run_quality_gates()` |
| QG-2 | Checklist верификации (4 тира) | ✅ Реализовано | Warning | `service_gates.py` `_check_verification_checklist()` авто-тир |
| QG-2 | Root cause для дефектов | ✅ Реализовано | Warning | `service_task.py` `task_done()` — проверка ключевых слов |
| QG-2 | Захват знаний | ✅ Реализовано | Warning | `service_task.py` `task_done()` — подсчёт memory/decision |

**Результат: 13/13 реализовано.** Уровни enforcement соответствуют спецификации SENAR.

## Правила

| Правило | Описание | Статус | Enforcement | Evidence |
|---------|---------|--------|-------------|----------|
| 1 | Задача перед кодом | ✅ Реализовано | Hard (hook) | `hooks/task_gate.py` блокирует Write/Edit без активной задачи |
| 2 | Границы scope | ✅ Реализовано | Warning | `scope` + `scope_exclude` предупреждение при старте для medium/complex |
| 3 | Проверка по критериям | ✅ Реализовано | Hard | QG-0 + QG-2 совместный enforcement |
| 5 | Checklist верификации | ✅ Реализовано | Warning | 4-тировая авто-детекция (lightweight/standard/high/critical) |
| 7 | Root cause для дефектов | ✅ Реализовано | Warning | Обнаружение ключевых слов в notes |
| 8 | Захват знаний | ✅ Реализовано | Warning | Подсчёт memory/decision + `--no-knowledge` opt-out |
| 9.1 | Нет кода без задачи | ✅ Реализовано | Hard (hook) | То же что Rule 1 |
| 9.2 | Лимит сессии (180 мин **active**) | ✅ Реализовано | Hard block | Gap-based active time (≥10 мин idle = AFK, не учитывается). `service_gates.py` блокирует `task_start` при >180 мин active; `status` показывает "X min active / Y min wall"; `session extend` и `session recompute` доступны. Threshold настраивается через `session_idle_threshold_minutes`. |
| 9.3 | Checkpoint каждые 30-50 вызовов | ✅ Реализовано | Warning (авто) | MCP счётчик в meta, warning при 40 вызовах, сброс при handoff |
| 9.4 | Документирование dead ends | ✅ Реализовано | Instruction + tooling | `dead_end()` + инструкции в скиллах + `/end` проверка |
| 9.5 | Периодический аудит | ✅ Реализовано | Warning | `audit_check/mark` + интеграция в `/start` |

**Результат: 11/11 реализовано.** Все gaps закрыты.

## Метрики

| Метрика | Статус | Evidence |
|---------|--------|----------|
| Throughput (задач/сессия) | ✅ Реализовано | `backend_queries.py` `get_metrics()` combined query |
| Lead Time (среднее часов) | ✅ Реализовано | `backend_queries.py` `get_metrics()` — julianday * 24 |
| FPSR (% с первой попытки) | ✅ Реализовано | `backend_queries.py` `get_metrics()` — attempts=1 |
| DER (% побега дефектов) | ✅ Реализовано | `backend_queries.py` `get_metrics()` — DISTINCT defect_of |
| Dead End Rate (%) | ✅ Реализовано | `backend_queries.py` `get_metrics()` — memory type=dead_end |
| Cost per Task (часов по complexity) | ✅ Реализовано | `backend_queries.py` `get_metrics()` — GROUP BY complexity |

**Результат: 6/6 реализовано.**

## Section 5.1: Исследования (Explorations)

| Функция | Статус | Evidence |
|---------|--------|----------|
| explore_start (time-bounded, 30 мин по умолч.) | ✅ Реализовано | `service_knowledge.py` — clamps 1-480 мин |
| explore_current (elapsed + over_limit) | ✅ Реализовано | `service_knowledge.py` — UTC elapsed calc |
| explore_end (capture findings) | ✅ Реализовано | `service_knowledge.py` — summary + optional task |

**Результат: 3/3 реализовано.**

## Дополнительные возможности (сверх SENAR Core)

| Функция | Статус | Evidence |
|---------|--------|----------|
| Multi-language gates | ✅ Реализовано | `project_config.py` — 25 default стеков + custom_stacks override |
| MCP coverage (106 инструментов) | ✅ Реализовано | `handlers.py` — 96 project + 10 brain |
| Batch execution (`/run`) | ✅ Реализовано | `plan_parser.py` + скилл `/run` |
| Structured logs (task_logs + FTS5) | ✅ Реализовано | `backend_schema.py` + `service_task.py:task_log` |
| Fake test detection | ✅ Реализовано | `/review` — 10 паттернов |
| Skills система | ✅ Реализовано | 38 skill'ов (16 core + 22 vendor) — `service_skills.py` + `tausik-skills` репо |
| Hooks система | ✅ Реализовано | 19 хуков на PreToolUse / PostToolUse / SessionStart / Stop / pre-commit |
| Реестр ролей | ✅ Реализовано | Гибрид: SQLite-метаданные + `agents/roles/{role}.md` профиль; CRUD CLI + 6 MCP инструментов |
| Doctor health check | ✅ Реализовано | `tausik doctor` + `tausik_doctor` MCP — 4 группы (venv/DB/MCP/skills) + drift |
| Zero-defect skill | ✅ Реализовано | `/zero-defect` (Maestro-inspired): read-before-write, verify-before-claim, never-hallucinate-APIs |

## Общий результат

| Категория | Реализовано | Частично | Нет | Оценка |
|-----------|-------------|----------|-----|--------|
| Quality Gates (13) | 13 | 0 | 0 | **100%** |
| Правила (11) | 11 | 0 | 0 | **100%** |
| Метрики (6) | 6 | 0 | 0 | **100%** |
| Исследования (3) | 3 | 0 | 0 | **100%** |
| **Итого (33)** | **33** | **0** | **0** | **100%** |

**Соответствие SENAR v1.3 Core: 100%.** Все gaps закрыты.
