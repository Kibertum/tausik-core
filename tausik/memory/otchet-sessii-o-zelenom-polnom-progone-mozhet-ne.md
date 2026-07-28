---
slug: otchet-sessii-o-zelenom-polnom-progone-mozhet-ne
title: "Отчёт сессии о зелёном полном прогоне может не соответствовать действительности: test_mypy_clean красный на HEAD с сессии #147"
type: gotcha
tags:
  - baseline
  - handoff
  - mypy
  - verification
task: mcp-handlers-god-module-split
edges: []
---

Хендофф сессии #147 утверждал «Полный pytest: 6396 passed / 24 skipped / 0 failed / 0 errors (655 s), mypy Success 291 файл». Проверка сессии #148 показала, что это неверно: tests/test_mypy_clean.py::test_scripts_tree_is_mypy_clean КРАСНЫЙ на коммите cd0617f.

Доказано чисто, без правки рабочего дерева: git worktree --detach на HEAD плюс ТОТ ЖЕ venv дают те же 2 ошибки mypy — import-untyped на PyYAML в scripts/renar_conformance.py:327 и scripts/project_cli_renar.py:70. Пакеты в .tausik/venv не менялись с 03.05.2026 (проверено CreationTime в site-packages), оба renar-файла в рабочем дереве не тронуты. То есть красный не зависит ни от накопленного некоммитного батча, ни от среды, изменённой сессией #148.

Механика ловушки: PyYAML УСТАНОВЛЕН, но не несёт стабов и не помечен py.typed. Если бы пакета не было, mypy сказал бы import-not-found; раз он есть — import-untyped. Это ВАЖНО, потому что глобального ignore_missing_imports в pyproject нет, а override для одного модуля глушит обе категории сразу. Ставить types-PyYAML нельзя: venv намеренно без лишнего, и сам doctor проверяет «stdlib only».

СЛЕДСТВИЕ ДЛЯ РАБОТЫ: цифру полного прогона из чужого (и своего прошлого) хендоффа НЕ принимать как базовую линию. Базовую линию для «нет новых падений» брать замером на HEAD в отдельном worktree — это дёшево (одна команда) и, в отличие от прозы в хендоффе, фальсифицируемо. Связано с [[proksi-metrika-obyazana-vychitat-deloproizvodstvo]] и с задачей mypy-blind-to-harness-mcp-tree.
