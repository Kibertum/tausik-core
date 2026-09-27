---
slug: two-tests-fail-only-under-parallel-and-hide-which-step-broke
title: "Два теста падают только под параллелью и скрывают, какой шаг сломался"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 40
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

НАЙДЕНО ПОЛНЫМ ПРОГОНОМ в смене #277 (задача 683-structurally-identical-tests-in-294-groups, AC-6). Два теста зелены в изоляции и КРАСНЫ в параллельном прогоне, причём в двух полных прогонах подряд:

  tests/test_mcp_integration.py::TestMCPNewToolHandlers::test_dead_end_handler
  tests/test_consumer_first_close.py::ТестНовыйПроектЗакрываетПервуюЗадачу::test_путь_целиком_проходит

ДОКАЗАНО, ЧТО ДЕФЕКТ ДОСТАВШИЙСЯ, а не внесён той задачей: `git stash` правок смены и повторный прогон дают ТЕ ЖЕ два отказа (81 passed, 2 failed, 41 с).

РЕЦЕПТ ВОСПРОИЗВЕДЕНИЯ ДЕШЁВЫЙ — 42 секунды вместо восьмиминутной ленты:
python -m pytest tests/test_consumer_first_close.py tests/test_mcp_integration.py tests/test_bootstrap_drift_gate.py tests/test_hosts_coexist.py tests/test_migrations.py -q -p no:randomly -m "" -n auto

ВТОРАЯ НАХОДКА ВАЖНЕЕ ПЕРВОЙ: потребительский тест СКРЫВАЕТ, какой шаг сломался. Он падает на `assert done.returncode == 0` с сообщением «Task 'add-subtract' was never started, so it cannot close as delivered» — то есть упал РАНЬШЕ, на `task start`, а код возврата start не проверяется. Тест сам предупреждает об этой ловушке в соседнем утверждении («дальше проверялся бы не тот отказ»), но к самому start её не применяет. Читатель видит отказ закрытия там, где сломался старт.

ЧТО СДЕЛАТЬ: (1) проверять код возврата КАЖДОГО шага потребительского пути, чтобы отказ назывался своим именем; (2) назвать причину отказа под параллелью — тест создаёт временный проект и гоняет настоящий CLI подпроцессом, так что подозреваемые: блокировка SQLite под нагрузкой, конкурентная перезапись профиля другим тестом, общий путь во временном каталоге; (3) починить причину, а не отключить тест маркером.

ПОЧЕМУ ЭТО ДОРОГО: потребительский путь — единственный тест, проходящий установку в новый проект целиком. Его отказ под параллелью означает, что полная лента в CI не даёт о нём правды, а изоляция даёт ложное спокойствие.

## Acceptance Criteria

## Plan

## Rollback

## Journal
