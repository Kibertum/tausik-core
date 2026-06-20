---
title: "v1.5 — Cursor MCP integration rework"
subtitle: "Backlog note (TAUSIK dogfooding, Cursor 3.2.x / Windows)"
lang: en
date: 2026-05-08
status: backlog
---

# v1.5 — Cursor MCP integration rework

## Why a dedicated track

v1.4 added **`"type": "stdio"`** to generated `.mcp.json` and `.cursor/mcp.json`, matching Cursor docs for stdio MCP. That does **not** resolve the observed behaviour: TAUSIK tools still do not reach the Composer / workspace **`mcps/`** mirror path that lists MCP servers for the agent tool surface.

The **bootstrap or Python server being broken** hypothesis is **not supported** here: venv, `mcp` import, `.cursor/scripts/`, and a manual `server.py` launch do not show an immediate crash.

## Findings (2026-05-08)

### `Mcp FileSystem Writer.log` (primary)

On each window reload:

1. `cursor_mcp_lease_server_status` lists **four** servers (including `project-0-claude-tausik-project`).
2. `cursor_mcp_lease_snapshot_store` then lists **only `cursor-ide-browser`**.
3. `fetchAndWrite: lease returned 26 tools across 1 clients` — only the browser client is written.

So project stdio servers are **visible in lease status** but **not included in the FS-writer snapshot** that feeds the agent tool filesystem mirror.

### `workbench.mcp.oauth.log`

Project entries show **`disconnected`**; browser shows **`connected`**. This channel is **OAuth-oriented**; treat **`disconnected` for raw stdio** as **non-authoritative** for “process failed”.

### Historical contrast (2026-05-06)

Global **`user-*`** servers, when healthy, **did** appear in `cursor_mcp_lease_snapshot_store` with large tool counts. So stdio **can** flow through snapshot — **project-prefixed** servers behave differently in observed logs.

## v1.5 goals (minimum)

1. Maintain a **host contract matrix**: Cursor docs promise vs actual FS mirror behaviour per release.
2. Explore mitigations: **HTTP/SSE bridge**, **Cursor Extension MCP registration**, **out-of-IDE MCP handshake diagnostic script**, **upstream Cursor issue** with repro + FileSystem Writer excerpts (no secrets).
3. User docs: **Composer vs CLI** without mandating global `~/.cursor/mcp.json` where project policy forbids it.

## Regression guards

- `.tausik/tausik` CLI remains the **supported** full workflow if MCP is unavailable.
- No bootstrap test regressions; no secrets committed.

RU mirror: [`docs/ru/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md`](/ru/docs/research/tausik-1.5-mcp-cursor-rework-2026-05-08).
