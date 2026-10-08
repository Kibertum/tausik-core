---
slug: claude-md-v-trinadtsati-baytah-ot-potolka-fayl-ne
title: "CLAUDE.md в тринадцати байтах от потолка: файл не принимает нового указателя"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Убрать из CLAUDE.md справочную прозу и дубли указателей, объявить правило допуска строкой в самом файле, обоснование — в claude-md-guide (оба языка). Ни одно жёсткое ограничение не снимается. Заявление SENAR остаётся: его требует test_senar_claim."
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "tests/test_claude_md_size.py"
  - "docs/ru/claude-md-guide.md"
  - "docs/en/claude-md-guide.md"
scope_paths:
  - CLAUDE.md
  - "docs/ru/claude-md-guide.md"
  - "docs/en/claude-md-guide.md"
  - "tests/test_claude_md_size.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T16:23:59Z"
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

У CLAUDE.md есть запас на следующий указатель, и правило, по которому в нём что-то появляется, объявлено. Замер: статическая часть 4083 из 4096 байт до этой уборки — тринадцать байт, то есть один указатель не влезал, и потолок молча превращался в запрет на любое дополнение.

## Acceptance Criteria

1. Замер ДО и ПОСЛЕ: байты статической части, и что именно освободило место. 2. Названо правило, ЧТО имеет право стоять в CLAUDE.md: ограничение, которое агент нарушает по умолчанию, против справочной прозы — второе живёт в docs. 3. Дубли указателей убраны: один адрес называется один раз. 4. НЕГАТИВНЫЙ: сокращение не выбрасывает ни одного жёсткого ограничения — сравнение списка ограничений до и после, он обязан совпасть.

## Plan

## Rollback

git revert — правка текстовая, поведение кода не меняется. Список жёстких ограничений сверяется тестом до и после, поэтому потеря ограничения видна отказом, а не откатом.

## Journal

- 2026-09-28T16:23:34Z [implementation] — AC-1 ЗАМЕР ДО и ПОСЛЕ: статическая часть 4088 из 4096 байт, свободно 8 (в постановке было 13 — за смену файл дорос ещё на пять). ПОСЛЕ: 3842, свободно 254, рост запаса в 32 раза. Освободили: строка стека 110 Б, список типов памяти 62 Б, блок из пяти команд 355 Б, второй адрес контракта 40 Б; добавлена строка правила 240 Б. Итог −246. ✓ tests/test_claude_md_size.py::test_the_cap_leaves_room_for_the_next_pointer (MIN_HEADROOM_BYTES=180 — четыре указателя по 45 Б).
- 2026-09-28T16:23:34Z [implementation] — AC-2 ПРАВИЛО НАЗВАНО: ✓ ::test_the_admission_rule_is_stated_in_the_file_it_governs. Строка стоит в САМОМ CLAUDE.md: ограничение, которое агент нарушает по умолчанию, плюс заявление, которого требует стандарт; справка — в docs, адрес один раз. Обоснование и замер — docs/{ru,en}/claude-md-guide.md, держит ::test_the_guide_carries_the_measurement_that_set_the_rule. Правило унесённое от предмета есть отговорка, которую не перечитывают. AC-3 ДУБЛИ СНЯТЫ: ✓ ::test_no_documentation_address_is_named_twice — agent-contract был дважды (QG-2 и Reference), cli.md дважды (запрет угадывать и хвост блока команд); теперь каждый адрес один раз.
- 2026-09-28T16:23:35Z [implementation] — AC-4 НЕГАТИВНЫЙ: ✓ список выделенных правил совпал — 19 до, 19 после (проверено регуляркой по ^- \*\*…\*\* до правки и после). Ни одно жёсткое ограничение не снято: ушли только строка стека, перечень типов, криба команд и дублирующий адрес. Заявление SENAR оставлено намеренно — его требует tests/test_senar_claim.py в четырёх местах, включая CLAUDE.md, и правило допуска называет это исключением, а не забывает про него. Domain: правило действует на живом файле проекта, который агент грузит каждый ход, а не на образце. Лента: 12094 прошли, 30 пропущены (было 12090), +4 теста.
