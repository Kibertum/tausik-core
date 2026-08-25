---
slug: backlog-orphan-tasks-invisible-to-release-scope
title: "Задача без story невидима roadmap'у и подсчёту объёма релиза — класс рецидивировал, гейта нет"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/service_doctor_backlog.py (новый); scripts/project_cli_doctor.py (вызов проверки); tests/test_doctor_backlog_hygiene.py (новый); docs/ru/doctor.md; docs/en/doctor.md; CHANGELOG.md; CHANGELOG.ru.md"
scope_exclude: "scripts/project_cli_tasks.py и backend — task_add/task_done НЕ трогаем (standalone-задача законна); tausik/gates.json — новый гейт не заводим (это doctor-сигнал, не блокирующий гейт); tausik/tasks/*.md — привязка сирот едет через CLI task move, файлы дерева переэкспортируются триггером"
relevant_files:
  - "scripts/service_doctor_backlog.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_doctor_backlog_hygiene.py"
  - "docs/ru/doctor.md"
  - "docs/en/doctor.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T07:53:00Z"
---

## Goal

Граница релиза 1.8 определена решением МЕХАНИЧЕСКИ — «членство в эпике landscape-2026-h2». Задача без story_slug не принадлежит ни одному эпику, поэтому не видна ни `tausik roadmap`, ни `task list --epic`, то есть выпадает из подсчёта объёма релиза МОЛЧА. На сессии #148 таких сирот четыре, и среди них КАПСТОУН релиза `redoc-1-8-final` («итоговая редокументация под релиз 1.8») и БЛОКЕР `mcp-handlers-god-module-split` (на неё ссылаются временные именные exempt в tausik/gates.json, которые обязаны быть сняты до релиза). То есть механическое правило границы отвечало на вопрос «что осталось до 1.8» неверно, и ошибка была в пользу занижения.

Класс УЖЕ чинился: решение «Сироты привязаны» привязало предыдущие 4 сироты руками. Гейта или сигнала после этого не появилось — и за ~20 сессий накопилось ровно столько же новых. Ручная починка без сигнала не держится; чинить надо так, чтобы следующая сирота была НАЗВАНА, а не найдена случайно при подсчёте релиза.

Область: (1) привязать четыре текущие сироты к story эпика landscape-2026-h2; (2) добавить в `tausik doctor` проверку, называющую открытые (planning/active/blocked/review) задачи без story и точную команду починки. Именно открытые: закрытая сирота — безвредная история, она уже не влияет ни на один подсчёт объёма. Проверка — WARN, а не FAIL: `task_add` объявляет standalone-задачу законной («task can be standalone»), поэтому запрещать создание нельзя, но молчать про накопление — тоже.

## Acceptance Criteria

AC1. Четыре сироты привязаны к story эпика landscape-2026-h2 и после этого видны в `tausik roadmap`: redoc-1-8-final → l26-narrative; mcp-handlers-god-module-split → l26-arch-debt; filesize-rejoin-cap-deformed-wrappers → l26-arch-debt; doctor-claudemd-drift-warn-never-actionable → l26-arch-debt.
AC2. `tausik doctor` содержит проверку «Backlog hygiene», которая при наличии открытых (planning/active/blocked/review) задач без story печатает WARN, называет счётчик и до трёх слагов поимённо, и печатает точную команду починки `tausik task move <slug> <story>`.
AC3. Проверка МОЛЧИТ (не печатает ни WARN, ни строку OK-шум только при сиротах) когда сирот нет — печатает OK с нулём, а не остаётся невидимой; и НЕ считает done-задачи: closed-сирота не вызывает WARN.
AC4. Проверка не может уронить doctor: исключение внутри неё деградирует в WARN «could not validate», как у соседних service_doctor_* проверок.
AC5. Тесты: (a) сирота в planning → WARN и слаг назван; (b) сирота в done → тишина/OK; (c) сирот нет → OK; (d) сбой backend → WARN, doctor не падает.
AC6. НЕГАТИВ: проверка не блокирует ни task_add, ни task_done — standalone-задача остаётся законной, меняется только видимость.
AC7. Гейты зелёные (ruff/mypy/scoped pytest), CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью, docs/{ru,en}/doctor.md отражают новую проверку (число проверок в шапке «восемь/eight» пересчитано).

## Plan

