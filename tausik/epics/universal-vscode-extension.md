---
slug: universal-vscode-extension
title: "Universal TAUSIK VSCode Extension (multi-host, auto-updating)"
status: done
---

One marketplace-delivered, auto-updating extension that hosts the TAUSIK framework code ONCE (replacing per-project vendored .claude/ copies + .tausik-lib submodule), leaving only .tausik/ (SQLite db + config) per project. Eliminates manual per-project re-bootstrap on every framework update. Works across enforcement-capable hosts (Claude Code, Qwen Code, Cursor) with model-by-subscription on both axes: Claude (Max/Pro via local Claude Code shell-out) and GLM (z.ai Coding Plan). Research swarm (session #102) established: MCP server is the harness-agnostic universal spine; skills live in .claude/skills read by both Claude Code and Kilo; two-axis design (host x model-family, Decision #119); GLM-by-subscription works via Anthropic-compatible endpoint and is DECOUPLED from the extension (available today via env vars). Enforcement tiers by hook dialect: Claude-contract (Claude Code + Qwen, zero work) / Cursor hooks.json (adapter needed) / Kilo (advisory only). Host priority: Claude Code (MVP) -> Qwen -> Cursor -> Kilo(advisory).
