---
slug: migrate-frontend
title: "Migrate react/next/vue/nuxt/svelte/typescript/javascript"
status: done
epic: v16-plugin-arch-and-docs
story: migrate-builtins
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/{react,next,vue,nuxt,svelte,typescript,javascript}/* (NEW), agents/stacks/{react,next,vue,nuxt,svelte,typescript,javascript}.md (move)"
scope_exclude: null
relevant_files:
  - "stacks/typescript/stack.json"
  - "stacks/javascript/stack.json"
  - "stacks/react/stack.json"
  - "stacks/next/stack.json"
  - "stacks/vue/stack.json"
  - "stacks/nuxt/stack.json"
  - "stacks/svelte/stack.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:46:17Z"
---

## Goal

Create stacks/{react,next,vue,nuxt,svelte,typescript,javascript}/stack.json + guide.md. Move signatures + tsc/eslint/js-test gates with proper stacks-filter migration. Multi-stack gates (e.g. eslint applies to 5 stacks) — split into per-stack declarations vs shared gate (architectural decision: gate lives under primary stack, listed-as-applicable in others).

## Acceptance Criteria

1. stacks/{react,next,vue,nuxt,svelte,typescript,javascript}/stack.json + guide.md созданы; detect/extensions/filenames соответствуют STACK_SIGNATURES + _EXT_TO_STACKS + _FILENAME_TO_STACKS.
2. typescript/stack.json owns gate tsc (stacks=[typescript,react,next,vue,nuxt,svelte]).
3. javascript/stack.json owns gates eslint (stacks=[typescript,javascript,react,next,vue,nuxt,svelte]) + js-test (same scope).
4. agents/stacks/{react,next,vue,nuxt,svelte,typescript,javascript}.md → stacks/<name>/guide.md.
5. StackRegistry.load_builtin('stacks') загружает все 11 (4 python + 7 frontend), errors=[].
6. pytest tests/test_stack_registry.py + tests/test_gates.py: 0 регрессий.
7. JSON-валидны + validate_decl=[]/all.

## Plan

## Rollback

## Journal

- 2026-04-25T16:46:16Z [implementation] — AC verified: 1. ✓ 7 stacks/<name>/{stack.json,guide.md} созданы (typescript, javascript, react, next, vue, nuxt, svelte). 2. ✓ typescript/stack.json owns tsc gate (stacks=[typescript,react,next,vue,nuxt,svelte]). 3. ✓ javascript/stack.json owns eslint+js-test (stacks=[ts,js,react,next,vue,nuxt,svelte]). 4. ✓ guides перемещены mv-bash циклом. 5. ✓ StackRegistry: 11 стэков (4 python + 7 frontend) загружаются errors=[]. 6. ✓ pytest регрессий нет (107 проходят). 7. ✓ JSON валидны, validate_decl=[] для всех 7 (smoke через registry).
