---
slug: dev-doc-checks-describes-a-machine-that-changed
title: "Документ про доковые проверки описывает состояние полугодовой давности, а таблица модулей не знает пяти модулей"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/doc_drift_fixes.py"
  - "scripts/doc_drift_tables.py"
  - "tests/test_doc_drift_fixes_repair_what_they_detect.py"
  - "docs/en/dev-doc-checks.md"
  - "docs/ru/dev-doc-checks.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/dev-doc-checks.md"
  - "docs/ru/dev-doc-checks.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "scripts/doc_drift_fixes.py"
  - "scripts/doc_drift_tables.py"
  - "scripts/doc_drift_common.py"
  - "tests/test_doc_drift_fixes_repair_what_they_detect.py"
  - "tests/test_doc_drift_scanners.py"
  - "tests/test_gen_doc_constants.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T16:01:15Z"
resolution: null
resolution_reason: null
---

## Goal

Найдено ревью #41/#42 в смене #224, вынесено из задачи review-fail-4896bbf-unbound-subjects-and-untracked-constant как предсуществующий пробел, не относящийся к её предмету.

ДОКУМЕНТ, КОТОРЫЙ ЧИТАЕТ НОВЫЙ УЧАСТНИК, ЧТОБЫ УЗНАТЬ «ЧТО ГОНЯЕТ CI ПО ДОКУМЕНТАМ», отстал от машинерии: docs/{en,ru}/dev-doc-checks.md правился 2026-07-20 и до сих пор описывает gen_doc_constants.py --check как проверку «версии из pyproject.toml или счётчиков MCP-инструментов». За это время появились: счётчики repo-state (хуки, стеки, роли, агенты ревью, core-скиллы, official-скиллы), сверка закрытых перечней стандарта, столбцовый скан таблиц с реестром субъектов, перечень исключений с причинами и перечень «не проверяется никем». Ничего из этого в документе нет.

ТАБЛИЦА МОДУЛЕЙ в docs/{en,ru}/architecture.md называет только gen_doc_constants.py и mcp_tool_counts.py. Отсутствуют doc_drift_common.py, doc_drift_scanners.py, doc_drift_fixes.py, doc_drift_tables.py и code_counts.py — пять модулей, из них один заведён в смене #224.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: обе задачи смены #224 были про то, что утверждение продукта о себе должно быть привязано к тому, что его исполняет. Документ, описывающий САМ механизм привязки, — первое место, куда посмотрит тот, кто будет его чинить или расширять, и он описывает состояние полугодовой давности. Это тот же класс, только про документацию инструмента, а не про счётчики.

ПРЕДМЕТ: привести оба документа в соответствие и решить, нужна ли охрана от повторного отставания (например, требовать упоминания каждого scan_* из __all__ в dev-doc-checks.md — по образцу теста, требующего живого совпадения для каждого шаблона). Второе — предмет обсуждения, не данность: охрана документации по списку имён легко вырождается в разметку ради разметки.

## Acceptance Criteria

