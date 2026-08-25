---
slug: gates-multi-lang
title: "Multi-language quality gates with stack auto-detection"
status: done
epic: frai-v24
story: multi-lang-gates
complexity: medium
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
completed_at: "2026-03-26T14:23:36Z"
---

## Goal

Gates для TS/JS/Go/Rust/Java/PHP auto-enable при обнаружении стека, gate_runner поддерживает все стеки из references/stacks/

## Acceptance Criteria

1. project_config.py содержит gates для tsc, eslint, go-vet, golint, cargo-check, clippy, phpstan, phpcs, javac, ktlint. 2. Gates auto-enable при обнаружении стека в .frai/config.json. 3. gate_runner корректно запускает gates для обнаруженного стека. 4. Gates для необнаруженных стеков остаются disabled. 5. frai gates status показывает статус по стекам. 6. Тесты покрывают auto-enable и multi-stack scenarios.

## Plan

[{"step": "project_config: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c gates \u0434\u043b\u044f Go, Rust, Java/Kotlin, PHP", "done": true}, {"step": "\u041c\u0430\u043f\u043f\u0438\u043d\u0433 stack\u2192gates \u0432 project_config (python\u2192pytest+ruff, typescript\u2192tsc+eslint, etc)", "done": true}, {"step": "gate_runner: auto-enable gates \u043f\u043e \u0441\u0442\u0435\u043a\u0430\u043c \u0438\u0437 config", "done": true}, {"step": "bootstrap: \u043f\u0440\u0438 detect_stacks \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0435 gates", "done": true}, {"step": "stacks/init/*.yaml: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c gates \u0441\u0435\u043a\u0446\u0438\u044e \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0441\u0442\u0435\u043a\u0430", "done": true}, {"step": "frai gates status: \u0433\u0440\u0443\u043f\u043f\u0438\u0440\u043e\u0432\u043a\u0430 \u043f\u043e \u0441\u0442\u0435\u043a\u0430\u043c", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: auto-enable, multi-stack, no false activation", "done": true}]

## Rollback

## Journal
