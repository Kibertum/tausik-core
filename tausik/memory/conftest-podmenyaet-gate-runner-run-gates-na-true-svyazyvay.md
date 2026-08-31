---
slug: conftest-podmenyaet-gate-runner-run-gates-na-true-svyazyvay
title: "conftest подменяет gate_runner.run_gates на (True, []) — связывай имя на импорте модуля"
type: gotcha
tags:
  - conftest
  - gates
  - schema
  - tests
task: claudemd-state-gate-reports-passed-when-it-could-not-run
edges: []
---

tests/conftest.py держит autouse-фикстуру _mock_run_gates, которая на КАЖДОМ тесте патчит gate_runner.run_gates возвратом (True, []) — защита от pytest-в-pytest. Тест, вызывающий gate_runner.run_gates(...) из тела, меряет МОК и зеленеет ни на чём: в #193 это дало len(results)==0 и увело на ложный след.

Штатный выход, уже применённый в tests/test_gate_registry.py и tests/test_gates.py: связать имя на ИМПОРТЕ модуля — `from gate_runner import run_gates` в шапке файла, до того как фикстура подменит атрибут модуля.

Рядом, в ту же цену: версия схемы лежит в таблице `meta`, ключ 'schema_version' (backend_init.init_schema), а НЕ в таблице schema_version. Фикстура, пишущая не туда, не поднимет охранник версии — БД молча инициализируется с нуля и тест меряет другой сценарий. DDL таблицы gate_runs брать импортом backend_schema_gate_runs.GATE_RUNS_SQL, а не перепечатывать: свой gate_runs в тесте не доказывает ничего о настоящем.
