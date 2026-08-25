---
slug: v15-prep-cursor-mcp-stdio-type
title: "v1.5 prep: add type:stdio to Cursor MCP stdio transport entries"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T12:20:54Z"
---

## Goal

Закоммитить уже сделанные изменения в bootstrap_generate/bootstrap_qwen + tests + CHANGELOG + research, готовящие v1.5 Cursor MCP rework

## Acceptance Criteria

(1) bootstrap_generate.py + bootstrap_qwen.py применяют helper _stdio_mcp_server для 6 MCP server entries (3 Claude + 3 Qwen) с type:stdio. (2) tests/test_bootstrap_{generate_mcp,qwen}.py содержат assert entry['type']=='stdio' и проходят (pytest зелёный). (3) CHANGELOG.md + CHANGELOG.ru.md содержат [Unreleased] → Planned (v1.5) с пояснением и ссылками на research-документы. (4) Research-документы по обоим локалям закоммичены. (5) Git-коммит атомарный, без CLAUDE.md (dynamic) и без site/Dockerfile/.gitlab-ci.yml. (6) Ошибка: коммит не должен случайно затянуть незакоммиченные правки сайта или CLAUDE.md dynamic block — staging проверен через git diff --cached перед commit.

## Plan

## Rollback

## Journal

- 2026-05-15T12:20:21Z [implementation] — commit 98902b4 made, 8 files, 166+/36-, mypy clean, pytest 10/10 green
- 2026-05-15T12:20:53Z [implementation] — AC verified: (1) ✓ helper _stdio_mcp_server применён в 3 Claude generation sites (bootstrap_generate.py) + 3 Qwen sites (bootstrap_qwen.py через import). (2) ✓ tests/test_bootstrap_{generate_mcp,qwen}.py содержат 4 новых assert type=='stdio', pytest 10/10 passed. (3) ✓ CHANGELOG.md+ru.md содержат [Unreleased] Planned (v1.5) c корректными ссылками. (4) ✓ research докуметы в обеих локалях добавлены через create mode 100644. (5) ✓ Атомарный коммит 98902b4: 8 файлов, без site/CLAUDE.md. (6) ✓ git diff --cached проверен перед commit — site/Dockerfile/.gitlab-ci.yml остались untracked.
