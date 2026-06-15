---
title: "TAUSIK 1.4 — ретро Cursor/Composer batch и план релиза"
subtitle: "Что Composer сделал, что закрыто без verify, что осталось до 1.4.0"
lang: ru
date: 2026-05-02
session: "#42"
preceded_by: "tausik-1.4 master plan (removed pre-release)"
---

# TAUSIK 1.4 — ретро Cursor/Composer batch

## TL;DR

- За один batch в Cursor/Composer **закрыто 28 v14-* задач**, написано **~20 новых файлов** (скриптов + EN/RU доки), **70 файлов модифицировано**, **+2242 / −467** строк.
- **5 эпиков** v14-* перешли в `done`: `brain-snippets`, `model-prompts`, `verify-integrity`, `cost-telemetry`, `framework-lean`.
- **5 эпиков active** с **7 planning** задачами (hygiene/test/doc/audit/skill-store).
- **Pytest**: 2505 passed / **1 failed** (test pollution в `test_task_next_model_hint::test_hint_via_config_file`) / 7 skipped. **Test count 2318 → 2513**.
- **Версия `1.3.7` не bumped**, `CHANGELOG.md` для 1.4 не написан, ничего не закоммичено.
- Главный системный риск: часть done-задач закрыта с `WARN: no relevant_files passed — scoped gates SKIPPED` — pytest-gate реально не отрабатывал.

## 1. Что Composer сделал хорошо

### 1.1 Покрытие master-плана
Из 35 запланированных v14-* задач **28 закрыты** ровно по AC из мастер-плана, 7 в planning соответствуют исходным "tail" задачам (audit/hygiene/CLI). Композер не выдумал новых слугов, шёл по списку.

### 1.2 Документы
18 новых doc-файлов (9 EN + 9 RU mirror) — соответствует конвенции #55:
- `brain-artifact-taxonomy`, `brain-search-ranking`, `memory-merge-guidelines`,
- `skill-ecosystem`, `skill-profiles`, `task-archive-spec`,
- `testing-principles`, `verify-glossary`.

Качество выборочной проверки `verify-glossary.md`: чёткое разведение **opt-out / bypass / shim**, ровно та проблема, ради которой эпик заведён. Документ содержит таблицы, anti-patterns, doc review checklist.

