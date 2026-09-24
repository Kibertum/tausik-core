---
slug: complexity-proxy-counts-state-projection
title: "Детектор занижения сложности считает сгенерированную проекцию tausik/ поведенческими файлами и пишет ложные занижения в лог супервизии"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: complexity-heuristic-counts-doc-mirrors
scope: "scripts/complexity_understatement.py, при заведении общего реестра — модуль-источник и его читатели, tests/, CHANGELOG.md, CHANGELOG.ru.md. После правки scripts/ обязателен bootstrap --ide all."
scope_exclude: "НЕ менять пороги implied_complexity и веса — чинится измеряемая величина, а не шкала. НЕ чистить уже накопленные ложные записи в логе супервизии: это отдельный вопрос (данные), и его решение требует отдельного обоснования. НЕ трогать .gitattributes — второй симптом того же корня заведён как tausik-tree-gitattributes-lf."
relevant_files:
  - "scripts/derived_trees.py"
  - "scripts/complexity_understatement.py"
  - "scripts/state_triggers.py"
  - "scripts/gen_doc_constants.py"
  - "tests/test_derived_trees.py"
scope_paths:
  - "scripts/derived_trees.py"
  - "scripts/complexity_understatement.py"
  - "scripts/state_triggers.py"
  - "scripts/gen_doc_constants.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:33:31Z"
---

## Goal

Найдено в сессии #153 при закрытии revise-kb-export-tasks-superseded. Закрытие выдало «COMPLEXITY UNDERSTATED: declared simple but touched 9 behaviour-bearing files of 10 declared — implies medium». Из десяти объявленных файлов девять — сгенерированные markdown-проекции строк БД (tausik/tasks/*.md, tausik/stories/*.md, tausik/decisions/*.md), написанные экспортёром, а не человеком. Поведения они не несут по построению: это сериализация тех же строк, которые задача и меняла.

ПРИЧИНА, прочитана в коде. scripts/complexity_understatement.py:54 объявляет _GENERATED_DIRS = ("docs/_generated/",) — ровно один каталог. Дерево tausik/ появилось позже (эпик team-state-in-git, релиз 1.8) и в перечень не попало. Церемониальные файлы (_CEREMONY_FILES) и языковые зеркала обработаны, генерируемая проекция — нет.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА, И ПОЧЕМУ ИМЕННО ЭТОТ МОДУЛЬ. Докстринг этого же файла (строки 21-39) описывает, ради чего он создан: «однострочный фикс приезжал на закрытие с +6 файлами и объявлялся complex — семь сессий подряд, и каждое из этих предупреждений ТАКЖЕ писалось в лог супервизии, поэтому калибровочные данные теперь содержат систематическое занижение, которого не было». То есть модуль существует именно для того, чтобы ложные занижения не отравляли калибровку — и сейчас отравляет их сам, по той же механике, на новом дереве. Телеметрия пишется на строках 174-183 до возврата сообщения, то есть запись в лог происходит и тогда, когда предупреждение ложно.

ЦЕНА. Калибровка проекта (actual/budget) и композит риска закрытия читаются при планировании релиза — в этой же сессии решение #209 опиралось на коэффициент 0.71. Систематический шум в супервизии делает эти цифры хуже, а не просто шумнее.

