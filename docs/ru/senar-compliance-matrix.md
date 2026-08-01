[English](/docs/senar-compliance-matrix) | **Русский**

# SENAR v1.5 Core — Матрица соответствия

**Дата:** 2026-06-13 | **Аудиторы:** 6+ независимых review-циклов | **Фреймворк:** TAUSIK v1.7.0

## Quality Gates

| Gate | Требование | Статус | Enforcement | Evidence |
|------|-----------|--------|-------------|----------|
| QG-0 | Цель обязательна | ✅ Реализовано | Hard block | `gate_qg0_check.py` `check_qg0_start()` — ServiceError (через делегатор `service_gates.GatesMixin._check_qg0_start`) |
| QG-0 | AC обязательны | ✅ Реализовано | Hard block | `gate_qg0_check.py` `check_qg0_start()` — ServiceError (через делегатор `service_gates.GatesMixin._check_qg0_start`) |
| QG-0 | Негативный сценарий в AC | ✅ Реализовано | Hard block | `gate_negative_scenario.py` `NEGATIVE_SCENARIO_KEYWORDS` + `has_negative_scenario()` (30+ en+ru); проверяется внутри `gate_qg0_check.check_qg0_start()` |
| QG-0 | Объявление scope | ✅ Реализовано | Hard (medium/complex) | `gate_qg0_check.py` `check_qg0_start()` — medium/complex-задача без `scope`/`scope_paths` бросает ServiceError (opt out `qg0.scope_hard_gate=false`); simple/unset остаётся warning'ом. `scope_exclude` — по-прежнему совещательный warning в stderr. |
| QG-0 | Обнаружение security surface | ✅ Реализовано | Warning | `gate_qg0_check.py` `SECURITY_KEYWORDS` + `SECURITY_AC_KEYWORDS` (re-export из `service_gates` для backward-compat) |
| QG-2 | AC проверены с evidence | ✅ Реализовано | Hard block | `gate_ac_check.py` `verify_ac()` — flag + notes + per-criterion. НЕТ `--force` байпаса. (через делегатор `service_gates.GatesMixin._verify_ac`) |
| QG-2 | Шаги плана выполнены | ✅ Реализовано | Hard block | `gate_ac_check.py` `verify_plan_complete()` — JSON план (через делегатор `service_gates.GatesMixin._verify_plan_complete`) |
| QG-2 | Scoped pytest gate | ✅ Реализовано | Hard block | `service_verification.py` — basename match `tests/test_<file>.py` per `relevant_files` (нет fallback на full suite, когда files supplied) |
| QG-2 | Verify cache (10 min TTL) | ✅ Реализовано | Skip-on-hit | таблица `verification_runs` — same `files_hash` + green = skip; security paths байпасят cache |
| QG-2 | Quality gates (pytest/ruff) | ✅ Реализовано | Hard block | `gate_runner.py` + `service_gates.py` `_run_quality_gates()` |
| QG-2 | Checklist верификации (4 тира) | ✅ Реализовано | Warning | `gate_ac_check.py` `check_verification_checklist()` + `determine_checklist_tier()` авто-тир — v1.5 дополнительно прогоняет `service_ac_evidence.build_report()` и сообщает о per-AC покрытии, отсутствующих test-ref и негативных сценариях (через делегатор `service_gates.GatesMixin._check_verification_checklist`) |
| QG-2 | Root cause для дефектов | ✅ Реализовано | Warning | `service_task.py` `task_done()` — проверка ключевых слов |
| QG-2 | Захват знаний | ✅ Реализовано | Warning | `service_task.py` `task_done()` — подсчёт memory/decision |

**Результат: 13/13 реализовано.** Уровни enforcement соответствуют спецификации SENAR.

## Правила

