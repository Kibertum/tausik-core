---
slug: opencode-imena-tulov-i-kontrakt-plagina-provereno-po
title: "OpenCode: имена тулов и контракт плагина — проверено по первоисточнику, не угадано"
type: gotcha
tags:
  - enforcement
  - opencode
  - plugin
  - qg0
task: opencode-qg0-plugin
edges: []
---

Факты с opencode.ai/docs (tools + plugins), сверено при написании harness/opencode/plugins/tausik-qg0.js:

1. ПИШУЩИЕ тулы: `write`, `edit`, `apply_patch`. Именно `apply_patch` — тула с именем `patch` НЕ существует. Гейт по «patch» был бы мёртвым кодом, который выглядит как принуждение.
2. `todowrite` пишет todo-лист, а не репозиторий — гейтить его не надо. `bash` не гейтим сознательно: заблокировав его, мы заблокируем саму команду `tausik task start`, которой агент снимает блокировку (та же логика в матчере Claude Code).
3. Read-only: `read`, `grep`, `glob`, `lsp`, `skill`, `webfetch`, `websearch`, `question`, `bash`.
4. Каталог плагинов: `.opencode/plugins/` (мн.ч.), глобальный — `~/.config/opencode/plugins/`. Ключ `plugin` в конфиге — только для npm-пакетов.
5. Контракт: `export const X = async ({ project, client, $, directory, worktree }) => ({ "tool.execute.before": async (input, output) => {...} })`. У input есть `input.tool`, у output — `output.args` (мутабельно: так дока escape-ит bash-команду).
6. ОТМЕНА вызова тула — через `throw new Error(...)` из хука. Отдельного «deny»-API в доке нет; официальный пример защиты .env именно бросает ошибку.
7. Плагин обязан работать БЕЗ npm-установки: ноль import/require, типы — только JSDoc. Импорт @opencode-ai/plugin (даже type-only) = ERR_MODULE_NOT_FOUND и падение всего prompt-цикла.

Проверять семантику плагина можно под Node (bun не нужен): плагин намеренно не зависит ни от чего, кроме глобала `process`, а отсутствие глобала `Bun` трактует как «подписи БД нет» (см. решение #133).
