---
slug: v2-global-mcp
title: "TAUSIK 2.0 — глобальная установка вместо сабмодуля (breaking)"
status: active
---

Major-веха 2.0. Ломающий переход: установка либы один раз (pipx/uv), user-scope MCP вместо per-project копий .claude/scripts|mcp, в проекте остаётся только .tausik/ (db+config+keys). Гейт-спайк gmcp-spike-roots определяет первичный механизм резолва (roots vs pointer) и launch-модель Claude Code — до его закрытия gmcp-server-multitenant не стартовать. Отложено из v1.5.
