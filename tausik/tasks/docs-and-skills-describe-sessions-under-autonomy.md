---
slug: docs-and-skills-describe-sessions-under-autonomy
title: "Документация и скиллы описывают сессию при автономной работе: одна страница, одна формулировка, без ритуала"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: medium
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/skills/start/SKILL.md"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/checkpoint/SKILL.md"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_docs_describe_sessions_as_signals.py"
  - "tests/test_bootstrap_generate.py"
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "harness/skills/*/SKILL.md"
  - "bootstrap/bootstrap_templates.py"
  - CLAUDE.md
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - context-pressure-is-a-measured-signal-with-a-basis
  - handoff-is-generated-from-the-journal
completed_at: "2026-09-23T19:10:12Z"
---

## Goal

После четырёх механических задач истории слово «сессия» означает окно хоста с порождаемым handoff и сигналами вместо гейтов. Страницы sessions.md, session-active-time.md, agent-contract.md (Rule 9.2/9.3), quickstart, hooks.md, cli.md, senar-compliance-matrix, CLAUDE.md core и шаблон потребителя (bootstrap) сегодня говорят «180 мин ACTIVE», «/end или session extend», «checkpoint каждые 30–50 вызовов». Цель: все места говорят одно и то же, число порога нигде не набрано руками, а раздел Компакции в CLAUDE.md переносит через сжатие то, что порождаемый handoff всё равно сохранит.

## Acceptance Criteria

1. Перечислены все места с формулировками о лимите/ёмкости/чекпоинте (команда grep по репозиторию приложена в журнале задачи как замер ДО), после правки ни одно не называет число порога руками.
2. Скиллы start/checkpoint/end: /start = session_open + дашборд; /checkpoint = генератор handoff + совет по сигналам; /end = генератор + session end; никакого ручного JSON handoff.
3. Шаблон CLAUDE.md потребителя (bootstrap_templates) несёт ту же строку, что CLAUDE.md core; тест на паритет формулировки.
4. НЕГАТИВНЫЙ: тест проверяет, что docs не обещают отказ там, где механизм даёт совет (фраза «блокируется» рядом с «сессия»/«ёмкость» — находка).
5. EN и RU в паритете; CHANGELOG EN+RU.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-23T18:21:23Z [planning] — ЗАМЕР ДО (grep по docs/ru, docs/en, harness/skills, CLAUDE.md, bootstrap_templates, README): 38 строк о лимите 180 минут, гейте ёмкости и «30–50 вызовах», из них ложных после 1.10 — senar.md (ru/en: «жёсткая блокировка после 180 минут»), model-providers.md (ru/en: «hard, отказывает»), workflow.md (ru/en), mcp.md (ru/en), cli.md (ru/en, раздел лимита и таблица), configuration.md (en), enforcement-coverage.md (en), agent-quickstart.md (en), skills.md (ru/en), скиллы checkpoint и task, CLAUDE.md, bootstrap_templates (HARD_CONSTRAINTS, таблица правил, MCP-строка).
- 2026-09-23T19:10:09Z [implementation] — AC verified: 1. ✓ замер ДО в журнале, после правки test_no_hand_typed_checkpoint_interval_remains и test_no_page_promises_a_session_refusal зелёные по docs ru/en, скиллам, CLAUDE.md и шаблону 2. ✓ скиллы start/checkpoint/end: /start = session_open + дашборд, /checkpoint = генератор handoff + совет по сигналам, /end = генератор + session end, ручного JSON нет 3. ✓ маркеры 'Checkpoint when the signal says so' и 'Context pressure is a signal, not a gate' в tests/test_bootstrap_generate.py (CLAUDE/AGENTS/.cursorrules/QWEN) 4. ✓ НЕГАТИВНЫЙ test_the_detector_would_catch_the_old_wording 5. ✓ EN/RU паритет, CHANGELOG EN+RU. Verify #2751 зелёный.