## Rollback

git revert коммита: изменения аддитивны (новый модуль service_doctor_backlog.py + вызов в cmd_doctor + тест + строки доков). Привязка сирот откатывается обратной командой `tausik task move <slug> <старая-story>` — старой story нет, поэтому откат привязки не требуется и не планируется: сирота была дефектом состояния, а не намеренной конфигурацией.

## Journal

- 2026-07-28T07:51:01Z [implementation] — Реализовано. (1) Четыре сироты привязаны: redoc-1-8-final -> l26-narrative; mcp-handlers-god-module-split, filesize-rejoin-cap-deformed-wrappers, doctor-claudemd-drift-warn-never-actionable -> l26-arch-debt. (2) scripts/service_doctor_backlog.py — проверка достижимости из ЭПИКА (а не факта привязки к story: задача на story без эпика невидима так же). (3) Вызов в project_cli_doctor.py обёрнут try/except как соседние service_doctor_*. (4) 8 тестов зелёные. ЖИВАЯ ПРОВЕРКА ОБОИХ ПУТЕЙ: завёл tmp-orphan-probe без story -> doctor напечатал WARN со слагом и командой починки; удалил -> вернулся OK. (5) Доки RU+EN: «восемь/eight» -> «девять/nine», строка группы Backlog в таблице проверок, строка в «Типичные починки». (6) CHANGELOG.md + CHANGELOG.ru.md. (7) bootstrap.py --ide all прогнан — без него CLI исполнял старые развёрнутые копии и проверка не появлялась (конвенция #321 подтвердилась на практике).
- 2026-07-28T07:52:58Z [implementation] — AC1 ✓ Четыре сироты привязаны через task move и видны в roadmap: redoc-1-8-final -> l26-narrative; mcp-handlers-god-module-split / filesize-rejoin-cap-deformed-wrappers / doctor-claudemd-drift-warn-never-actionable -> l26-arch-debt. Проверено: doctor печатает «every open task is reachable from an epic». AC2 ✓ Проверка «Backlog hygiene» в doctor. ЖИВОЙ ПРОГОН: завёл tmp-orphan-probe без story — doctor напечатал «! Backlog hygiene 1 open task(s) belong to no epic ... : tmp-orphan-probe. Fix: tausik task move <slug> <story>». Счётчик, слаг и команда починки присутствуют. Лимит 3 слага + «+N more» покрыт test_long_orphan_list_is_summarised_not_dumped. AC3 ✓ Пустой случай печатает OK, а не исчезает — test_clean_backlog_reports_ok_rather_than_vanishing; удалил probe -> doctor вернулся в «✓ Backlog hygiene». Done-сирота молчит — test_closed_orphan_is_silent; фильтр статусов пришпилен test_only_open_statuses_are_queried (done не запрашивается). AC4 ✓ Вызов в project_cli_doctor.py обёрнут try/except Exception -> _print_warn «could not validate», как соседние service_doctor_*; test_backend_failure_degrades_to_warn_and_does_not_crash_doctor проверяет и подъём исключения из чистой функции, и наличие обёртки на месте вызова. AC5 ✓ 8 тестов в tests/test_doctor_backlog_hygiene.py, все зелёные (0.18 s): (a) сирота-planning названа; (b) сирота-done молчит; (c) чисто -> OK; (d) сбой backend -> WARN на месте вызова. Плюс кейс story-без-эпика и «никогда не fail». AC6 ✓ НЕГАТИВ: scope_exclude соблюдён — ни task_add, ни task_done не тронуты; проверка возвращает только ok/warn (test_check_never_emits_fail), гейт не заводился, tausik/gates.json не менялся. Живой прогон: task add без story создал задачу успешно, лишь QG-0 предупредил о goal. AC7 ✓ Гейты: verify #scoped pytest PASS над 11 из 355 файлов, отображённых из relevant_files; ruff «All checks passed»; mypy «Success: no issues found in 2 source files»; выборка doc/drift/changelog/lint — 494 passed, 3 skipped. Доки RU+EN: шапка «восемь->девять» / «eight->nine», группа Backlog добавлена в список и в таблицу проверок, строка в «Типичные починки». CHANGELOG.md + CHANGELOG.ru.md — прозаические записи-зеркала. bootstrap.py --ide all прогнан (конвенция #321).
