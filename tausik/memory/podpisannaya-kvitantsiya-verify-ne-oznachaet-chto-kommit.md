---
slug: podpisannaya-kvitantsiya-verify-ne-oznachaet-chto-kommit
title: "Подписанная квитанция verify НЕ означает, что коммит пройдёт: у commit пять гейтов, которых у verify нет"
type: gotcha
tags:
  - commit
  - gates
  - mypy
  - state-roundtrip
  - verify
task: verify-mypy-verify-dict
edges: []
---

ЗАМЕР, сессия #187-#188. Задача закрыта через `verify --task` с подписанной квитанцией (run #1831), а `gate_runner.py commit` через минуту дал ДВА блокирующих отказа на тех же файлах.

НАБОРЫ РАЗНЫЕ, СВЕРЕНО ВЫВОДОМ ОБЕИХ КОМАНД:
  verify (scope=manual): ruff, hadolint, pytest — и всё.
  commit: ruff, mypy, filesize, class_surface, memory_route, state_roundtrip, skill_spec_conformance, hadolint.

То есть у коммита ПЯТЬ гейтов, которых у verify нет: mypy, filesize, class_surface, memory_route, state_roundtrip. Ни pytest у коммита, ни mypy у verify.

ЧЕМ ЭТО КУСАЕТСЯ НА ПРАКТИКЕ. Оба сегодняшних отказа были настоящими и оба пришли из этой разницы: (1) mypy — непроаннотированный `out = {}` в новом тесте; (2) state_roundtrip — производное дерево tausik/ разошлось с БД по ЧУЖОМУ файлу задачи, потому что поле depends_on, введённое в 448d9b8, не досталось ровно одному файлу из 1412. Ни то, ни другое verify увидеть не мог.

ПРАВИЛО. «Задача закрыта по квитанции» и «изменение готово к коммиту» — РАЗНЫЕ утверждения, и первое не влечёт второго. Перед закрытием партии гонять `python scripts/gate_runner.py commit --files <staged>` отдельно, а не считать, что verify уже всё сказал.

ОТДЕЛЬНО ПРО state_roundtrip: он отказывается принимать ЧАСТИЧНЫЙ коммит производного дерева — «tausik/ matches the DB, but N change(s) are unstaged». Это делает дерево tausik/ атомарным для коммита и практически запрещает разбивать сессию на «продуктовый коммит» и «коммит бухгалтерии» по отдельности, если оба трогают tausik/.
