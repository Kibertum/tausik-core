---
slug: documentation-parity-three-features-shipped-this-r
title: "documentation parity: three features shipped this release exist in one language only"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/receipts.md"
  - "docs/ru/model-providers.md"
  - "docs/en/sessions.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/ru/graph.md"
  - "docs/en/graph.md"
  - "docs/en/cli.md"
  - "tests/test_audit_translation_drift.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "docs/en/receipts.md"
  - "docs/ru/model-providers.md"
  - "docs/en/sessions.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/ru/graph.md"
  - "docs/en/graph.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "tests/test_audit_translation_drift.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T20:54:02Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ЛИНЗОЙ tausik coherence при проверке готовности 1.9: шесть пар документов разошлись. Разбор по заголовкам со снятыми блоками кода даёт пять НАСТОЯЩИХ расхождений, и три из них про то, что выпускает ЭТОТ релиз.

1) docs/{en,ru}/receipts.md — В АНГЛИЙСКОЙ ВЕРСИИ НЕТ ТРЁХ РАЗДЕЛОВ, которые есть в русской: «Что чек говорит о себе (схема v3)», «Хендл прогона — предъявление вместо поиска» и «Проверка при предъявлении — fail-closed». Это механика v3, выпускаемая в 1.9. Англоязычный читатель о ней не узнает.
2) docs/{en,ru}/model-providers.md — в русской НЕТ раздела «Cost telemetry for non-Claude models». Стоимостная телеметрия — предмет этого релиза (схема v58, колонки токенов и стоимости).
3) docs/{en,ru}/sessions.md — в английской НЕТ раздела про то, что usage-телеметрия выбыла из списка выключающегося без сессии (схема v48).
4) docs/{en,ru}/enforcement-coverage.md — у русской версии ВООБЩЕ НЕТ заголовка первого уровня, и уровни заголовков разъехались с английской.
5) docs/{en,ru}/graph.md — в русской нет раздела «Как это стоит рядом с детекторами дрейфа RENAR». Документ создан в этом релизе мной.

ПОПУТНО, И ЭТО ОШИБКА РЕНДЕРА: docs/en/graph.md:330 — строка прозы начинается с '#663):' и markdown отрисует её ЗАГОЛОВКОМ посреди абзаца.

ЧТО НЕ ВХОДИТ: не выравнивать cli.md (расхождение там — комментарии внутри блоков кода, то есть артефакт счётчика, а не текста).

## Acceptance Criteria

AC-1. Три раздела про механику v3 (самоописание чека, хендл прогона, проверка при предъявлении) появляются в английской версии receipts.md — переводом того, что уже сказано по-русски, а не новым текстом.
AC-2. Раздел о стоимостной телеметрии появляется в русской model-providers.md; раздел о выбывшей usage-телеметрии — в английской sessions.md.
AC-3. У русской enforcement-coverage.md появляется заголовок первого уровня, уровни заголовков совпадают с английской.
AC-4. В русской graph.md появляется раздел про соседство с детекторами дрейфа RENAR.
AC-5. Строка docs/en/graph.md:330 перестаёт начинаться с '#', то есть перестаёт рендериться заголовком.
AC-6. НЕГАТИВНЫЙ СЦЕНАРИЙ И ПРОВЕРКА: audit_translation_drift на этих пяти парах даёт НОЛЬ расхождений. Проверено прогоном детектора, а не чтением. cli.md остаётся в списке и это объявлено, а не замолчано.

## Plan

## Rollback

## Journal

- 2026-09-08T20:53:58Z [implementation] — AC verified: AC-1: ✓ три раздела про механику v3 переведены в docs/en/receipts.md: 'What the receipt says about itself (schema v3)', 'The run handle — presenting instead of searching', 'Verification on presentation — fail-closed', плюс абзацы про совместимость, про то, чего хендл НЕ даёт, и SQL-запрос аудита непогашенных хендлов. Перевод существующего русского текста, а не новый текст. AC-2: ✓ стоимостная телеметрия переведена в docs/ru/model-providers.md; выбывшая usage-телеметрия (схема v48) — в docs/en/sessions.md. AC-3: ✓ у docs/ru/enforcement-coverage.md появился заголовок первого уровня. ПРИЧИНА ОКАЗАЛАСЬ НЕ В ТЕКСТЕ: файл начинался с BOM, поэтому строка '# Граница принуждения...' не начиналась с '#' и заголовком не считалась ни детектором, ни markdown. BOM снят здесь и везде, где встречался под docs/. AC-4: ✓ раздел про соседство с детекторами дрейфа RENAR добавлен в docs/ru/graph.md. AC-5: ✓ строка docs/en/graph.md перестала начинаться с '#663):' — перенос сдвинут, абзац больше не рендерится с заголовком посередине. AC-6: ✓ ПРОВЕРЕНО ПРОГОНОМ ДЕТЕКТОРА: audit_translation_drift даёт НОЛЬ расхождений. Было шесть пар. ПОСТАНОВКА ЗАДАЧИ ОШИБЛАСЬ, И ЗАМЕР ЕЁ ОПРОВЕРГ. Я написал, что дрейф cli.md — артефакт счётчика от комментариев внутри блоков кода, и вывел его из объёма. Позиционная сверка заголовков показала другое: в русской версии есть раздел 'Вычеркивание из памяти (v1.9, решение #258)', а в английской его нет вовсе. Это команда redact, выпускаемая в 1.9. Раздел переведён, cli.md вошёл в объём. Negative: заведён ратчет НА ЖИВОМ ДЕРЕВЕ — tests/test_audit_translation_drift.py::TestЖивоеДеревоНеРасходится. Существующие тесты проверяли ДЕТЕКТОР на фикстурах и были зелены всё то время, пока шесть настоящих пар расходились: детектор просто никто не спрашивал. Второй тест закрепляет три непарных документа ПОИМЁННО, чтобы новый непарный объявлял о себе, а не растворялся в счётчике. Третий требует, чтобы сравнивалось больше 20 пар — ноль расхождений при нуле сравнений был бы самым тихим способом обессмыслить первый. Domain: проверено вне тестов чтением. Англоязычный читатель receipts.md теперь узнаёт про хендл прогона и про то, что чек v1/v2 предъявить нельзя; русскоязычный читатель model-providers.md — что неизвестная цена не равна нулю. Ни один из этих фактов до правки на своём языке не существовал.
- 2026-09-08T20:54:15Z [done] — AC-6 (что именно проверено): ✓ tests/test_audit_translation_drift.py::TestЖивоеДеревоНеРасходится::test_ни_одна_пара_не_разошлась ✓ tests/test_audit_translation_drift.py::TestЖивоеДеревоНеРасходится::test_список_непарных_документов_закреплён ✓ tests/test_audit_translation_drift.py::TestЖивоеДеревоНеРасходится::test_проверка_действительно_смотрит_на_пары ✓ verification_run #2340 зелёный (ruff PASS, pytest PASS)
