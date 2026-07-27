---
slug: pereimenovanie-klyucha-geyta-steka-lomaet-testy
title: "Переименование ключа гейта/стека ломает тесты, хардкодящие имя — не верифай с --no-tests-expected"
type: gotcha
tags:
  - no-tests-expected
  - regression
  - rename
  - stack-gates
  - verify
task: fix-kubeconform-rename-fallout
edges: []
---

stack.json/gate/role реестры хардкодятся по ИМЕНИ в тестах (напр. tests/test_stack_iac.py параметризует ('kubeval','kubernetes')). Переименование ключа гейта (kubeval→kubeconform в stacks/kubernetes/stack.json) молча ломает эти тесты — DEFAULT_GATES/STACK_GATE_MAP выводятся из stack.json на импорте, старый ключ исчезает → KeyError/assert fail. Задача, сделавшая ренейм, закрылась ЗЕЛЁНОЙ, потому что верифала с --no-tests-expected (data-only декларация) и test_stack_iac.py вообще не прогонялся. Правило: при ренейме любого РЕЕСТРОВОГО ключа (gate/stack/role) — (1) `grep -rn '<old-key>' tests/` ПЕРЕД закрытием, (2) НИКОГДА не --no-tests-expected если для меняемого артефакта есть *_iac/registry/_test. Поймано только adversarial-ревью каждые-5-задач. [[doc-drift-fenced-illustrative]] — тот же класс «declaration вместо verification».