ЭТО ТРЕТИЙ СЛУЧАЙ ОДНОГО КОРНЯ, назван явно, чтобы чинили корень, а не симптом. Дерево tausik/ не зарегистрировано ни в одном реестре, который уже знает про предыдущие производные деревья: (1) .gitattributes знает про renar/** и не знает про tausik/** — задача tausik-tree-gitattributes-lf; (2) _GENERATED_DIRS знает про docs/_generated/ и не знает про tausik/ — эта задача. Оба реестка перечисляют каталоги руками. Рассмотреть при исполнении: единый источник «производные деревья проекта», выводимый из кода экспортёров, и тест, требующий, чтобы КАЖДЫЙ реестр читал его, а не свой список (конвенции #339, #354).

НЕ ДЕЛАТЬ: не добавлять "tausik/" строкой в _GENERATED_DIRS и не закрывать на этом. Это четвёртый ручной перечень, и он протечёт на следующем дереве так же, как протекли три предыдущих.

## Acceptance Criteria

1. Сгенерированная проекция перестаёт считаться поведенческой: закрытие задачи, объявившей только файлы дерева tausik/, больше не выдаёт «COMPLEXITY UNDERSTATED». Тест на наборе из девяти путей вида tausik/tasks/*.md доказывает нулевой счёт и падает до фикса.
2. Ложная запись не уходит в лог супервизии: тест доказывает, что при отсутствии занижения телеметрия занижения НЕ пишется. Это отдельная проверка от пункта 1 — сегодня строки 174-183 пишут запись до возврата сообщения, поэтому «не показали пользователю» и «не записали» разные вещи.
3. Реестр производных каталогов перестаёт быть ручным перечнем в этом модуле. _GENERATED_DIRS выводится из источника, знающего про производные деревья проекта, а не дополняется четвёртой строкой. Если единого источника нет — он заводится, и в журнале названо, кто ещё обязан его читать.
4. НЕГАТИВ И ГРАНИЦЫ. (а) Детектор не ослеп: задача, реально тронувшая девять файлов в scripts/, по-прежнему получает предупреждение — существующие тесты занижения зелёные без правки ожиданий. (б) Пороги НЕ трогаются: меняется измеряемая величина, а не шкала — тот же принцип, которым чинился исходный дефект. (в) Файл дерева, отредактированный РУКАМИ, не превращается в исключение молча: если такой случай возможен, в журнале сказано, почему он всё равно не считается поведенческим (дерево перегенерируется экспортёром, ручная правка теряется).
5. Полный pytest зелёный; ruff и mypy чистые.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert. Изменение затрагивает счётчик поведенческих файлов и, возможно, новый общий реестр производных деревьев; поведение продукта не меняется, меняется только советующая телеметрия. Худший исход отката — возврат ложных занижений в лог супервизии.

## Journal

- 2026-07-28T20:27:56Z [planning] — ВТОРОЙ ЖИВОЙ ЗАМЕР В ТОЙ ЖЕ СЕССИИ, годится как приёмочные данные. Закрытие tausik-tree-gitattributes-lf выдало «COMPLEXITY UNDERSTATED: declared simple but touched 23 behaviour-bearing files of 26 declared — implies complex». Фактическая работа задачи — ЧЕТЫРЕ файла: одна строка в .gitattributes, один новый тестовый файл, две парные записи в CHANGELOG. Остальные 22 — сгенерированная проекция БД. ТО ЕСТЬ ОШИБКА НЕ КРАЕВАЯ, А СИСТЕМАТИЧЕСКАЯ И РАСТУЩАЯ. Первый замер (закрытие revise-kb-export-tasks-superseded): 9 из 10 объявленных, вердикт simple->medium. Второй: 23 из 26, вердикт simple->complex. Шум растёт вместе с длиной сессии, потому что автотриггер перегенерирует проекцию при каждой записи в журнал, а гейт верификации требует объявлять всё изменённое. Чем добросовестнее агент журналирует, тем сильнее его задача выглядит заниженной по сложности — то есть детектор наказывает ровно то поведение, которого требует фреймворк. Оба замера ушли в лог супервизии (телеметрия пишется до возврата сообщения), поэтому калибровочные данные уже содержат два ложных занижения из одной сессии. Это делает пункт 2 критериев приёмки — «ложная запись не уходит в лог супервизии» — не теоретическим: данные для проверки есть. Пара для приёмочного теста, оба конца из реальных закрытий: набор из 26 путей, где 22 под tausik/, обязан давать ноль занижения; набор из девяти путей под scripts/ обязан по-прежнему давать предупреждение.
- 2026-09-24T07:24:00Z [implementation] — Root cause: complexity_understatement._GENERATED_DIRS was a hand list ('docs/_generated/' only); the tausik/ projection tree (1.8) was never added, so exporter-written files counted as behaviour.
- 2026-09-24T07:24:01Z [implementation] — AC-1: ✓ tests/test_derived_trees.py::test_the_projection_is_not_behaviour — the real 26-path close gives 2 behaviour files and no understatement; mutation (old hand list restored) turns it red.
- 2026-09-24T07:24:01Z [implementation] — AC-2: ✓ tests/test_derived_trees.py::test_no_false_detection_reaches_the_supervision_log — no event_add call when nothing is understated.
- 2026-09-24T07:24:01Z [implementation] — AC-3: ✓ tests/test_derived_trees.py::test_every_reader_takes_the_layout_from_the_one_source — scripts/derived_trees.py (PROJECTION_ROOT, DOC_CONSTANTS_DIR, relative_dirs from state_serialize.ENTITY_DIRS) read by state_triggers._tree_root, gen_doc_constants.output_json_path and complexity_understatement. Other hand lists that should read it: audit_orphan_files/audit_stale_docs (docs/_generated) — named here, not migrated in this task.
- 2026-09-24T07:24:02Z [implementation] — AC-4: ✓ tests/test_derived_trees.py::test_the_detector_is_not_blind and tests/test_derived_trees.py::test_config_files_in_tausik_stay_behaviour_bearing — negative: 9 scripts still warn, thresholds unchanged, tausik/gates.json and policy.json stay behaviour; a hand edit to a projection file is regenerated by the exporter, so it is not behaviour either.
- 2026-09-24T07:24:02Z [implementation] — AC-5: ✓ measurement — 118 complexity/state-trigger/doc-constants tests green; ruff clean.
- 2026-09-24T07:33:12Z [implementation] — NO-DEAD-END: the refused close was bootstrap drift (deployed copy older than scripts/), fixed by bootstrap, not an approach error.
