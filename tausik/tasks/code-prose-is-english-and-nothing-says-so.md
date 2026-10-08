---
slug: code-prose-is-english-and-nothing-says-so
title: "Правила «код и комментарии по-английски» нет нигде, а шаблон разрешает обратное"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/prose_language.py"
  - "tests/test_prose_language.py"
  - "bootstrap/bootstrap_templates.py"
  - CLAUDE.md
  - "tests/test_generated_rules_code_style.py"
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "scripts/prose_language.py"
  - "tests/test_prose_language.py"
  - "tests/test_instruction_tone.py"
  - "tests/test_generated_rules_code_style.py"
  - "tausik/gates.json"
  - CLAUDE.md
  - "docs/ru/agent-contract.md"
  - "docs/en/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T12:46:03Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

Правило «код и комментарии на английском» (решение #404, указание владельца) стоит в поставляемых инструкциях и в CLAUDE.md, а остаток замерен и ратчетится. Сегодня шаблон CODE_STYLE утверждает ОБРАТНОЕ: «Docstrings, comments and test descriptions take any language».

## Acceptance Criteria

1. Шаблон CODE_STYLE говорит «по-английски» вместо «на любом языке»; правило уезжает в порождаемые инструкции. 2. Строка в CLAUDE.md этого проекта; храповик запаса не нарушен. 3. Остаток замерен и записан в gates.json: 5348 строк прозы в 287 файлах, отдельно 269 кириллических идентификаторов; оба только вниз. 4. НЕГАТИВНЫЙ: идентификаторы в tests НЕ переименовываются — конвенция #745 объявила цену (83 цитаты доказательств в 21 задаче), и правило про прозу её не отменяет; тест закрепляет, что исключение осталось. 5. НЕГАТИВНЫЙ: массового перевода 5348 строк в этой задаче НЕТ — правка без задачи ровно того размера, который проект запрещает; храповик разрешает уменьшение, но не требует его сейчас. 6. Полная лента зелёная.

## Plan

## Rollback

git revert; добавляется правило и читающий храповик. Массового перевода нет, поэтому откат не трогает ни одной строки существующего кода.

## Journal

- 2026-09-29T12:44:38Z [implementation] — AC-1: ✓ шаблон CODE_STYLE говорит «Code is written in English — identifiers AND prose», формулировка «any language» удалена; tests/test_prose_language.py::TestTheShippedRuleSaysIt и tests/test_generated_rules_code_style.py (42 теста перенаправлены на новую формулировку). AC-2: ✓ строка в CLAUDE.md, запас 223 байта при пороге 180. Заплачено обменом двух строк, каждая из которых повторяла механизм: task done ОТКАЗЫВАЕТ в закрытии с красным verify без dead end и печатает команду, а счётчик чекпоинта печатается в ответе инструмента при переходе порога. AC-3: ✓ база в gates.json: prose_lines 5348, files 287, identifiers 269, оба только вниз.
- 2026-09-29T12:44:54Z [implementation] — AC-4 НЕГАТИВНЫЙ: ✓ ::TestTheExemptionSurvivesAndIsPriced — 269 идентификаторов остаются, причина в gates.json называет ЦЕНУ (83 цитаты доказательств в 21 задаче, журнал append-only), а не предпочтение; счёт ведётся раздельно, чтобы исключение не переползло в число прозы. AC-5 НЕГАТИВНЫЙ: ✓ массового перевода нет — git diff не трогает ни одной из 5348 строк; храповик разрешает уменьшение и запрещает рост. AC-6: ✓ полная лента 12279 прошли, 34 пропущены. Domain: правило проверено на ПОРОЖДЁННОМ файле правил, а не на константе, и на живом дереве — 5348/287/269 совпадает с базой. Граница держится тестом: ответ пользователю остаётся на его языке.
- 2026-09-29T12:44:54Z [implementation] — ДВА САМОСЧЁТА ПОЙМАНЫ СВОИМИ ЖЕ ПРОВЕРКАМИ: (1) ruff format свернул экранированный диапазон в литеральные символы, и детектор посчитал строку собственного шаблона — теперь диапазон строится через chr(); (2) тест, проверяющий правило в CLAUDE.md, написал искомое слово кириллицей и добавил строку к числу, которое охраняет — игла тоже строится через chr(). Обе поймал храповик на следующем прогоне, не ревью.