| Правило | Описание | Статус | Enforcement | Evidence |
|---------|---------|--------|-------------|----------|
| 1 | Задача перед кодом | ✅ Реализовано | Hard (hook) | `hooks/task_gate.py` блокирует Write/Edit без активной задачи |
| 2 | Границы scope | ✅ Реализовано | Hard (hook + QG-0) | `hooks/scope_write_gate.py` блокирует Write/Edit вне `scope_paths` активной задачи; `hooks/bash_write_gate.py` распространяет тот же вердикт на оболочечные записи; QG-0 жёстко блокирует старт medium/complex без объявленного scope. `scope_exclude` — совещательный. |
| 3 | Проверка по критериям | ✅ Реализовано | Hard | QG-0 + QG-2 совместный enforcement |
| 4 | Внешнее состязательное ревью | ✅ Реализовано | Hard (закрытия с тонким доказательством) | `risk_l3_trigger.py` блокирует `task_done` с тонким доказательством, пока не записан L3-ревью (`tausik review record --type L3`); ревьюер — сепаратный по модели, read-only субагент `tausik-external-reviewer` (`external_reviewer.py`, разделение обязанностей). Opt out `risk.l3_block_on_high=false`. Отбор ОПИСЫВАЕТ доказательство закрытия, а не предсказывает побег дефекта (AUC 0.4820 — решение #212). |
| 5 | Checklist верификации | ✅ Реализовано | Hard (substantial/deep) / Warning | `gate_ac_check.py` `checklist_hard_block()` жёстко блокирует тиры substantial/deep, чьи AC не ссылаются на существующий тест; ниже — эскалирующий warning (4-тировая авто-детекция). Opt out `task_done.checklist_hard=false`. |
| 6 | План отката | ✅ Реализовано | Hard (medium/complex) | `gate_qg0_check.py` `check_qg0_start()` — medium/complex-задача без `rollback_plan` бросает ServiceError на `task_start`; unset complexity предупреждает. |
| 7 | Root cause для дефектов | ✅ Реализовано | Warning | Обнаружение ключевых слов в notes |
| 8 | Захват знаний | ✅ Реализовано | Warning | Подсчёт memory/decision + `--no-knowledge` opt-out |
| 9.1 | Нет кода без задачи | ✅ Реализовано | Hard (hook) | То же что Rule 1 |
| 9.2 | Лимит сессии (180 мин **active**) | ✅ Реализовано | Hard block | Bounded gap-based active time (`Σ min(Δ, threshold)`, default threshold 10 мин — длинный AFK клипуется до threshold'а, v14b-session-active-time). `service_gates.py` блокирует `task_start` при >180 мин active; `status` показывает "X min active / Y min wall"; `session extend` и `session recompute` доступны. Threshold настраивается через `session_idle_threshold_minutes`. |
| 9.3 | Checkpoint каждые 30-50 вызовов | ✅ Реализовано | Warning (авто) | MCP счётчик в meta, warning при 40 вызовах, сброс при handoff |
| 9.4 | Документирование dead ends | ✅ Реализовано | Instruction + tooling | `dead_end()` + инструкции в скиллах + `/end` проверка |
| 9.5 | Периодический аудит | ✅ Реализовано | Warning | `audit_check/mark` + интеграция в `/start` |

**Результат: 13/13 реализовано.**

### Gaps и план закрытия

| Gap | План | Приоритет |
|-----|------|-----------|
| ~~Rule 2: `scope_exclude` не проверяется~~ | ✅ FIXED — добавлено warning для medium/complex задач | Done |
| ~~Rule 9.3: Нет автоматического счётчика checkpoint'ов~~ | ✅ FIXED — MCP-счётчик + warning на 40 вызовах + сброс при handoff | Done |

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
| MCP coverage (124 инструмента) | ✅ Реализовано | `tools.py` + `tools_extra.py` — (117 project + 7 brain) |
| Batch execution (`/run`) | ✅ Реализовано | `plan_parser.py` + скилл `/run` |
| Structured logs (task_logs + FTS5) | ✅ Реализовано | `backend_schema.py` + `service_task.py:task_log` |
| Fake test detection | ✅ Реализовано | `/review` — 10 паттернов |
| Skills система | ✅ Реализовано | 13 core + 20 vendor (markitdown, zero-defect, skill-test и др. — opt-in; bundles via `tausik skill bundle`) — `service_skills.py` + `tausik-skills` репо |
| Hooks система | ✅ Реализовано | 22 Python-хука + 1 shell pre-commit на PreToolUse / PostToolUse / SessionStart / SessionEnd / Stop / UserPromptSubmit |
| Реестр ролей | ✅ Реализовано | Гибрид: SQLite-метаданные + `harness/roles/{role}.md` профиль; CRUD CLI + 6 MCP инструментов |
| Doctor health check | ✅ Реализовано | `tausik doctor` + `tausik_doctor` MCP — 4 группы (venv/DB/MCP/skills) + drift |
| Zero-defect skill | ✅ Реализовано | `/zero-defect` (Maestro-inspired): read-before-write, verify-before-claim, never-hallucinate-APIs |

## Общий результат

| Категория | Реализовано | Частично | Нет | Оценка |
|-----------|-------------|----------|-----|--------|
| Quality Gates (13) | 13 | 0 | 0 | **100%** |
| Правила (13) | 13 | 0 | 0 | **100%** |
| Метрики (6) | 6 | 0 | 0 | **100%** |
| Исследования (3) | 3 | 0 | 0 | **100%** |
| **Итого (35)** | **35** | **0** | **0** | **100%** |

**Соответствие SENAR v1.5 Core: 100%.** Все gaps закрыты.
