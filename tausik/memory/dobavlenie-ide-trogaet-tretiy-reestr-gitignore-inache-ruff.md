---
slug: dobavlenie-ide-trogaet-tretiy-reestr-gitignore-inache-ruff
title: "Добавление IDE трогает ТРЕТИЙ реестр — .gitignore, иначе ruff идёт линтить чужой вендоренный код"
type: gotcha
tags:
  - bootstrap
  - gitignore
  - ide
  - opencode
  - ruff
task: opencode-ide-support
edges: []
---

Память #184 говорит про ДВА реестра IDE (bootstrap-time IDE_DIRS vs runtime ide_utils.IDE_REGISTRY). При добавлении opencode вылез третий, неявный: **.gitignore**.

Что произошло: добавил ".opencode" в IDE_DIRS + SCAFFOLD_IDES, прогнал `bootstrap --ide all` — появился каталог .opencode/ с развёрнутой копией скриптов, включая вендоренный сторонний код (scripts/vendor_seo/). Тест tests/test_ble001_enforced.py гоняет ruff по всему дереву и опирается на то, что «ruff уважает .gitignore → развёрнутые IDE-каталоги пропускаются». В .gitignore ".opencode/" не было → ruff впервые залез в .opencode/scripts/vendor_seo/ и завалил сборку на BLE001 в ЧУЖОМ коде, к моим правкам отношения не имеющем.

Чек-лист при добавлении IDE (все четыре места):
1. bootstrap_config.IDE_DIRS + SCAFFOLD_IDES
2. bootstrap.bootstrap_ide — ветка диспетчера (гард: tests/test_scaffold_dispatch_backed.py)
3. scripts/ide_utils.IDE_REGISTRY + detect_ide
4. **.gitignore** — каталог .<ide>/ И любой генерируемый корневой конфиг с машинно-специфичными путями (для opencode это opencode.json: абсолютные пути там неизбежны, т.к. OpenCode не раскрывает переменные рабочей папки).

Симптом, по которому узнать: полный pytest падает в тестах, которые СКАНИРУЮТ ДЕРЕВО (ble001, filesize, docs-sync), а не в тестах твоей фичи. Не лечи чужой код — проверь .gitignore.

Побочно: функция диспетчера в bootstrap.py называется bootstrap_ide, а НЕ run_for_ide (в старых ТЗ/AC встречается неверное имя).
