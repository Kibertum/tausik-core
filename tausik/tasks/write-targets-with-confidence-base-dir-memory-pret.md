---
slug: write-targets-with-confidence-base-dir-memory-pret
title: "write_targets_with_confidence не получил base_dir: memory_pretool_block читает скрипт из чужого дерева"
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
  - "scripts/hooks/shell_channel.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/**"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

shell_channel.write_targets_with_confidence (scripts/hooks/shell_channel.py:122-131) не получила довод base_dir в отличие от write_targets, поэтому memory_pretool_block.py:151 — единственный вызывающий этой точки — по-прежнему резолвит путь скрипта из _script_file_writes от CLAUDE_PROJECT_DIR, а не от каталога оболочки. Замерено сквозным прогоном: команда, запущенная в чужой выгрузке и пишущая в защищённый домашний memory-синк, ПРОПУЩЕНА (rc=0), потому что вместо реального скрипта был прочитан одноимённый безобидный файл проекта. Это тот же дефект, который данная задача заявляет закрытым — открыт на втором гейте, читающем тот же код.

## Acceptance Criteria

## Plan

## Rollback

## Journal
