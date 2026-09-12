---
slug: response-contract-sets-a-shape-not-only-a-length
title: "Контракт ответа задаёт ФОРМУ, а не только краткость: сейчас у агента нет обязательной структуры"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: null
role: architect
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: "Расширить CAVEMAN_DIRECTIVE до контракта формы (порядок частей, несжимаемые типы, ситуационные исключения списком, pre-send чек); паритет с /i-have-adhd закреплён тестом; docs; CHANGELOG."
scope_exclude: "Не вводить второй режим рядом с caveman, не менять доставку директивы (это output-discipline-reaches-the-agent-once), не мерить послушание (это adherence-задача), не релизить."
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - "harness/skills/i-have-adhd/SKILL.md"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_response_contract_shape.py"
  - "tests/test_rules_generator_warning_parity.py"
scope_paths:
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "bootstrap/bootstrap_templates.py"
  - "harness/skills/i-have-adhd/SKILL.md"
  - "tests/test_caveman_output_mode.py"
  - "tests/test_response_contract_shape.py"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/response-contract-sets-a-shape-not-only-a-length.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T16:01:49Z"
---

## Goal

Всё, что TAUSIK принуждает делать, касается ДЕЙСТВИЙ: гейты, область записи, критерии приёмки. О ФОРМЕ ответа не сказано ничего. Единственный существующий рычаг — output_mode: caveman — задаёт только краткость («terse, telegraphic prose») и ничего не говорит о структуре: какие разделы обязаны быть в ответе, где стоит вывод, где основание, где остаток работы. Следствие видно на живых сессиях: агент выдаёт пространное рассуждение вместо разложенного по местам ответа, и читателю приходится извлекать факты из прозы. Задача: ввести контракт формы ответа — обязательные части и их порядок (что сделано / чем проверено / что осталось / что решает пользователь), с явным исключением для того, что уже защищено в caveman как некомпрессируемое (код, вывод инструментов, пути, ошибки, доказательства критериев, решения, журналы, передачи смены). Контракт обязан быть коротким сам: он впрыскивается каждую сессию и его длина есть его же цена. Не выдумывать новый режим рядом с caveman — расширить существующий или заменить его, но не оставить два рычага об одном.  ДОПОЛНЕНО В СЕССИИ #185 ИЗ ЧУЖОГО ИСТОЧНИКА, github.com/ayghri/i-have-adhd (MIT), принесён владельцем. Из десяти его правил новыми для нас оказались ровно две вещи, и обе — про то, как правило ВЫЖИВАЕТ, а не про то, как оно звучит:  1) ИСКЛЮЧЕНИЯ НАЗВАНЫ СПИСКОМ, А НЕ ОСТАВЛЕНЫ НА УСМОТРЕНИЕ. У него контракт явно отменяется в пяти случаях: запрошено объяснение; действие разрушительно и требует подтверждения; идёт спираль отладки; налицо настоящая двусмысленность; соблюдение правила удалило бы сам ответ. Наш caveman перечисляет несжимаемые ТИПЫ СОДЕРЖИМОГО, но не ситуации. Правило без названных исключений нарушается молча и по одному, после чего перестаёт значить что-либо — это тот же механизм, что и вырожденный контроль из памяти #404.  2) ПРОВЕРКА ПЕРЕД ОТПРАВКОЙ КАК ЧАСТЬ КОНТРАКТА. Короткий чек-лист, применяемый к уже написанному ответу: снять объявление намерения («сейчас я...»), снять закрывающий пересказ, снять боковые ветки, снять хеджирование, не несущее информации. Это ровно то, чем контракт формы отличается от пожелания краткости: у него есть шаг, на котором он применяется.  Оба пункта закрываются ЗДЕСЬ, отдельными задачами не заводятся — иначе выйдет добавление к бэклогу без основания (решение #244 требует очерёдности, а не добавления). Замер послушания контракту вынесен в response-contract-adherence-is-never-measured, доставка директивы — в output-discipline-reaches-the-agent-once-not-every-turn.

## Acceptance Criteria

AC-1: the existing lever (output_mode caveman, CAVEMAN_DIRECTIVE) becomes the response contract — it names the SHAPE (done → verified by → left → your call, in that order, empty parts omitted), keeps the byte-exact and full-prose lists, and adds nothing beside it: no second mode, no new config key. AC-2: the situational EXCEPTIONS are a named list inside the directive — explanation requested; destructive action needing confirmation; three failed debugging turns; genuine ambiguity; the rule would delete the answer — so a violation is a named exception or a violation, never silent judgement. AC-3: the PRE-SEND check is part of the directive: delete intent announcements, closing recaps, side branches and empty hedges, then check that the first and last lines carry the next action and the current state. AC-4 (negative): the directive stays ≤ CAVEMAN_DIRECTIVE_MAX_CHARS after the ceiling is moved by the measured amount and no more (test_ceiling_is_actually_enforced_not_vacuous keeps its < 2000 bound); the eight existing caveman tests stay green; the byte-exact and full-prose protections are unchanged. AC-5 (parity): tests/test_response_contract_shape.py asserts that the directive and harness/skills/i-have-adhd/SKILL.md name the same four shape parts, the same five exceptions and the same pre-send deletions — one contract, two delivery paths (config or slash) — and fails if either drifts. AC-6: docs/{en,ru}/quickstart.md (the page that documents output_mode) and configuration.md describe the contract; CHANGELOG EN/RU; ruff, signed verify.

