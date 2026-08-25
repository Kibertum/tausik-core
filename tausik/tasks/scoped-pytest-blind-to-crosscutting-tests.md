---
slug: scoped-pytest-blind-to-crosscutting-tests
title: "Scoped pytest не видит кросс-режущие тесты: задача закрылась зелёной, сломав три чужих теста"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/gate_test_resolver.py (чтение CROSSCUTTING_SCOPE + резолв по пути), tests/test_gate_test_resolver_crosscutting.py (новый), tests/test_crosscutting_registry.py (meta-тест видимости), декларации CROSSCUTTING_SCOPE в 6 named тестах, CHANGELOG"
scope_exclude: null
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "tests/test_gate_test_resolver_crosscutting.py"
  - "tests/test_crosscutting_registry.py"
  - "tests/test_gates.py"
  - "tests/test_hook_encoding.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "tests/test_block_message_quality.py"
  - "tests/test_mcp_single_canonical_tree.py"
  - "tests/test_check_docs_hook.py"
  - "tests/test_bypass_telemetry.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T11:09:42Z"
---

## Goal

Наблюдение сессии #133, воспроизведённое на живом закрытии. Гейт pytest скоупится через resolve_test_files_for_relevant по эвристике tests/test_<basename>.py. Задача firewall-blocked-patterns-substring-fp объявила relevant_files = [scripts/hooks/bash_firewall.py, tests/test_hooks.py, ...], гейт прогнал tests/test_hooks.py, дал PASS, задача закрылась. Полный прогон следом показал ТРИ падения, вызванные ровно этой правкой: tests/test_hook_encoding.py (новое сообщение блокировки содержит не-ASCII, а хук не звал force_utf8_io), tests/test_check_docs_hook.py (docs/_generated/constants.json разошёлся — вырос счётчик тестов) и tests/test_agent_units_recording.py (фикстура опиралась на снятый предикат). Ни один из трёх не маппится на изменённые файлы по basename-эвристике и не мог быть найден скоупом в принципе.

Это не дефект эвристики как таковой — это её ЗАЯВЛЕННАЯ граница, которая нигде не заявлена. Класс тестов, о котором речь, устроен обратно эвристике: они итерируют по ДЕРЕВУ (все хуки, все доки, все профили) и потому релевантны любому изменению внутри дерева, не будучи привязанными к basename. Их в репозитории заметное число: test_hook_encoding, test_bootstrap_hooks_parity, test_block_message_quality, test_mcp_single_canonical_tree, test_check_docs_hook, test_bypass_telemetry.