ЗАМЕР ДО РАБОТЫ (смена #236): docs/{en,ru}/dev-doc-checks.md — по 73 строки, и во всём файле назван РОВНО ОДИН модуль механизма, gen_doc_constants.py. Реально их семь: doc_drift_common, doc_drift_scanners, doc_drift_fixes, doc_drift_tables, code_counts, mcp_tool_counts и сам gen_doc_constants. Таблица модулей в docs/{en,ru}/architecture.md называет два из семи. Сканеров в doc_drift_scanners шесть (scan_version_refs, scan_py_version_constants, scan_mcp_tool_counts, scan_closed_list_enums, scan_test_counts, scan_code_counts) плюс scan_table_count_columns в doc_drift_tables — семь, и ни один не назван в документе.

AC1. ДОКУМЕНТ ОПИСЫВАЕТ НЫНЕШНЮЮ МАШИНУ. dev-doc-checks.md на обоих языках называет все семь проверок и говорит, что каждая ловит. Не список имён ради списка: у каждой сказано, какое утверждение она стережёт и от какого дрейфа.

AC2. ТАБЛИЦА МОДУЛЕЙ В architecture.md ПОЛНА на обоих языках: семь модулей вместо двух, с одной строкой назначения у каждого.

AC3. ПОЧИНЩИК ЗАКРЫВАЕТ ФОРМУ, КОТОРУЮ САМ ЖЕ НАХОДИТ. _MCP_COUNT_PAIR_PATTERN («N project + M brain») импортируется ТОЛЬКО сканером; doc_drift_fixes его не знает. Из-за этого gen_doc_constants.py --write чинит часть файлов и выходит красным со словами «drift remains after --write». Замер: при подъёме числа инструментов со 145 до 146 в смене #234 таких ссылок пришлось править РУКАМИ восемь в семи файлах. После правки --write чинит и их.

AC4. ПОЧИНКА ПАРЫ ПРАВИТ ОБЕ ЧАСТИ И НИ ОДНОЙ ЛИШНЕЙ. У шаблона ДВЕ группы, и существующий _fix_counts заменяет только первую. Тест подаёт «(145 project + 7 brain)» при ожидаемых 146 и 7 и требует «(146 project + 7 brain)»: вторая часть не тронута, потому что она уже верна.

AC5. НЕГАТИВНАЯ ПОЛОВИНА. Починка не заходит внутрь огороженных блоков кода и внутрь динамической секции CLAUDE.md — там же, где не ходит сканер. Тест подаёт пару внутри ``` и требует, чтобы она осталась нетронутой.

AC6. СВЯЗЬ ПРОВЕРЯЕТСЯ МАШИНОЙ, А НЕ ОБЕЩАНИЕМ. Тест утверждает: каждое семейство шаблонов, которое СКАНЕР умеет находить, имеет починщика. Детектор без починщика заставляет делать руками ровно то, ради автоматизации чего он заведён, и даёт ложное чувство охвата.

AC7. САМООПИСАНИЕ МОДУЛЯ ИСПРАВЛЕНО. Докстринг doc_drift_tables.py открывается словами «Third module of the doc-drift split» и перечисляет три модуля, тогда как раскол четырёхмодульный. Соседний doc_drift_scanners уже исправлен на «four-module split», этот недосчитан.

AC8. ГЕЙТ ПОКРЫТИЯ НЕ ОБХОДИТСЯ. Правка не ослабляет doc_coverage и не добавляет исключений; полный прогон остаётся зелёным.

## Plan

## Rollback

git revert. Правка состоит из документации и одного дополнения к починщику доковых констант; поведение сканера не меняется, поэтому откат возвращает лишь ручную починку парной формы.

## Journal

- 2026-09-07T09:42:48Z [planning] — ЕЩЁ ОДНА МЕЛОЧЬ ТОГО ЖЕ КЛАССА, НАЙДЕНА ПРИ ФИНАЛЬНОЙ ВЫЧИТКЕ СМЕНЫ #224 И ОСОЗНАННО НЕ ПОЧИНЕНА ЗДЕСЬ ЖЕ: докстринг scripts/doc_drift_tables.py открывается словами «Third module of the doc-drift split» и перечисляет три модуля, тогда как раскол уже четырёхмодульный (common, scanners, fixes, tables) — соседний докстринг doc_drift_scanners в той же смене исправлен на «four-module split», а этот недосчитан. Правка на одно слово, но она требует активной задачи (SENAR Rule 1), а капасити смены #224 был исчерпан (222/200). Взять сюда: это ровно предмет данной задачи — самоописание, отставшее от машины.
- 2026-09-08T13:18:27Z [planning] — ПРЕДМЕТ ДОБАВЛЕН ИЗ СМЕНЫ #234, с числом. Сканер доковых констант НАХОДИТ дрейф ссылок вида «145 project + 7 brain», но починить их не умеет: gen_doc_constants.py --write чинит часть файлов и заканчивает словами «drift remains after --write; a ref is outside the known patterns. Fix it by hand or widen the scanner». При поднятии числа инструментов MCP со 145 до 146 руками правились ВОСЕМЬ таких ссылок в семи файлах (AGENTS.md дважды, docs/ru/architecture.md, docs/en/mcp.md, docs/ru/mcp.md, docs/ru/agent-contract.md, обе senar-compliance-matrix.md), плюс два README и три ячейки таблицы в AGENTS.md, плюс колонка IDE-таблицы в обоих README. Итого около пятнадцати ручных правок на одно изменение одного числа. Это ровно тот класс, о котором задача: механизм привязки утверждения к исполнителю сам отстаёт от машины. Предложение в предмет задачи: расширить doc_drift_fixes до ПОЛНОГО покрытия тех форм, которые сканер уже умеет НАХОДИТЬ — детектор без починщика заставляет делать руками то, ради автоматизации чего он и заведён, и при этом даёт ложное чувство, что дрейф охвачен.
- 2026-09-08T16:00:35Z [implementation] — AC-1: ✓ docs/{en,ru}/dev-doc-checks.md получили раздел, называющий все СЕМЬ сканов с тем, что каждый стережёт: scan_version_refs, scan_py_version_constants, scan_mcp_tool_counts, scan_closed_list_enums, scan_test_counts, scan_code_counts, scan_table_count_columns. Было названо ноль сканов и один модуль из семи. AC-2: ✓ таблица модулей в docs/{en,ru}/architecture.md выросла с двух строк до семи: добавлены doc_drift_common, doc_drift_scanners, doc_drift_tables, doc_drift_fixes, code_counts; gen_doc_constants и mcp_tool_counts разведены на отдельные строки с собственным назначением. AC-3: ✓ tests/test_doc_drift_fixes_repair_what_they_detect.py::TestThePairFormIsRepairedNotOnlyDetected::test_the_stale_half_is_rewritten — три формы пары чинятся; ::TestEveryDetectedFamilyHasARepairer::test_the_pair_pattern_reaches_the_fixer утверждает сам факт связи. AC-4: ✓ ::test_the_correct_half_is_left_alone и ::test_an_already_correct_pair_is_not_touched; отдельно ::test_a_width_change_does_not_corrupt_the_second_number — 99 в 146 при 7 в 12, случай, который правка «сначала первая группа» испортила бы, а 145 в 146 не поймал бы никогда. AC-5: ✓ ::TestTheRepairRespectsTheSameBoundariesAsTheScan — пара внутри огороженного блока не трогается, и рядом стоит предпосылка: та же пара ВНЕ блока чинится, иначе первый тест проходил бы от того, что не чинится ничего. AC-6: ✓ ::TestEveryDetectedFamilyHasARepairer::test_each_count_family_is_known_to_both_sides — четыре семейства перечислены поимённо и проверены с ОБЕИХ сторон. Перечислены руками, а не выведены из того же модуля: вывод из общего источника прошёл бы по построению и не доказал бы согласия сторон. AC-7: ✓ ::TestTheSplitDescribesItself::test_the_tables_module_does_not_claim_to_be_the_third_of_three — докстринг doc_drift_tables.py исправлен на четырёхмодульный раскол и теперь называет doc_drift_scanners, которого в перечне не было. AC-8: ✓ гейт doc_coverage не ослаблялся и исключений не добавлялось; полный прогон 10 144 passed, 27 skipped; gen_doc_constants --check зелёный. Domain: осмысленно вне тестов — починка пары прогнана на настоящих формах из живых документов, включая «**145 project + 7 brain = 152 tools**», и именно эти восемь ссылок правились руками в смене #234. Negative: три отрицательных утверждения — верная половина не переписывается, верная пара не трогается вовсе, пара внутри огороженного блока не трогается. ЗАМЕР ДО И ПОСЛЕ. До: подъём числа инструментов со 145 до 146 потребовал восьми ручных правок парной формы в семи файлах плюс правки таблиц и README — около пятнадцати на одно целое число. После: та же форма чинится командой --write.
- 2026-09-26T19:02:56Z [done] — EVIDENCE-RETIRED: tests/test_doc_drift_fixes_repair_what_they_detect.py::TestThePairFormIsRepairedNotOnlyDetected::test_the_stale_half_is_rewritten — member removed by 77703c4a (feat(knowledge)!: remove the Notion transport)
