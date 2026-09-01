---
slug: cd-block-allow-base-dir
title: "Гейт записи: cd внутри команды переводит BLOCK в ALLOW через base_dir"
status: planning
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: write-gate-resolves-a-script-path-against-the-wrong-directory
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "tests/**"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

scripts/hooks/bash_write_parse.py:111-112 (_script_file_writes), через bash_write_gate.py: событие несёт cwd ДО выполнения команды, а _parse не отслеживает cd/pushd/env -C ВНУТРИ самой команды. Продемонстрировано сквозь реальный bash_write_gate.py: 'python helper.py' стоя в проекте — BLOCKED (rc=2); 'cd <project> && python helper.py' стоя в scratch-каталоге — ALLOWED (rc=0), хотя shell реально пишет в <project>/scripts/stolen.py. До этой правки project_dir был (случайно) верным корнем для этой формы команды; после правки base_dir неверен, файл не находится, fail-soft тихо возвращает [] без события supervision-degradation. Это чистый регресс от данного коммита для этой формы команды, а не только остаточный пробел.

## Acceptance Criteria

## Plan

## Rollback

## Journal
