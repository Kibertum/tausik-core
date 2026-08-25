---
slug: project-cli-main-guard
title: "3.1: project_cli.py без __main__-гварда — запуск как скрипта молча возвращает 0"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "scripts/cli_entrypoint.py (новый), scripts/project_cli*.py, tests/."
scope_exclude: "Не трогать scripts/project.py — это настоящая точка входа."
relevant_files:
  - "scripts/cli_entrypoint.py"
  - "scripts/project_cli.py"
  - "tests/test_cli_entrypoint_guard.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T13:13:51Z"
---

## Goal

Подтверждено: 'python .claude/scripts/project_cli.py skill sign <dir>' печатает пустоту и выходит с 0, подпись не ставится; в файле нет ни одного вхождения __main__. Добавить гвард, который либо выполняет CLI, либо отказывает с понятной ошибкой и ненулевым кодом ('запускай через .tausik/tausik'). Молчаливый успех хуже отказа: пользователь уверен, что подпись поставлена.

## Acceptance Criteria

1) Запуск любого scripts/project_cli*.py напрямую печатает понятную ошибку в stderr и выходит с ненулевым кодом. 2) Ошибка называет правильную точку входа (.tausik/tausik). 3) Импорт модулей не ломается. Негативные сценарии: 4) Ошибка, если хоть один project_cli*.py по-прежнему возвращает 0 и пустой вывод — тест перебирает все. 5) Ошибка, если гвард сработал при обычном импорте.

## Plan

## Rollback

git checkout -- scripts/ tests/; bootstrap.

## Journal

- 2026-07-10T13:13:40Z [implementation] — AC verified: 1. ✓ Все 26 scripts/project_cli*.py отказывают при прямом запуске — test_direct_run_is_refused параметризован по glob, exit=2, stdout пуст. 2. ✓ Сообщение называет '.tausik/tausik' и имя модуля — test_refusal_names_the_module. 3. ✓ Импорт цел — test_module_still_imports по всем 26. 4. ✓ (негативный) Тест перебирает модули через glob, поэтому новый project_cli_*.py без гварда завалит прогон, а не проскочит. Проверено: до правки 'python scripts/project_cli.py skill sign /tmp/x' давал exit=0 и пустой вывод; после — exit=2 и текст в stderr. 5. ✓ (негативный) test_entrypoint_is_not_guarded: scripts/project.py (настоящая точка входа) по-прежнему отвечает 0 на --help. Расширил область против заявленной: находка 3.1 была про один project_cli.py, но гварда не было ни у одного из 26 модулей. Чинить один — оставить ту же ловушку на 25 других. Отказ вынесен в scripts/cli_entrypoint.py::refuse_direct_run, exit 2 (код ошибки использования у argparse). Прогон: tests/test_cli_entrypoint_guard.py — 54 passed.
