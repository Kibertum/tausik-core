---
slug: migrate-native
title: "Migrate go/rust/java/kotlin/swift/flutter"
status: done
epic: v16-plugin-arch-and-docs
story: migrate-builtins
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/{go,rust,java,kotlin,swift,flutter}/* (NEW), agents/stacks/{go,rust,java,kotlin,swift,flutter}.md (move)"
scope_exclude: "scripts/*, bootstrap/*"
relevant_files:
  - "stacks/go/stack.json"
  - "stacks/rust/stack.json"
  - "stacks/java/stack.json"
  - "stacks/kotlin/stack.json"
  - "stacks/swift/stack.json"
  - "stacks/flutter/stack.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:47:04Z"
---

## Goal

Create stacks/{go,rust,java,kotlin,swift,flutter}/stack.json + guide.md. Migrate go-vet/golangci-lint/go-test, cargo-check/clippy/cargo-test, javac, ktlint per-stack. Empty gates field for swift/flutter (no built-in gates yet, intentional).

## Acceptance Criteria

1. stacks/{go,rust,java,kotlin,swift,flutter}/stack.json + guide.md созданы.
2. go/stack.json owns gates: go-vet, golangci-lint, go-test (stacks=[go]).
3. rust/stack.json owns: cargo-check, clippy, cargo-test (stacks=[rust]).
4. java/stack.json owns: javac (stacks=[java]).
5. kotlin/stack.json owns: ktlint (stacks=[kotlin]).
6. swift/stack.json + flutter/stack.json — без своих гейтов (DEFAULT_GATES не имеет stacks-фильтров для них).
7. agents/stacks/{go,rust,java,kotlin,swift,flutter}.md → stacks/<name>/guide.md.
8. StackRegistry загружает все стэки errors=[]; pytest tests/test_stack_registry.py + tests/test_gates.py: 0 регрессий.

## Plan

## Rollback

## Journal

- 2026-04-25T16:47:04Z [implementation] — AC verified: 1. ✓ stacks/{go,rust,java,kotlin,swift,flutter}/{stack.json,guide.md}. 2. ✓ go owns go-vet/golangci-lint/go-test (gates_for=go-test,go-vet,golangci-lint). 3. ✓ rust owns cargo-check/clippy/cargo-test. 4. ✓ java owns javac. 5. ✓ kotlin owns ktlint. 6. ✓ swift+flutter без своих гейтов. 7. ✓ Guides перемещены. 8. ✓ StackRegistry: 17 стэков загружаются errors=[].
