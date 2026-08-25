---
slug: event-window-boundary-flake
title: "Флейк: task_event_count_in_window undercount на границе секунды (windows-3.13 CI)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_queries.py"
  - "tests/test_agent_units_recording.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-17T21:48:04Z"
---

## Goal

Честный CI задачи ci-slow вскрыл скрытый флейк. test_counts_events_in_window упал 'assert 3>=4' на windows-latest/3.13 (1 из 11 ячеек; локально 3.11 и 3.13 по 25/25 pass — недетерминирован). Корень: utcnow_iso()='%Y-%m-%dT%H:%M:%SZ' секундной гранулярности; task_event_count_in_window (backend_queries.py:318) ограничивает окно сверху julianday(COALESCE(completed_at,'now')). Для АКТИВНОЙ задачи (completed_at IS NULL) 'now' при запросе может оказаться РАНЬШЕ только что записанных событий (created_at усечён к следующей секунде / skew писатель-vs-SQLite'now') → свежие события выпадают из окна → undercount. Фикс: для активной задачи верхнюю границу не применять (все события >= started_at); completed_at-cap только для завершённой.

## Acceptance Criteria

1. Детерминированное репро: для активной задачи событие с created_at в усечённой/будущей секунде относительно SQLite now считается в окне (на старом коде выпадает). 2. Фикс task_event_count_in_window: активная задача (completed_at IS NULL) без верхней границы (все события >= started_at); завершённая cap на julianday(completed_at). 3. Регресс-тест детерминированно падает на старом коде, проходит на новом. 4. Локально зелено: полная полоса -m '' по файлу + мета-гард 5/5 + ruff чист. 5. Зелёная GitHub-матрица: все 11 ячеек + test-full + lint. 6. Негативный граничный кейс: при отсутствующем started_at (пустое окно) функция возвращает 0 без исключения. 7. Для завершённой задачи событие позже completed_at не должно попадать в окно (верхняя граница сохранена).

## Plan

## Rollback

git revert коммита фикса; запрос окна возвращается к прежней верхней границе 'now'

## Journal

- 2026-07-17T21:18:28Z [implementation] — Фикс task_event_count_in_window: для активной задачи (completed_at NULL) снята верхняя граница 'now' (считаем все события >= started_at); completed_at-cap только для завершённой. 2 регресс-теста: active-window (падает 2 vs 3 на старом коде — доказано git stash; проходит на новом), completed-negative. Локально: TestEventCountWindow 6/6 на 3.11 и 3.13, ruff чист, +2 теста -> test_count 4742->4744 -> регенерирован constants.json + бейджи README.md/README.ru.md, строгий doc-check зелёный. QG-2 receipt 1008. Коммит a5e01df -> origin(GitLab) 5beafae..a5e01df. Жду dev-гейт GitLab 3817 перед публикацией на github.
- 2026-07-17T21:48:04Z [implementation] — AC verified: 1. ✓ детерминированное репро test_active_window_counts_event_stamped_at_or_after_now (событие created_at=started+5s). 2. ✓ фикс backend_queries.py: активная (completed_at NULL) без верхней границы, завершённая cap на julianday(completed_at). 3. ✓ регресс падает на старом коде (git stash: 2 вместо 3), проходит на новом. 4. ✓ локально: TestEventCountWindow 6/6 на 3.11 и 3.13, мета-гард 5/5, ruff чист, строгий+skip doc-check зелёные. 5. ✓ GitHub-матрица run 29614582518: все 11 ячеек + test-full(4598 passed/134 skip=4732) + lint success; windows-3.13 зелёный. 6. ✓ негатив: test_zero_when_no_started_at — при отсутствующем started_at возвращает 0 без исключения. 7. ✓ test_completed_window_excludes_event_after_completion — для завершённой задачи событие после completed_at не считается.