## Plan

[{"step": "\u0414\u0438\u0440\u0435\u043a\u0442\u0438\u0432\u0430: \u0444\u043e\u0440\u043c\u0430 + \u0438\u0441\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f + pre-send \u0432 CAVEMAN_DIRECTIVE, \u043f\u043e\u0442\u043e\u043b\u043e\u043a \u043f\u043e \u0437\u0430\u043c\u0435\u0440\u0443", "done": true}, {"step": "\u041f\u0430\u0440\u0438\u0442\u0435\u0442 \u0441\u043e SKILL.md: \u0442\u0435\u0441\u0442 \u043d\u0430 4 \u0447\u0430\u0441\u0442\u0438, 5 \u0438\u0441\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0439, pre-send", "done": true}, {"step": "Docs, CHANGELOG, verify", "done": true}]

## Rollback

git revert; директива возвращается к чистой краткости.

## Journal

- 2026-09-12T15:59:34Z [implementation] — Step 1: CAVEMAN_DIRECTIVE now carries SHAPE (done → verified by → left → your call), five named EXCEPTIONS and PRE-SEND, inside the one marker; keep-lists untouched. Measured 888 chars (was ≤700); ceiling moved to 888 exactly, comment records the measurement. Agent-contract cost row 175 tok/0.06% → 222 tok/0.08%, ~25x.
- 2026-09-12T15:59:34Z [implementation] — Step 2: SKILL.md gained a ## Shape section naming the same four parts in order; tests/test_response_contract_shape.py (18 tests) pins 4 parts, order, 5 exceptions (count by semicolons), 4 pre-send deletions, first/last-line frame, one lever (OUTPUT_MODE_VALUES == {off, caveman}), no-headroom ceiling, keep-lists, two negatives. test_rules_generator_warning_parity cap pin 700 → 888 with the reason.
- 2026-09-12T15:59:35Z [implementation] — Step 3: quickstart EN/RU paragraph extended, CHANGELOG EN/RU Changed entry, profiles redeployed (--check clean); ruff clean; 59 caveman/parity/warning tests + 66 doc guards green. Full lane after 85e8af15: 10012 passed, 1 external red (renar corpus v1.1, owner task).
- 2026-09-12T16:00:22Z [implementation] — AC-1 ✓ tests/test_response_contract_shape.py::test_the_contract_rides_the_existing_directive_not_a_second_mode, ::test_the_keep_lists_survived_the_rewrite — shape in CAVEMAN_DIRECTIVE under the one marker, keep-lists intact, OUTPUT_MODE_VALUES still {off, caveman}. AC-2 ✓ tests/test_response_contract_shape.py::test_exactly_five_exceptions_in_the_directive, ::test_both_name_the_exception[5 params]. AC-3 ✓ tests/test_response_contract_shape.py::test_both_name_the_pre_send_deletion[4 params], ::test_both_frame_the_answer_with_action_and_state[2 params]. AC-4 ✓ tests/test_response_contract_shape.py::test_the_ceiling_moved_by_the_measured_amount_only (888 == len), tests/test_caveman_output_mode.py 8 tests green, ::test_ceiling_is_actually_enforced_not_vacuous (< 2000). AC-5 ✓ tests/test_response_contract_shape.py::test_both_name_the_shape_part[4 params], ::test_the_shape_keeps_its_order_in_both, ::test_a_skill_without_the_shape_section_is_caught, ::test_the_directive_names_no_exception_the_skill_lacks. AC-6 ✓ docs/en/quickstart.md:198, docs/ru/quickstart.md:197, docs/ru/agent-contract.md cost rows, CHANGELOG.md + CHANGELOG.ru.md Changed entry; ruff clean; verify run #2521 signed.
- 2026-09-12T16:01:10Z [implementation] — Root cause (test-shape): four parametrized parity tests shared one AST shape; dedupe gate grew 290→292 groups. Collapsed into one table-driven test over NAMED_TERMS (family:name ids, 15 rows); file now 22 tests, dedupe report has no group from it.
- 2026-09-12T16:01:58Z [done] — Correction to the AC line: after the dedupe collapse the four look-alike tests are one. AC-2 ✓ tests/test_response_contract_shape.py::test_both_documents_carry_the_named_term[exception:*] (5 ids). AC-3 ✓ ::test_both_documents_carry_the_named_term[pre-send:*] (4 ids) and [frame:*] (2 ids). AC-5 ✓ ::test_both_documents_carry_the_named_term[shape:*] (4 ids), ::test_the_shape_keeps_its_order_in_both. Domain: an agent under output_mode caveman receives one ## Output economy block of 888 chars in its rules file whose four-part shape matches what /i-have-adhd tells the same agent in prose — one contract, two entry points, both live in the deployed profiles (bootstrap --check clean).
