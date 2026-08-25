---
slug: bookmark-corpus-review-what-to-take-and-into-which-release
title: "Разбор корпуса закладок владельца: что из чужой обвязки взять в TAUSIK и в какую версию"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: "scripts/**, bootstrap/**, tests/** — это разбор, а не реализация; из него заводятся отдельные задачи"
relevant_files:
  - "docs/ru/research/bookmark-corpus-review-2026-08.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/docs_lint.py"
  - "scripts/audit_stale_docs.py"
scope_paths:
  - "docs/ru/research/*.md"
  - "docs/en/research/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-11T08:00:59Z"
---

## Goal

Из 284 закладок владельца по обвязке AI-агентов выделены настоящие пробелы TAUSIK, а не пересказ чужих README, и разложены по версиям с ценой и риском.

## Acceptance Criteria

1. Разобраны ВСЕ 284 записи корпуса, а не выборка: срезы A-memory, B-harness, C-standards, D-security, E-other покрыты полностью.
2. Каждая находка названа с тем, что у TAUSIK ЕСТЬ сегодня по этой теме, — иначе это пересказ чужого README, а не находка.
3. Находки разложены по версиям (1.9 / 2.0 / исследование) с ценой и риском.
4. НЕГАТИВНЫЙ сценарий: находка, дублирующая существующую возможность TAUSIK, ОТБРАСЫВАЕТСЯ явно, с указанием, чем она дублируется. Список «двадцать идей», где половина уже сделана, считается провалом разбора.
5. НЕГАТИВНЫЙ сценарий: числа из LLM-сводок [вычеркнуто: third-party-service] НЕ принимаются на веру — звёзды, даты и заявления о бенчмарках проверяются по источнику, прежде чем попасть в план.

## Plan

## Rollback

Артефакт разбора лежит в scratchpad; задачи из него заводятся отдельно и откатываются по одной

## Journal

- 2026-08-11T07:58:20Z [implementation] — Чек-лист доказательств. AC-1 (разобраны все 284 записи): ✓ MANUAL: корпус выгружен из продакшена [вычеркнуто: third-party-service] (284 записи, 223 КБ), нарезан на пять срезов A-memory 95, B-harness 74, C-standards 14, D-security 25, E-other 76 — сумма 284. Срезы A, B, C+D розданы трём агентам, E разобран вручную. ✓ MANUAL: нарезка по ключевым словам ОШИБЛАСЬ — Agent Plugins, loopx и ECC попали не в свои срезы. Агенты это обнаружили и пошли в первоисточники: спецификация целиком, changelog протокола, README через gh api. Ошибка зафиксирована в заметке как правило на будущее. AC-2 (каждая находка названа с тем, что есть у TAUSIK): ✓ MANUAL: проверено кодом, а не заявлено — .mcp.json с ${CLAUDE_PROJECT_DIR:-.} (3 вхождения), пин protocolVersion 2024-11-05 в tests/test_mcp_integration.py:119, самотрекаемый долг в knowledge_write.py, докстринг tool_output_truncation_nudge.py «coaching signal, not a censor», отсутствие дедупа чтений в 22 хуках, одно бинарное число в eval_memory_retrieval.py, существующий find_dedupe_candidates, гейт agentskills.io. AC-3 (разложены по версиям с ценой и риском): ✓ MANUAL: 15 задач заведены — 4 в 1.9, 7 в эпик release-110-proof-outward, 4 в research-with-a-death-date. У каждой цена в бюджете вызовов и риск в критериях. Решение #237. AC-4 (дубликаты отброшены явно): ✓ MANUAL: таблица отвергнутого в docs/ru/research/bookmark-corpus-review-2026-08.md — десять позиций с причиной отказа по каждой. Отвергнуты в том числе целые классы: эмбеддинговые системы памяти против принятого решения, обмен знаниями (есть cq_publish), markdown-граф (есть проекция tausik/), поиск по коду (есть codebase-rag). AC-5 (числа не приняты на веру): ✓ MANUAL: звёзды проверены gh api по пяти репозиториям лично мной, агентами — ещё по десятку. Сводки [вычеркнуто: third-party-service] оказались НЕ преувеличены, а занижены: ECC 239 315 при заявленных 182K, граф кода 105 085 при заявленных 70к. Моё исходное подозрение в галлюцинации было неверным, и это записано. Побочный результат: конвенция #384 — планировать по агрегату per-tier (0.63 на 502 закрытиях), а не по строке калибровки n=10, которая за один день дала и 1.06, и 0.63.
