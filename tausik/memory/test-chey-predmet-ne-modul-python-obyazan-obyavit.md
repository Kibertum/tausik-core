---
slug: test-chey-predmet-ne-modul-python-obyazan-obyavit
title: "Тест, чей предмет не модуль Python, обязан объявить CROSSCUTTING_SCOPE"
type: convention
tags: []
task: ci-does-not-run-on-the-release-branch
edges: []
---

Файл CI, конфиг, YAML не совпадает ни с одним basename и никем не импортируется, поэтому НИКАКОЕ изменение исходников не выберет такой тест, и scoped-прогон молча его пропустит. Ловится только полной лентой, тестом test_crosscutting_registry.py::TestInvisibleToEveryEdge — на Windows scoped-набор этого НЕ показывает. Проверка обратная: verify --relevant-files с этим файлом должен ВЫБРАТЬ твой тест.