Задача: сделать эту границу управляемой, а не невидимой. Кандидат — реестр «кросс-режущих» тестов с декларацией области, к которой они применимы (например, tests/test_hook_encoding.py применим при любом изменении в scripts/hooks/**), и включение таких тестов в scoped-прогон по совпадению пути, а не basename. Требование к решению: НЕ откатываться к полному suite (v1.3 его убрала осознанно — бюджет MCP), и не превращать реестр в список, который забудут пополнить — привязка должна выводиться из того, по чему тест итерирует, либо отсутствие привязки должно быть видимым.

## Acceptance Criteria

AC1. Cross-cutting тест объявляет охраняемую область module-level константой CROSSCUTTING_SCOPE (список path-префиксов). Резолвер scoped-pytest включает такой тест, если ЛЮБОЙ relevant_file начинается с любого префикса — по ПУТИ, не basename. Тест: relevant_files=[scripts/hooks/x.py] тянет тест с scope scripts/hooks/ без basename-совпадения. | AC2. Не откат к полному suite: резолвер добавляет только матчнувшие cross-cutting тесты; не-матч не тянет ничего; пустой результат по-прежнему SKIP. | AC3. Отсутствие привязки ВИДИМО: meta-тест детектит тесты, итерирующие исходное дерево (os.walk/glob/rglob по scripts|bootstrap|harness|docs|.claude через root-anchor) БЕЗ CROSSCUTTING_SCOPE, падает со списком — вынуждая объявить область ИЛИ явный опт-аут CROSSCUTTING_SCOPE=[] (просмотрено, не cross-cutting). Реестр не может молча устареть. | AC4. Декларации не гниют: meta-тест проверяет, что каждый префикс в CROSSCUTTING_SCOPE соответствует существующему пути. | AC5. Именованные cross-cutting тесты (test_hook_encoding, test_bootstrap_hooks_parity, test_block_message_quality, test_mcp_single_canonical_tree, test_check_docs_hook, test_bypass_telemetry) получили корректные CROSSCUTTING_SCOPE. | AC6. Полный pytest зелёный; CHANGELOG EN+RU.

## Plan

## Rollback

git revert — изменения изолированы в gate_test_resolver.py + новые тесты + декларации-константы в существующих тестах. Нет схемы/БД/данных. Откат убирает cross-cutting резолв, возвращает чистый basename-heuristic.

## Journal

- 2026-07-27T10:58:05Z [implementation] — Реализовано: (1) gate_test_resolver.read_crosscutting_scope (AST, no-import) + _crosscutting_index (grep-first, затем parse) + интеграция в resolve_test_files_for_relevant (аддитивно, по _under_prefix с directory-boundary). (2) CROSSCUTTING_SCOPE объявлен на 6 named тестах. (3) test_crosscutting_registry.py — храповик видимости: heuristic (ITER+ANCHOR+SRC) детектит tree-iterators; каждый обязан declare/opt-out/grandfather; _GRANDFATHERED (30) только сжимается; self-exclusion детектора. (4) AC4: объявленные префиксы проверяются на существование. Обновил test_gates::test_all_skipped (premise устарел: scripts/ файл теперь тянет cross-cutting тесты scope=scripts/ — сменил на unmapped top-level путь). 28 таргет-тестов + 112 (gates+meta+resolver) зелёные. Root cause (missing-validation): граница basename-эвристики резолвера реальна, но нигде не заявлена — tree-iterating тесты невидимы скоупу. Prevention: храповик делает отсутствие привязки видимым (новый недекларированный tree-iterator краснит CI).
- 2026-07-27T11:09:01Z [implementation] — AC1 (path-match, не basename): ✓ gate_test_resolver.read_crosscutting_scope + резолв по _under_prefix; test_gate_test_resolver_crosscutting.py::test_change_in_tree_pulls_the_crosscutting_test — relevant=[scripts/hooks/bash_firewall.py] тянет тест с scope scripts/hooks/. Живой репо: test_hooks_change_includes_named_crosscutting_tests (scripts/hooks/ тянет test_hook_encoding.py). | AC2 (нет отката к suite): ✓ test_no_match_pulls_no_crosscutting (unmatched → []), test_prefix_respects_directory_boundary (scripts/hooks/ не матчит scripts/hooks_helpers/). Аддитивно. | AC3 (отсутствие видимо): ✓ test_crosscutting_registry.py храповик — heuristic (ITER+ANCHOR+SRC) детектит tree-iterators; test_new_tree_iterator_must_declare_or_optout падает на недекларированном не-grandfathered; _GRANDFATHERED(30) только сжимается (test_grandfather_baseline_only_shrinks); опт-аут CROSSCUTTING_SCOPE=[]. | AC4 (не гниёт): ✓ test_every_declared_prefix_points_at_a_real_path. | AC5: ✓ 6 named тестов декларированы (hook_encoding, bootstrap_hooks_parity, block_message_quality, mcp_single_canonical_tree, check_docs_hook, bypass_telemetry). | AC6: ✓ полный pytest 6157 passed (1 teardown-race от конкурентного bootstrap, изолированно 28/28 зелёные — не дефект). CHANGELOG EN+RU. Обновил test_gates::test_all_skipped (устаревший premise: scripts/ файл теперь тянет cross-cutting scope=scripts/). Domain: scoped verify этой задачи покрыл 10 файлов (вкл. подтянутые cross-cutting) вместо 1-2 — механизм работает на живом прогоне.
- 2026-07-27T11:09:40Z [implementation] — AC1-6 verified (см. task log). path-match резолвер + 6 деклараций + храповик видимости + AC4 существование префиксов. Полный pytest 6157 passed (1 teardown-race от конкурентного bootstrap, изолированно зелёный). CHANGELOG EN+RU. test_gates::test_all_skipped обновлён (устаревший premise). Domain: scoped verify задачи покрыл 10 файлов вместо 1-2 — механизм работает вживую.
