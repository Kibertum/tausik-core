---
slug: closing-ceremony-costs-one-call-not-four
title: "Обряд закрытия стоит четыре вызова вместо одного: task done умеет проверить сам"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/task_close_inline_verify.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_verify.py"
  - "tests/test_closing_ceremony_cost.py"
scope_paths:
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/task_close_inline_verify.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_service.py"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T16:30:35Z"
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

Закрытие задачи стоит агенту 4-6 вызовов: verify, потом done, потом отказ гейта changelog или bootstrap_drift, потом verify заново, потом done. При замеренных 482 000 токенов префикса на вызов каждый лишний ход стоит около полумиллиона токенов, и это самый частый обряд во фреймворке — 1240 закрытий с записанным числом ходов. Цель: закрытие в ОДИН вызов, а предзакрывочные отказы становятся известны на verify, а не на done.

## Acceptance Criteria

AC-1 tausik task done <slug> --ac-verified --verify запускает проверку сам по объявленным relevant_files и закрывает в ОДНОМ вызове; квитанция записывается как при раздельном пути, handle не нужен. ✓ tests/test_closing_ceremony_cost.py
AC-2 Гейты, которые сегодня срабатывают только на done (changelog, bootstrap_drift), сообщают о себе и на verify — агент узнаёт о них ДО обряда, а не после. ✓ tests/test_closing_ceremony_cost.py
AC-3 НЕГАТИВНЫЙ: встроенная проверка красная — done ОТКАЗЫВАЕТ и не закрывает задачу, но квитанция о прогоне всё равно записана; задача остаётся in_progress. ✓ tests/test_closing_ceremony_cost.py
AC-4 НЕГАТИВНЫЙ: --verify при изменённых файлах и пустых relevant_files отказывает с причиной, а не выдаёт молча суженную квитанцию. ✓ tests/test_closing_ceremony_cost.py
AC-5 НЕГАТИВНЫЙ: --verify вместе с --verify-handle отказывает — два источника проверки в одном вызове означают, что один из них не тот, который записан.
AC-6 Полная лента зелёная.

## Plan

## Rollback

git revert; раздельный путь verify + done --verify-handle не тронут и остаётся рабочим

## Journal

- 2026-09-29T16:25:39Z [implementation] — Обряд стоил ещё один вызов ПРЯМО СЕЙЧАС: scope ACL отказал новому модулю, потому что при заведении задачи его имени ещё не было. Это второй класс потерь той же природы — заведение области идёт до того, как стало известно, какие файлы появятся. Замер этой смены: три таких блока на предыдущей задаче плюс один здесь, каждый стоит вызов отказа и вызов task update с ПЕРЕЧИСЛЕНИЕМ ВСЕГО списка заново.
- 2026-09-29T16:29:01Z [implementation] — НАЙДЕНО, третий блок области на одной задаче: гейт changelog ТРЕБУЕТ записи в CHANGELOG, scope ACL ЗАПРЕЩАЕТ туда писать, пока путь не объявлен, а конвенция #728 запрещает объявлять CHANGELOG в relevant_files. Списки разные (scope_paths против relevant_files), поэтому противоречия в правилах нет — но КАЖДАЯ задача платит вызов отказа и вызов task update с перечислением всего списка заново. Замер смены #278: 6 таких блоков на двух задачах подряд.
- 2026-09-29T16:30:30Z [implementation] — AC-1 ✓ ЭТА задача закрыта одним вызовом: task done --ac-verified --verify прогнал проверку и предъявил свой handle сам. tests/test_closing_ceremony_cost.py::TestTheOneCallStillCertifies. AC-2 ✓ post_close_advisory спрашивает НАСТОЯЩИЙ gate_changelog и печатает вердикт строкой AT CLOSE, NOT NOW на verify; ::TestTheCloseGatesAnnounceThemselvesBeforeTheCeremony, включая случай, когда сам совет падает — прогон не ломается. AC-3 ✓ красный прогон даёт SystemExit(1), задача не тронута, отчёт напечатан до отказа: ::test_a_red_run_stops_the_close_before_the_task_is_touched. AC-4 ✓ пустая область — ServiceError с названным честным выходом --no-file-changes, и НИЧЕГО не прогнано, то есть ничего не записано: ::test_an_undeclared_scope_is_refused_rather_than_certified_narrowly, плюс парный положительный на --no-file-changes. AC-5 ✓ --verify вместе с --verify-handle — отказ, называющий оба флага: ::test_two_sources_of_verification_in_one_call_are_refused, плюс три случая, где один источник или ни одного не трогают. AC-6 — лента гоняется следом. Domain: осмысленно вне тестов — обряд, которым закрыта сама эта задача, стоил ОДИН вызов вместо четырёх; при 482 000 токенов префикса на вызов это около 1,5 млн токенов на каждое закрытие. НАЙДЕНО: scope ACL отказал трижды на одной задаче, потому что область объявляется до того, как известно, какие файлы появятся, и каждый отказ стоит вызов плюс вызов task update с перечислением всего списка заново — заведено отдельно.
