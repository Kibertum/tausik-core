---
slug: cli-ops-residue-split-by-command
title: "Остаток project_cli_ops.py разрезать по командам — семейство уже имеет эту конвенцию"
status: planning
epic: arch-debt-post-18
story: adp18-module-boundaries
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Выделено из filesize-rejoin-cap-deformed-wrappers (решение #199), где замер показал: семейство project_cli_* содержит 26 модулей, и 24 из них названы ИМЕНЕМ КОМАНДЫ одним словом (adapt, aidd, config, doctor, drift, events, hygiene, key, receipt, renar, review, role, serve, skill, snippet, spec, stack, state, task, verify). Два выбивались: project_cli_ops.py и project_cli_extra.py, названные по остаточному признаку — «ops» не значит ничего, «extra» значит «что не влезло». Их строки документации ПЕРЕЧИСЛЯЛИ по 10 и 4 несвязанные команды вместо домена. Что это остаток гейта, а не архитектуры, записано в самих файлах: brain_cli_ops.py — «extracted from project_cli_ops for filesize gate», project_cli_events.py — «Kept out of project_cli_ops.py (400-line gate)», project_cli_metrics.py — «Extracted from project_cli_ops.py to keep it under the 400-line filesize gate». Родительская задача починила ТОЛЬКО два физически разорванных домена (cmd_metrics вернулась в project_cli_metrics.py, cmd_audit — в project_cli_audit.py, бывший _audit_extra), сознательно не трогая остальное: churn на CLI-поверхности перед капстоуном 1.8 при нулевой выгоде для релиза. Здесь доделать остаток. В project_cli_ops.py осталось 234 строки и 8 команд: cmd_hud, cmd_suggest_model, cmd_search, cmd_dead_end, cmd_explore, cmd_doc, cmd_run, cmd_session_recompute. В project_cli_extra.py — 368 строк и 4 команды: cmd_memory, cmd_update_claudemd, cmd_fts, cmd_gates. НЕ 1.8: это чистая архитектурная гигиена, ничего в релизе от неё не зависит.

## Acceptance Criteria

## Plan

## Rollback

## Journal
