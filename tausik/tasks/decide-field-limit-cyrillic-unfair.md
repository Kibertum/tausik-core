---
slug: decide-field-limit-cyrillic-unfair
title: "tausik_decide 'decision' лимит 512 считает БАЙТЫ — кириллица штрафуется 2× (~250 симв)"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/tausik_utils.py (MAX_DECISION const), scripts/service_knowledge.py (decide validation)"
scope_exclude: "MAX_TITLE (task title limit — не трогать), validate_length сигнатуру не менять"
relevant_files:
  - "scripts/tausik_utils.py"
  - "scripts/service_knowledge.py"
  - "tests/test_service_knowledge_decide.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:07:48Z"
---

## Goal

Поле decision в tausik_decide ограничено 512 (по факту байт UTF-8, не символов), поэтому кириллический headline обрезается на ~250 символах — в русскоязычных проектах это постоянный папакут (сессия #139: 6 попыток попасть в лимит). Решить: считать лимит в СИМВОЛАХ, а не байтах (убирает 2× штраф за кириллицу), и/или поднять до 1024. Симметрично проверить rationale и другие текстовые поля (memory content, task goal/AC) на байт-vs-символ. Dogfooding-баг.</parameter>
<parameter name="complexity">simple

## Acceptance Criteria

AC1. Подтверждено тестом: validate_length считает СИМВОЛЫ (len(str)), не байты — байтового 2× штрафа за кириллицу нет ни в одном текстовом поле (decision, rationale, memory content, task goal/AC). Премиса «512 байт» опровергнута (dead-end #324).
AC2. Поле decision получает СОБСТВЕННЫЙ символьный лимит MAX_DECISION=1024 (отдельно от общего MAX_TITLE=512, который остаётся для task title), чтобы снять реальную догфудинг-фрикцию многословных кириллических headline (#139).
AC3. service_knowledge.decide валидирует decision по MAX_DECISION; rationale — тоже (симметрично, char-based).
AC4. Тест: 1000-символьный кириллический decision (2000 байт) проходит; >1024 символов отклоняется с честным сообщением про символы.
AC5. НЕГАТИВ: task title по-прежнему ограничен 512 (MAX_TITLE не задет); тесты остальных полей зелёные.

## Plan

## Rollback

git revert коммита; лимит — чистая константа, откат безопасен (только расширяет допустимое, не сужает)

## Journal

- 2026-07-26T22:07:44Z [implementation] — AC1 ✓ validate_length считает символы (len(str)); dead-end #324 — байтовая теория опровергнута тестом test_decision_limit_counts_symbols_not_bytes_cyrillic_not_penalised (1000 кир.симв = 2000 байт → PASS). AC2 ✓ MAX_DECISION=1024 добавлен в tausik_utils.py отдельно от MAX_TITLE=512. AC3 ✓ decide валидирует и decision, и rationale по MAX_DECISION (service_knowledge.py:140-146). AC4 ✓ >1024 отклоняется с сообщением про 'char' (test_decision_over_symbol_limit_rejected_with_symbol_message). AC5 ✓ NEGATIVE: task title остаётся 512 (test_task_title_still_capped_at_max_title_not_widened). Verify run #1446: scoped pytest 2 файла PASS. Domain: 1024-символьный русский headline (частый реальный кейс #139) теперь проходит; лимит семантически валиден. CHANGELOG EN+RU обновлены.
