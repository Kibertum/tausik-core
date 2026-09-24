---
slug: task-next-ignores-declared-wave-order
title: "task next не уважает объявленный порядок волны: голова волны не выдаётся, выигрывает несвязанная задача"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_task_deps.py"
  - "scripts/service_task_order.py"
  - "scripts/service_task_team.py"
  - "tests/test_task_next_prefers_the_release.py"
scope_paths:
  - "scripts/backend_task_deps.py"
  - "scripts/service_task_order.py"
  - "scripts/service_task_team.py"
  - "scripts/render_task.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:16:26Z"
---

## Goal

ЗАМЕР (сессия #183, до кода): голова волны 2 релиза 1.9 — check-result-conflates-could-not-run-with-passed — НЕ выдаётся командой task next. Выигрывает brainh-reliability, с волной 1.9 ничем не связанная. Агент вынужден брать волну ЯВНО по тексту плана; команда, существующая ровно чтобы отвечать «что дальше», отвечает мимо.

РАЗЛИЧЕНИЕ, ВАЖНОЕ ДЛЯ ДИАГНОЗА: парные рёбра task depends команда УВАЖАЕТ — внутри волны порядок соблюдается (проверено на цепочке js-test-gate -> four-byte-identical-copies -> drift7). Дефект не в рёбрах, а в том, что ОБЪЯВЛЕННЫЙ порядок волны частичный: между «головой волны» и произвольной задачей вне волны ребра нет, и ранжирование решает вес, а не план.

ЧТО РЕШАЕТСЯ: task next обязан уважать объявленный порядок релиза/волны, а не только парные рёбра. Форма решения — предмет задачи (ребро на эпик/story, вес принадлежности к активной волне, явный фильтр — варианты сравнить ДО кода).

ПРОИСХОЖДЕНИЕ: найдено при передаче волны 2 в хэндоффе #182, заведено по решению владельца в сессии #183. Владелец выбрал «завести задачу в 1.9» из трёх вариантов (завести в 1.9 / завести вне 1.9 / не заводить).

НЕ ПУТАТЬ с задачей task-next-cannot-express-work-order (решение #259, порядок работ выражается ребром, а не числом приоритета): та задача дала рёбра, эта — о том, что рёбер НЕДОСТАТОЧНО для выражения порядка волны.

## Acceptance Criteria

1. task next ranks first the offerable tasks whose story belongs to the release composition in force (release_roadmap_composition.composition, read from decisions), then by declared predecessor edges and score as before; the 'Chosen by' line names the release. 2. NEGATIVE: a test builds a backlog where a higher-score task outside the release competes with a release task and requires the release task. 3. NEGATIVE: with no declared composition (RoadmapUnreadable) the old order applies unchanged; a task outside the release is still offered when the release has nothing offerable. 4. Live: on this repository task next offers a 1.10 task (it offered brainh-semantic-search before).

## Plan

## Rollback

Правка порядка выдачи в task next. Откат: git revert. Данные о порядке (рёбра task_deps) не изменяются — меняется только их прочтение, поэтому откат ничего не теряет.

## Journal

- 2026-08-29T14:22:52Z [planning] — [#189] ВЕРНУТА В 1.9 ПОСЛЕ ПРОВЕРКИ ПЛАНА. Прогнал task next на готовом плане релиза: он предложил brainh-reliability — задачу из ЧУЖОГО эпика (brain-hardening, Notion sync), при 53 свободных задачах 1.9 и объявленном порядке в 28 рёбрах. Строка обоснования печатает «Chosen by: declared order first, then complexity score», но выбор идёт по ВСЕМУ бэклогу из 190+ открытых задач, а не по релизу. Следствие прямое: при многоагентной работе агенты разберут случайные задачи из разных эпиков вместо ленты релиза, и объявленный порядок работ окажется декорацией. Это делает задачу условием выполнимости плана, а не улучшением удобства — потому она переезжает из arch-debt в историю про параллельную работу.
- 2026-09-24T07:15:34Z [implementation] — AC-1: ✓ tests/test_task_next_prefers_the_release.py::test_a_release_task_beats_a_higher_score_outside — task_next_candidate(release_story_ids) orders CASE story_id IN release first; service_task_order.release_story_ids reads composition(); basis 'release <v> first, then declared order, then complexity score'; team task_next uses it too.
- 2026-09-24T07:15:34Z [implementation] — Root cause: backend_task_deps.task_next_candidate ordered only by score among offerable tasks; the release composition existed (release_roadmap_composition) but nothing in task next read it.
- 2026-09-24T07:15:35Z [implementation] — AC-2: ✓ tests/test_task_next_prefers_the_release.py::test_a_release_task_beats_a_higher_score_outside — negative, score 99 outside vs 1 inside; mutation (release ordering dropped) -> red; restored.
- 2026-09-24T07:15:35Z [implementation] — AC-3: ✓ tests/test_task_next_prefers_the_release.py::test_without_a_declared_release_the_old_order_holds and tests/test_task_next_prefers_the_release.py::test_outside_work_is_still_offered_when_the_release_has_none — negative.
- 2026-09-24T07:15:35Z [implementation] — AC-4: ✓ measurement — live: task next now offers changed-path-does-not-require-its-artifact-to-move (1.10) with 'Chosen by: release 1.10 first'; before: brainh-semantic-search.
