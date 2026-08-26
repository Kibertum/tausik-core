---
slug: full-lane-runs-serial-on-a-twenty-core-machine
title: "Полная лента идёт в один поток на двадцатиядерной машине: 32 минуты вместо четырёх"
status: planning
epic: null
story: null
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕРЕНО В СЕССИИ #186, НЕ ПРЕДПОЛОЖЕНО. Полная лента (`pytest -m ''`) на дереве 3c3c87a: последовательно — 7395 passed за 32m24s; под `-n auto` на 20 ядрах — 7397 passed, 24 skipped, 2 failed за 228.59s (3m48s). УСКОРЕНИЕ 8.5x.

pytest-xdist не установлен и не упомянут НИГДЕ: ни в pyproject.toml, ни в requirements.txt, ни в .gitlab-ci.yml, ни в .github/workflows/*.yml. Девятнадцать ядер из двадцати простаивают все 32 минуты.

ПОЧЕМУ ЭТО НЕ ЛЕЧИТСЯ ВЫЧЁРКИВАНИЕМ ТЕСТОВ. Стоимость ленты ПЛОСКАЯ — записано в самом pyproject.toml: «30 самых медленных это 10% от неё, остальное ~0.09 s x 5700». И масса корпуса тоже плоская: 409 файлов, 5859 функций, топ-20 файлов дают 18% массы, топ-60 — 37.5%. Толстого хвоста, вырезав который что-то изменится, НЕ СУЩЕСТВУЕТ. Вычеркнуть 1000 тестов (17% корпуса, недели судейства, риск снести настоящего стража) купило бы примерно 5 минут. Одна строка конфига покупает 28.

ДВА ПАДЕНИЯ ЗАМЕРА, И ОНИ РАЗНЫЕ:
1) tests/test_mypy_clean.py::test_declared_tree_is_mypy_clean — АРТЕФАКТ ЗАМЕРА, не находка: во временное окружение не был поставлен mypy, тест честно сказал «No module named mypy». К xdist отношения не имеет.
2) tests/test_stress.py::TestStressSessions::test_100_sessions — НАСТОЯЩИЙ кандидат в xdist-небезопасные. Воркер gw14 умер («node down: Not properly terminated»), трассировка ведёт в service_session.session_end -> subprocess.run. Стресс-тест, поднимающий 100 сессий, под двадцатью параллельными воркерами либо дерётся за общий ресурс (.tausik/, SQLite, cwd), либо выедает машину. РАЗОБРАТЬ, а не объявить: либо чинится, либо получает объявленную последовательную группу (xdist_group), и причина записывается словами.

ЧТО ДЕЛАЕТСЯ: pytest-xdist в requirements.txt, `-n auto` в [tool.pytest.ini_options], разбор test_100_sessions. Проверить взаимодействие с faulthandler_timeout = 60 и faulthandler_exit_on_timeout: в замере сторож зависаний ЛОЖНО НЕ СРАБОТАЛ ни разу под двадцатью воркерами, но это надо закрепить, а не запомнить. Проверить, что порядок тестов, ставший недетерминированным, не прячет тесты, зависящие друг от друга.

ФЕНС ВЛАДЕЛЬЦА: pyproject.toml правится только с его согласия и ОДНИМ ЗАХОДОМ вместе с hang-guard-promises-eleven-times-headroom-and-has-one и pytest-asyncio-default-loop-scope-unset-warns-on-every-run — все три правят один и тот же блок [tool.pytest.ini_options].

ОГОВОРКА К ЧИСЛАМ: замер гонялся с --ignore двух bootstrap-модулей (скопировано из CI), поэтому 7397 и 7395 — не строго одна выборка. Порядок ускорения это не меняет, но при закреплении базовой линии выборки обязаны совпасть.

## Acceptance Criteria

## Plan

## Rollback

## Journal
