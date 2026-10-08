---
slug: tri-oshibki-mypy-v-tests-conftest-py-artefakt-vyzova-geyta
title: "Три ошибки mypy в tests/conftest.py — артефакт ВЫЗОВА гейта, а не типы: полный прогон зелёный на 341 файле"
type: gotcha
tags:
  - false-positive
  - gates
  - measurement
  - mypy
task: null
edges: []
---

ИСПРАВЛЯЕТ УТВЕРЖДЕНИЕ, ПЕРЕДАВАВШЕЕСЯ ИЗ СМЕНЫ В СМЕНУ: «mypy на коммит-гейте красный тремя ошибками в tests/conftest.py:71/207/212 — дорелизные». Формулировка «дорелизные ошибки» неверна и вводит в заблуждение: чинить в типах там нечего.

ЗАМЕР (сессия #191):
  python -m mypy                      -> Success: no issues found in 341 source files
  python -m mypy tests/conftest.py    -> 3 errors: import-not-found "service_gates" (:71), import-not-found "backend_schema" (:207), no-any-return (:212)

ПРИЧИНА: конфигурация в pyproject.toml задаёт СВОЙ набор источников, и tests/ в него не входит — полный прогон conftest.py не проверяет ВООБЩЕ. Гейт `mypy` объявлен как `mypy {files}`, то есть подставляет ИЗМЕНЁННЫЕ файлы аргументами. Переданный явным аргументом conftest.py проверяется вне контекста пакета, поэтому mypy не находит service_gates и backend_schema — модули, которые в штатном прогоне резолвятся.

СЛЕДСТВИЕ: гейт краснеет ровно тогда, когда в коммит попал tests/conftest.py, и краснеет на пустом месте. Прогон гейтов триггера commit на коммите 550326e: mypy PASS — conftest в коммит не входил.

ЧТО ЭТО ЗНАЧИТ ДЛЯ БУДУЩЕЙ СМЕНЫ: не пытайся «починить типы в conftest». Настоящий вопрос — почему гейт, объявленный как `mypy {files}`, меряет иначе, чем `mypy` по конфигу проекта; это дефект СПОСОБА ВЫЗОВА гейта. Тот же вопрос стоит задать любому гейту вида `<инструмент> {files}`.

Связано: [[commit-hooks-are-dead-hookspath-points-at-a-missing-repo]] — на этом дереве гейт mypy на коммите не исполняется вовсе.
