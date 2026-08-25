---
slug: stack-go-rust-vertical
title: "Go + Rust vertical — test runners + resolver patterns"
status: done
epic: enterprise-stack-agnostic
story: stack-verticals
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py (добавить go-test, cargo-test gates)\nscripts/gate_runner.py (resolve_test_files_for_relevant Go/Rust fallback — optional, можно отложить)\ntests/test_stack_go_rust.py (новый)"
scope_exclude: "bootstrap/* (detection уже работает — не трогаем)\nagents/skills/* (отдельно)\nreal Go/Rust subprocess execution (gate command-strings, не реальный запуск)"
relevant_files:
  - "scripts/project_config.py"
  - "tests/test_stack_go_rust.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:29:41Z"
---

## Goal

Go: gate go-test command 'go test ./<pkg>/...' scoped по relevant_files (derive package paths). Detection from go.mod presence. Resolver pattern '*_test.go' (same package, не subdir). Rust: gate cargo-test command 'cargo test --package <crate>' scoped. Detection from Cargo.toml. Resolver patterns: tests/*.rs (integration) + inline 'mod tests' (unit, can't easily scope — fallback на full crate). Both gates с stacks=['go'] / stacks=['rust'] restriction. Tests: Go project с *_test.go matched + run; Rust project с tests/ matched + run; Python project пропускает оба.

## Acceptance Criteria

- [ ] DEFAULT_GATES['go-test']: command='go test ./...' (full module) с stacks=['go']; trigger=['task-done']; severity='block'; enabled=False (auto-enable через bootstrap detect)
- [ ] DEFAULT_GATES['cargo-test']: command='cargo test' с stacks=['rust']; trigger=['task-done']; enabled=False
- [ ] go-test и cargo-test попадают в STACK_GATE_MAP['go'] и STACK_GATE_MAP['rust'] соответственно
- [ ] resolve_test_files_for_relevant получает stack-aware fallback: для Go — `*_test.go` рядом с .go (same dir); для Rust — `tests/*.rs` integration + return empty для inline `mod tests`
- [ ] Detection: bootstrap detect_stacks (если не done) — добавить go.mod → 'go' detection и Cargo.toml → 'rust'; если уже есть — verify (читаем существующий код)
- [ ] tausik stack info go показывает go-test и go-vet; tausik stack info rust показывает cargo-test, cargo-check, clippy
- [ ] Negative scenarios: pytest skipped на main.go (verified в gate-stack-aware-dispatch); go-test skipped на main.py (test); Python tests остаются зелёные
- [ ] Tests test_stack_go_rust.py: (a) gates есть в DEFAULT_GATES; (b) STACK_GATE_MAP integration; (c) stack info вывод; (d) backwards compat — Python tests не тригаются

## Plan

## Rollback

## Journal

- 2026-04-25T12:29:40Z [implementation] — AC verified: 1. DEFAULT_GATES['go-test'] с stacks=['go'], trigger task-done, severity block ✓ (test_go_test_in_defaults PASSED) 2. DEFAULT_GATES['cargo-test'] с stacks=['rust'] ✓ (test_cargo_test_in_defaults PASSED) 3. STACK_GATE_MAP['go'] и ['rust'] содержат test gates ✓ (test_in_stack_gate_map PASSED) 4. tausik stack info go показывает go-test+go-vet ✓ (test_go_info_lists_test_runner PASSED) 5. tausik stack info rust показывает cargo-test+cargo-check+clippy ✓ (test_rust_info_lists_test_runner PASSED) 6. resolver Go/Rust fallback — отложено как dead end (Python-flavoured resolver достаточен для этой итерации, scoped tests Go/Rust = follow-up) 7. Negative scenarios: go-test skipped на main.py ✓ (test_go_test_skipped_for_python_files PASSED); cargo-test на main.py skipped ✓; pytest unaffected ✓ 8. Tests test_stack_go_rust.py 10/10 PASSED + test_gates 82/82 PASSED
