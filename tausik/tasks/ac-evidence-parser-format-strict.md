---
slug: ac-evidence-parser-format-strict
title: "Парсер AC-evidence засчитывает только форму «AC-N:» — 61 закрытая задача цитирует существующий тест и не получает кредита"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/ac_evidence_detectors.py и/или scripts/service_ac_evidence.py (парсер привязки evidence↔AC), tests/ (репро + негативы)"
scope_exclude: "Не ослаблять gate_ac_check._test_ref_exists (fail-closed на несуществующий файл), не менять требование «номер критерия + резолвимая ссылка», PROSE/STRUCTURAL detector-реестр не ломать"
relevant_files:
  - "scripts/ac_evidence_detectors.py"
  - "scripts/service_ac_evidence.py"
  - "tests/test_ac_evidence.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:26:21Z"
---

## Goal

Измерено в сессии #133 при переводе гейта Rule 5 с подсчёта слов на структурное покрытие. service_ac_evidence распознаёт привязку доказательства к критерию практически только в форме «AC-N: ...». Причины: task_log ВСЕГДА добавляет префикс «[timestamp] », а AC_NUMBER_PREFIX_RE якорится на начало строки, поэтому естественные формы «AC verified: 1. ✓ tests/foo.py::test_x», «1. ✓ tests/...» и «- pytest tests/foo.py: 15/15 pass» дают ac_index=None и не засчитываются никуда. Форма «AC-N:» проходит, потому что матчится не с начала строки.

Цифры на реальной БД: из 561 закрытой задачи, которые новый гейт считает «без доказательств», 61 (11%) НА САМОМ ДЕЛЕ цитирует существующий файл теста — просто не в засчитываемой форме. Остальные 500 не ссылаются ни на что резолвимое. То есть гейт прав примерно в 89% случаев, а в 11% наказывает за формат.

Ирония в том, что немаппящуюся форму «AC verified: 1. ✓ ...» использовали фикстуры и журналы самого проекта — то есть формат, которому парсер не следует, порождён его же экосистемой.

Задача: расширить парсер так, чтобы он терпел префикс, добавляемый его же командой логирования, и распознавал распространённые формы привязки — НЕ ослабляя требование «номер критерия + резолвимая ссылка». Обязательные негативы: свободная проза со словом tests/ и без номера критерия кредита НЕ получает; ссылка на несуществующий файл не получает (fail-closed уже реализован в gate_ac_check._test_ref_exists). После правки пересчитать те же 61/500 и показать, что первое число упало, а второе не выросло за счёт послаблений.

## Acceptance Criteria

AC1. Парсер терпит префикс `[timestamp] `, добавляемый task_log: строка вида `[2026-...] AC verified: 1. ✓ tests/foo.py::test_x` привязывает ссылку на тест к AC-1 (ac_index=1), а не роняет в unmatched.
AC2. Распознаются распространённые формы привязки после снятия timestamp: `1. ✓ tests/...`, `AC-1: ✓ ...`, `AC1 ✓ ...`, `AC verified: 1. ✓ ...` — все дают корректный ac_index.
AC3. НЕГАТИВ (fail-closed сохранён): свободная проза со словом `tests/` без номера критерия кредита НЕ получает (ac_index=None → unmatched); ссылка на несуществующий файл не засчитывается (gate_ac_check._test_ref_exists не тронут).
AC4. Измерение на реальной БД до/после: показано, что число «ложно-без-доказательств» задач, которые НА САМОМ ДЕЛЕ цитируют существующий тест (было ~61), упало; число «реально без резолвимой ссылки» (~500) НЕ выросло за счёт послаблений.
AC5. Все существующие тесты парсера зелёные; добавлены тесты на timestamp-префикс и каждую форму + негативы.

## Plan

## Rollback

git revert; изменение в regex/парсере локально, откат возвращает строгую форму. Обратная совместимость: старые ноты продолжают парситься.

## Journal

- 2026-07-26T22:26:19Z [implementation] — AC-1: ✓ Префикс [timestamp] терпится — tests/test_ac_evidence.py::test_timestamp_and_header_prefix_bind_to_ac (форма '[ts] AC verified: 1. ✓ tests/...' привязывает ссылку к AC-1). _strip_log_prefixes снимает TIMESTAMP_PREFIX_RE + AC_HEADER_PREFIX_RE только для распознавания номера. AC-2: ✓ Все формы: '1. ✓ tests/', 'AC-1: ✓', 'AC1 ✓', 'AC: 1.✓', 'AC verified: 1. ✓' — параметризованный test_timestamp_and_header_prefix_bind_to_ac (5 форм зелёные). AC-3: ✓ НЕГАТИВ fail-closed — tests/test_ac_evidence.py::test_numberless_test_mentions_not_credited (безномерные '- pytest tests/x', 'Tests: tests/x', 'see section 3.', 'Decision #138', em-dash 'AC verified —' → covered_with_tests==0). gate_ac_check._test_ref_exists не тронут. test_header_strip_does_not_eat_ac_number_token гарантирует 'AC-1:' не съедается. AC-4: ✓ Измерение на реальной БД (scratchpad/measure_ac.py, service-layer read-only): covered_with_tests==0 590→569; MIS-SCORED (цитируют резолвимый тест, не привязан) 41→21; truly-unresolved 549→548 (НЕ вырос — послаблений нет). Остаточные 21 действительно безномерные (спот-чек brain-decide-auto-route/r14-senar-l3-marker: ссылка на строке без номера критерия). AC-5: ✓ Существующие тесты зелёные — pytest tests/ -k 'ac_check or ac_evidence or rule5 or checklist or verify_ac or task_done' 161 passed; 3 файла AC-evidence 55 passed. test_prefix_strip_preserves_raw_evidence_text: raw сохраняет timestamp (аудируемость). Verify run #1450 scoped pytest PASS. mypy: 2 файла Success. Domain: гейт теперь читает форму, порождённую собственной оснасткой проекта (task_log), а не наказывает за неё — класс #302 (детектор говорит на языке проверяемого). CHANGELOG EN+RU обновлены.
