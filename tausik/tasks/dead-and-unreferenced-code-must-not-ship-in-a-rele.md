---
slug: dead-and-unreferenced-code-must-not-ship-in-a-rele
title: "dead and unreferenced code must not ship in a release about honesty"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_bypass_record.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - "tests/test_direct_edit_bypass_record.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "scripts/gate_bypass_record.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - "tests/test_direct_edit_bypass_record.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T20:45:50Z"
---

## Goal

НАЙДЕНО ЛИНЗОЙ tausik coherence при проверке готовности 1.9. Две находки уровня HIGH и MEDIUM, обе одного класса: код, который есть, но которого никто не зовёт.

1) scripts/gate_bypass_record.py:133 record_direct_edit — МЁРТВЫЙ ДУБЛИКАТ. Функция зовёт build() и emit_supervision_bypass(); её не вызывает никто: ни продуктовый код, ни тесты, ни MCP. Живой путь существует и делает то же самое — project_cli_events.py:83,102 сам зовёт build() и emit_supervision_bypass(). Это три строки в двух местах, из которых работает одно. Заведено на 1.10 задачей record-direct-edit-is-a-dead-duplicate-of-the-live-path, но выпускать релиз про честность с мёртвой функцией внутри гейта надзора нельзя.

2) scripts/rag_retrieval_bench.py — НА НЕГО НИЧТО НЕ ССЫЛАЕТСЯ. Это НЕ мёртвый код: инструмент настоящий и произвёл числа, которыми хвалится changelog (recall@3 context 0.4870 -> 0.8348). Он законный ENTRYPOINT — route_map прямо говорит, что модуль, который сам по себе запускается, это не нарушение. Но в docs/ru и docs/en его нет ни разу, то есть найти его может только тот, кто уже знает, что он есть. Инструмент, о котором не сказано, — инструмент, которым не пользуются: это тот же класс, что 'граф построен и имеет ноль строк'.

ГРАНИЦА: не переписывать сам бенчмарк и не менять его выдачу — предмет только достижимость.

## Acceptance Criteria

AC-1. record_direct_edit УДАЛЕНА, а не помечена. Проверено, что после удаления живой путь записи обхода работает: тест на emit_supervision_bypass через project_cli_events зелёный.
AC-2. НЕГАТИВНЫЙ СЦЕНАРИЙ для AC-1: удаление не смеет ослабить запись обхода. Тест требует, чтобы обход через живой путь ПО-ПРЕЖНЕМУ записывался, и краснеет, если запись пропала. Удалить функцию и потерять механизм — худший исход этой задачи.
AC-3. rag_retrieval_bench назван в документации там, где его ищет читатель, с одной строкой о том, что он меряет и как запускается. Проверяется тестом на присутствие, а не намерением.
AC-4. Линза перестаёт сообщать обе находки: audit_unused_python даёт ноль, audit_orphan_files даёт ноль. Проверено прогоном линзы, а не рассуждением.
AC-5. Полный прогон зелёный, ruff и mypy чисто.

## Plan

## Rollback

## Journal

- 2026-09-08T20:45:47Z [implementation] — AC verified: AC-1: ✓ record_direct_edit удалена из scripts/gate_bypass_record.py целиком, а не помечена. Модуль грузится, публичная поверхность на месте (build, completeness, decode, encode, missing_fields, split_nested, BypassRecordRefused). AC-2: ✓ tests/test_direct_edit_bypass_record.py::TestУдалениеДубликатаНеУнеслоМеханизм::test_живой_путь_записывает_обход — проверяется ЖИВОЙ путь целиком: build() плюс emit_supervision_bypass() пишут файл. Отсутствие удалённого имени проверяется ОТДЕЛЬНО и только как предпосылка: само по себе оно тривиально верно и ничего не говорит о работоспособности записи. Третий тест требует, чтобы вторая копия не завелась снова. AC-3: ✓ rag_retrieval_bench описан в docs/{ru,en}/architecture.md рядом с разделом о контекстных заголовках чанков — там, где читатель уже читает про то, ЧТО он меряет. Названы команда запуска, что именно меряется (recall@K по конкретному чанку), почему набор нельзя подогнать (запросы выводятся механически, выборка детерминированная) и оба набора запросов с числами. AC-4: ✓ ПРОВЕРЕНО ПРОГОНОМ, а не рассуждением: audit_unused_python.collect_unused даёт 0, audit_orphan_files.collect_orphans даёт 0. До правки было 1 и 1. AC-5: ✓ verification_run #2336 зелёный, ruff чисто, 214 тестов вокруг обхода и надзора зелёные. Negative: тест на живой путь краснеет, если запись обхода перестанет работать — то есть ловит худший исход этой задачи, когда вместе с дубликатом уносят механизм. Отдельный тест краснеет, если gate_bypass_record снова начнёт звать эмиттер сам. Domain: проверено вне тестов. Мёртвая функция была ВТОРОЙ реализацией трёх строк, живой путь в project_cli_events.py:83,102 зовёт build() и emit_supervision_bypass() сам. Инструмент rag_retrieval_bench не выдуман: числа, которые он произвёл, уже цитируются в CHANGELOG, а найти его до этой правки можно было только зная о нём заранее.
