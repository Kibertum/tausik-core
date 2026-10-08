---
slug: a-moved-ratchet-is-visible-only-from-the-full-lane
title: "Сдвинутый храповик виден только из пятиминутной ленты"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/ratchet_lane.py"
  - "scripts/project_cli_gates.py"
  - "scripts/project_parser.py"
  - "tests/test_ratchet_lane.py"
scope_paths:
  - "scripts/"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T17:35:38Z"
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

Пятнадцать храповиков в tausik/gates.json проверяются каждый своим тестом, и узнать, сдвинул ли ты один, можно только полной лентой: 12 441 тест, пять минут, плюс вызов на разбор. Замер смены #278: храповики краснели на моей же работе около десяти раз за смену. При этом ровно те же проверки — 22 файла, 459 тестов — идут 21 секунду. Цель: одна команда гоняет только их, а набор файлов ВЫВОДИТСЯ из дерева, а не перечисляется.

## Acceptance Criteria

AC-1 tausik gates ratchets гоняет ровно те файлы тестов, которые читают tausik/gates.json, и отдаёт ненулевой код, если хоть один упал. ✓ tests/test_ratchet_lane.py
AC-2 Набор ВЫВОДИТСЯ из дерева, а не перечисляется: новый тест храповика подхватывается без правки кода. Тест сажает такой файл во временное дерево и требует, чтобы он попал в набор.
AC-3 НЕГАТИВНЫЙ: набор оказался пустым — команда отказывает с ОТСУТСТВИЕМ и причиной, а не рапортует «всё зелено» (решение #334).
AC-4 НЕГАТИВНЫЙ: файл, который лишь УПОМИНАЕТ gates.json в прозе комментария, но ничего из него не читает, в набор не попадает — иначе лента расползётся обратно.
AC-5 Вывод прямо говорит, что это НЕ полная лента, и называет, сколько файлов взято.
AC-6 Полная лента зелёная.

## Plan

## Rollback

git revert; полная лента остаётся единственным путём, как и была

## Journal

- 2026-09-29T17:35:34Z [implementation] — AC-1 ✓ tausik gates ratchets гоняет 25 файлов, 549 тестов за 21-24 секунды и отдаёт код pytest; ✓ tests/test_ratchet_lane.py::TestTheRunSaysWhatItIsAndIsNot::test_it_passes_pytest_the_derived_files_and_returns_its_code. AC-2 ✓ набор ВЫВОДИТСЯ: ::TestTheSetIsDerivedFromTheTree — подложенный новый файл храповика подхватывается без правки кода, и отдельно проверено, что файл, достающий базу ЧЕРЕЗ ИМПОРТ, тоже входит (три формы импорта). AC-3 ✓ НЕГАТИВНЫЙ: пустой набор — NoRatchetTests с причиной и словами про отсутствие зелёного; отдельно дерево без каталога tests. AC-4 ✓ НЕГАТИВНЫЙ: файл, лишь упоминающий базу в комментарии, не входит; модуль, который базу не читает, не втягивает своих импортёров; не-тестовые имена файлов отсеиваются. AC-5 ✓ вывод говорит «NOT the full lane» и называет число файлов. AC-6 ✓ полная лента 12 457 passed, 34 skipped, 0 deselected. Плюс ::TestTheLiveTreeIsCovered сверяет набор с ключами базы напрямую — ни один из 14 храповиков не остаётся вне быстрой ленты. Domain: пять минут и вызов на разбор превращаются в 21 секунду; проверено на себе в ту же смену — отказ test_crosscutting_registry, найденный полной лентой за 4 минуты, входит в быстрый набор. НАЙДЕНО В ХОДЕ РАБОТЫ: первая редакция выводила набор только по имени файла в строке и ПОТЕРЯЛА test_gate_ruff_format.py, который читает базу через gate_ruff_format.legacy_unformatted() — ровно тот храповик, что краснел тем же утром. Добавлен второй путь, через импорт.