### 1.3 Новые скрипты (модули)
- `scripts/brain_artifact_card.py`, `brain_artifact_taxonomy.py`, `brain_publish_cli.py`, `brain_publish_flow.py`, `brain_store_format.py`, `brain_cli_ops.py` — Brain artifact pipeline (эпик 1).
- `scripts/skill_profile.py` — multi-model profile resolver (эпик 2).
- `scripts/gen_doc_constants.py` + `docs/_generated/constants.json` — single source of truth для версии/MCP counts (эпик 7).
- `scripts/mcp_tool_counts.py` — derive counts from harness/* (эпик 7).
- `scripts/verify_recent_lookup.py` — compat helper для verify cache (эпик 3).

### 1.4 Новая структура
- `harness/schemas/brain-artifact-card.schema.json` — JSON Schema (эпик 1).
- `harness/skills/_profile-demo/` — демо мульти-модельного скилла (эпик 2). `_` prefix → bootstrap пропускает в реальной генерации (защита от утечки демо).
- `.qwen/` + `QWEN.md` + изменения в `bootstrap_qwen.py` — **бонус сверх мастер-плана**: ещё одна IDE поддержана (Qwen Code agent). Согласуется с философией multi-model.

### 1.5 Тесты
+10 новых test-файлов: `test_bootstrap_model_profile`, `test_brain_artifact_external_repo`, `test_context_tier`, `test_doctor_auto_verify_hint`, `test_gen_doc_constants`, `test_llm_pricing_config`, `test_mcp_doc_tool_counts`, `test_skill_profile`, `test_task_next_model_hint`, `test_metrics_session_usage`. Полный suite: **2318 → 2513** (~+195).

## 2. Что Composer сделал плохо

### 2.1 Test pollution (release blocker)
`tests/test_task_next_model_hint.py::TestTaskNextModelHint::test_hint_via_config_file` падает в full suite, проходит в isolation. Диагноз: `monkeypatch.chdir(tmp_path)` + чтение `.tausik/config.json` — какой-то предыдущий тест оставляет cwd-state, или `load_config` кэширует значение на уровне модуля. Defect.

### 2.2 SKIPPED scoped gates на закрытии задач
Выборочная проверка показала: `v14-bootstrap-context-tier`, `v14-pricing-table-config`, `v14-doctor-auto-verify-hint` закрыты с `WARN: no relevant_files passed — scoped gates SKIPPED`. Gates прошли только filesize. По нашему правилу dead-end #66 это анти-паттерн — но в этом случае agent проигнорировал warning и закрыл задачу.

Реальный pytest показывает зелёным эти конкретные тесты, **поэтому проблема методологическая, а не функциональная**. Но мы в правах требовать retro-fix: пройти по списку done-задач и в `notes` явно указать `relevant_files`, чтобы аудит был воспроизводим.

### 2.3 Подозрительно быстрые `task_done`
`v14-task-rollup-cost`: `started_at: 11:04:58Z, completed_at: 11:05:01Z` — 3 секунды. Реально таких задач (схема + service + CLI + 2 IDE MCP + tests) за 3с не сделать. Видимо `task_start` вызвали уже после написания кода — нарушение SENAR Rule 9.1 ("задача перед кодом"). Но evidence в `notes` корректное.

### 2.4 Drift между статусом и реальностью
- `CLAUDE.md` строка `Tasks: 0/1 done` (auto-generated) — **устаревшая**, в БД 612/620 задач (585+27 v14-done).
- `CLAUDE.md` строка `pytest tests/ -v # 2318 тестов` — устаревшая, реально 2513.
- Версия `1.3.7` всюду; нет ни записи в CHANGELOG.md о 1.4, ни bump в pyproject.toml.

### 2.5 Не закоммичено
70 modified + 30+ untracked файлов в одной куче. Без splittinga по эпикам ревью будет невозможным.

## 3. Покрытие AC по эпикам

| Эпик | Status | Tasks (done/total) | Замечания |
|------|--------|--------------------|-----------|
| `v14-brain-snippets` | done | 5/5 | Богатый pipeline (taxonomy → schema → publish → search → external_repo). Тесты есть. |
| `v14-model-prompts` | done | 4/4 | Skill profiles + bootstrap env + AGENTS.md table + task_next hint. **Hint-тест flaky.** |
| `v14-verify-integrity` | done | 3/3 | Glossary + doctor hint + conftest comment. AC лаконичные, реализация выглядит ровно. |
| `v14-cost-telemetry` | done | 5/5 | usage_events + pricing config + ingest MVP + rollup + metrics --cost. Подозрительно быстрые close-ы. |
| `v14-framework-lean` | done | 3/3 | context_tier + status compact + AGENTS trim. AC по факту dorабатывался без relevant_files. |
| `v14-project-hygiene` | active | 2/3 | Осталось `v14-hygiene-cli-stub` (CLI команда). |
| `v14-test-philosophy` | active | 2/3 | Осталось `v14-pytest-dedupe-audit` (отчёт о дублях). |
| `v14-doc-automation` | active | 2/3 | Осталось `v14-ci-doc-check` (CI hook). |
| `v14-dead-code-audit` | active | 0/3 | Все три задачи в planning: vulture/ruff, stale-docs, orphan-files. |
| `v14-skill-store` | active | 2/3 | Осталось `v14-skill-cli-help-pass` (--help review). |

## 4. План до релиза 1.4.0

### Фаза A — стабилизация (must-have, до коммита)

| # | Задача | Owner | Статус |
|---|--------|-------|--------|
| A1 | Починить `test_hint_via_config_file` (test pollution) | new defect | TODO |
| A2 | Bump версии `1.3.7 → 1.4.0` (`pyproject.toml`, `__version__`, `docs/_generated/constants.json`) | new task | TODO |
| A3 | Записать CHANGELOG.md секцию `1.4.0` (EN + RU mirror) с разбивкой по эпикам | new task | TODO |
| A4 | Обновить `CLAUDE.md` Current State (test count 2513, version 1.4, tasks 612/620) | auto via `tausik update-claudemd` | TODO |
| A5 | Прогнать `.tausik/tausik doctor` + `tausik gates status` после bump | smoke check | TODO |
| A6 | Разбить uncommitted diff на ~6 коммитов по эпикам | release task | TODO |

### Фаза B — закрыть active эпики (должно влезть в 1.4)

7 planning-задач из мастер-плана. Приоритет внутри фазы (по полезности и зависимости):

| # | slug | Эпик | Усилие | Комментарий |
|---|------|------|--------|-------------|
| B1 | `v14-ci-doc-check` | doc-automation | light | Прямая зависимость от `gen_doc_constants.py` (уже есть). Pre-commit или CI step. |
| B2 | `v14-skill-cli-help-pass` | skill-store | trivial | Чеклист сообщений + snapshot. Снимает hot UX-проблему. |
| B3 | `v14-hygiene-cli-stub` | project-hygiene | light | `tausik hygiene --dry-run`. Реализует спеку из `task-archive-spec.md`. |
| B4 | `v14-audit-orphan-files` | dead-code-audit | light | Скрипт-отчёт, не удаление. |
| B5 | `v14-audit-stale-docs` | dead-code-audit | light | Скрипт-отчёт. |
| B6 | `v14-audit-unused-python` | dead-code-audit | moderate | vulture/ruff с белым списком. **После B5** (могут пересекаться). |
| B7 | `v14-pytest-dedupe-audit` | test-philosophy | light | Отчёт о дублях — может вытащить дубли пост-Composer (он любит копипасту тестов). |

### Фаза C — методологический долг (можно отложить в 1.4.x)

| # | Задача | Зачем |
|---|--------|-------|
| C1 | Retro-fix done-задач без `relevant_files` (~7-10 штук) — переоткрыть, добавить relevant_files в notes, верифицировать | Восстановить аудитопригодность |
| C2 | Тест на регрессию: hook/сервис, который **отказывает** в `task_done` если `relevant_files` пуст и `auto_verify=false` | Закрыть процессную дыру окончательно |
| C3 | Добавить в `audit` skill checklist: "проверь, что у `done` задач есть relevant_files" | Правило в SOP |

### Фаза D — релиз

1. PR/коммит-серия на `main` с шапкой `feat(v1.4): release batch`.
2. Tag `v1.4.0`.
3. Push core + skills repos (+ private mirrors).
4. Release notes (бilingual) — копия из CHANGELOG в `docs/{en,ru}/release-notes/v1.4.md`.

## 5. Решения для записи в DB

- **D-A:** Composer-batch не нарушает AC, но методологически закрывал задачи без scoped pytest. Для 1.4 принимаем; в 1.4.1 сделать hook против повтора.
- **D-B:** Qwen IDE добавлен сверх плана и принимается как бонус v1.4.
- **D-C:** Test pollution (A1) блокирует релиз — фиксим до коммита.

## 6. Связанные документы

- Master plan v1.4 — research артефакт удалён перед релизом (см. историю коммитов)
- [Verify glossary EN](/docs/verify-glossary) / [RU](../verify-glossary.md)
- [Testing principles EN](/docs/testing-principles) / [RU](../testing-principles.md)
- Dead end #66 — Закрытие task_done с полным списком relevant_files (исток правила B-A)

## Версионирование

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-05-02 | Первое ретро после Composer batch (session #42) |
