---
slug: opencode-shema-konfiga-i-pochemu-agenty-vydumyvayut
title: "OpenCode: схема конфига и почему агенты выдумывают интеграцию TAUSIK"
type: gotcha
tags:
  - config
  - ide
  - opencode
  - qg0
  - supply-chain
task: fix-opencode-docs-overclaim
edges: []
---

Факты по opencode (SST, npm-пакет `opencode-ai`, НЕ `@anthropic-ai/opencode`), взяты из официальной доки opencode.ai:

1. `opencode.json` → `tools` принимает ТОЛЬКО boolean: `{"bash": false}`. Объект (`{"qg0": {"module": "..."}}`) валит старт с ConfigInvalidError.
2. Кастомные тулы/хуки — это ПЛАГИНЫ, каталог `.opencode/plugins/` (мн. число!). Singular `.opencode/plugin/` = плагин молча не грузится (на этом уже ловились: gastown#1614). Ключ `plugin` в конфиге — для npm-пакетов.
3. Хук `tool.execute.before` = точный аналог PreToolUse в Claude Code → это правильное место для принуждения QG-0 (наш scripts/hooks/task_gate.py).
4. `AGENTS.md`: «first matching file wins» — файлы НЕ объединяются. Если у пользователя свой AGENTS.md, наш не загрузится НИКОГДА.
5. Ключ `instructions` (массив путей/глобов): «All instruction files are combined with your AGENTS.md files» — ДОПОЛНЯЕТ, не вытесняет. Это единственный неконфликтный способ доставить правила TAUSIK в чужой проект.
6. MCP: `mcp.<name> = {type:"local", command:[...], environment:{}, enabled:true}`.

ПЕРВОПРИЧИНА инцидента у пользователя (BiziBox): дока TAUSIK объявляла OpenCode «поддерживаемым», а ветки bootstrap не было. Агент увидел разрыв «поддерживается, но ничего не настроено» и закрыл его импровизацией: выдумал tools.qg0 и .opencode/tools/qg0.ts с импортом @opencode-ai/plugin → ConfigInvalidError + ERR_MODULE_NOT_FOUND.

УРОК (шире opencode): заявленная в доке поддержка без кода — не безобидная неточность. Она АКТИВНО провоцирует агента дописать недостающее наугад. Отсюда гард tests/test_docs_no_fake_npm_packages.py: колонка Scaffolded сверяется с bootstrap_config.SCAFFOLD_IDES.
