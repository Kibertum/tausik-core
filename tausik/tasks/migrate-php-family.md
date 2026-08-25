---
slug: migrate-php-family
title: "Migrate php/laravel/blade"
status: done
epic: v16-plugin-arch-and-docs
story: migrate-builtins
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/{php,laravel,blade}/* (NEW), agents/stacks/{php,laravel,blade}.md (move)"
scope_exclude: "scripts/*, bootstrap/*"
relevant_files:
  - "stacks/php/stack.json"
  - "stacks/laravel/stack.json"
  - "stacks/blade/stack.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:47:26Z"
---

## Goal

Create stacks/{php,laravel,blade}/stack.json + guide.md. Migrate phpstan/phpcs/phpunit. Blade extends laravel (Blade is template engine in Laravel projects).

## Acceptance Criteria

1. stacks/{php,laravel,blade}/{stack.json,guide.md}.
2. php/stack.json owns phpstan/phpcs/phpunit (stacks=[php,laravel]).
3. laravel — без своих gates (наследует через 'stacks' field на php gates).
4. blade — без своих gates, extensions=[.blade.php].
5. agents/stacks/{php,laravel,blade}.md → stacks/<name>/guide.md.
6. StackRegistry загружает 20 стэков errors=[].

## Plan

## Rollback

## Journal

- 2026-04-25T16:47:25Z [implementation] — AC verified: 1. ✓ stacks/{php,laravel,blade}/{stack.json,guide.md}. 2. ✓ php owns phpstan/phpcs/phpunit (stacks=[php,laravel]). 3. ✓ laravel — no own gates (inherits via stacks field). 4. ✓ blade extensions=[.blade.php], detect glob *.blade.php. 5. ✓ Guides перемещены. 6. ✓ Registry: 20 стэков errors=[].
