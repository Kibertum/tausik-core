---
slug: search-has-no-morphology-and-strips-the-wildcard
title: "Поиск не знает словоформ, а санитайзер вырезает единственный обходной путь"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/fts_morphology.py"
  - "tests/test_fts_morphology.py"
  - "tests/test_fts5_sanitizer.py"
scope_paths:
  - "scripts/backend_queries.py"
  - "scripts/fts_morphology.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:16:32Z"
resolution: null
resolution_reason: null
---

## Goal

Агент, ищущий по русскому корпусу, находит запись независимо от падежа и числа — либо получает честно названную границу и работающий приём вместо неё. Сейчас он не получает ни того, ни другого.

## Acceptance Criteria

AC1. КОРЕНЬ ДОКАЗАН КОДОМ, А НЕ ЗАМЕРОМ. Все виртуальные таблицы FTS5 создаются без указания tokenize, то есть на unicode61 — стемминга нет ни для русского, ни для английского. Одновременно _sanitize_fts5 в scripts/backend_queries.py вырезает символ звёздочки регуляркой по классу операторов. Итог: префиксный поиск, штатный обходной путь FTS5 для словоформ, недостижим — запрос гейт* превращается в гейт.
AC2. ЗАМЕР ДО ПРАВКИ ЗАФИКСИРОВАН на нашем корпусе, а не на выдуманном: подобраны пары словоформ, реально встречающиеся в памяти и задачах, и записано, что находится по каждой. Без этого нельзя показать, что правка что-то улучшила.
AC3. ВЫБОР МЕЖДУ ТРЕМЯ ПУТЯМИ СДЕЛАН ЯВНО И ОБОСНОВАН, а не взят первый работающий: (а) пропускать звёздочку на конце токена и научить агента приёму гейт*; (б) дописывать префикс автоматически, когда точный запрос дал мало попаданий; (в) сменить токенизатор на trigram. У каждого своя цена: (б) меняет смысл всех существующих запросов, (в) ломает существующий индекс и требует пересборки.
AC4. ЭТО НЕ ПОВОД ВЕРНУТЬ ВЕКТОРА. Задача l26-embeddings-revisit уже закрыта выводом, что embeddings дают меньше ожидаемого. Решение обязано остаться внутри FTS5, либо явно оспорить тот вывод новыми данными.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: звёздочка, пропущенная внутрь FTS5, не должна открывать дорогу синтаксическим ошибкам и инъекции операторов. Тест обязан проверить, что запрос с оператором в середине, с непарной кавычкой и с одной лишь звёздочкой не роняет поиск.
AC6. Приём записан в agent-contract на языке действия: что набирать, когда точный запрос ничего не дал. Знание, которое есть только в коде, следующему агенту не поможет.

## Plan

## Rollback

git revert: санитайзер снова вырезает звёздочку, поведение поиска возвращается к прежнему

## Journal

- 2026-09-24T08:12:43Z [implementation] — AC2 measurement BEFORE (search_all over tasks+memory+decisions, n=500): гейт 486 / гейта 244 / гейтами 13; задача 565 / задачи 665 / задачам 27; проверка 424 / проверки 236 / проверкой 76; сессия 237 / сессии 405 / сессиями 13; решение 466 / решения 198 / решениями 13; калибровка 17 / калибровки 21 / калибровкой 2. Each form finds only itself.
- 2026-09-24T08:15:05Z [implementation] — AC1: ✓ review — FTS tables use unicode61 (no stemming) and backend_queries._sanitize_fts5 stripped '*' in its operator class — root cause in code.
- 2026-09-24T08:15:05Z [implementation] — AC2: ✓ measurement — after: гейта/гейтами 680 (гейт alone stays exact 486), задача/задачи/задачам 900, проверка/проверки/проверкой 634, сессия/сессии/сессиями 588, решение 631 / решения/решениями 623, калибровка/калибровки/калибровкой 42 (was 17/21/2).
- 2026-09-24T08:15:05Z [implementation] — AC3: ✓ review — chosen (a) trailing star kept + Cyrillic ≥5-letter expansion (form OR stem*); rejected (b) prefix-on-few-hits: гейтами had 13 hits and would never expand; rejected (c) trigram: rebuilds every index, not needed. Reasoning in scripts/fts_morphology.py docstring.
- 2026-09-24T08:15:06Z [implementation] — AC4: ✓ review — stays inside FTS5; vectors not reopened.
- 2026-09-24T08:15:06Z [implementation] — AC5: ✓ tests/test_fts_morphology.py::test_only_a_trailing_star_survives_the_sanitizer and tests/test_fts_morphology.py::test_a_hostile_query_does_not_crash_the_search — negative: star in the middle, lone star, unpaired quote, operator; tests/test_fts_morphology.py::test_another_word_form_finds_the_record positive. tests/test_fts5_sanitizer.py::test_paren_star_colon_caret_stripped changed ON PURPOSE (trailing star is now kept; mid-token star still stripped).
- 2026-09-24T08:15:06Z [implementation] — AC6: ✓ review — docs/ru/agent-contract.md 'Поиск по словоформам': what to type when an exact query finds nothing.
