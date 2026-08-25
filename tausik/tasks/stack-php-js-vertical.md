---
slug: stack-php-js-vertical
title: "PHP + JS/TS vertical — phpunit/pest + jest/vitest detection"
status: done
epic: enterprise-stack-agnostic
story: stack-verticals
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_config.py (phpunit + js-test gates)\ntests/test_stack_php_js.py (новый)"
scope_exclude: "scripts/gate_runner.py (resolver patterns — отложено)\nagents/skills/* (отдельно)\nscripts/* (other)"
relevant_files:
  - "scripts/project_config.py"
  - "scripts/default_gates.py"
  - "tests/test_stack_php_js.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:32:14Z"
---

## Goal

PHP: gate phpunit-or-pest. Auto-detect из composer.json scripts (предпочесть 'composer test' если есть, иначе vendor/bin/phpunit или vendor/bin/pest по presence). Laravel: подхватить tests/Unit/ + tests/Feature/. Resolver patterns: tests/<Name>Test.php + tests/Unit/* + tests/Feature/*. JS/TS: gate js-test. Auto-detect из package.json scripts (prefer 'npm test' если есть test script, иначе jest vs vitest по presence in deps). Resolver: <name>.test.ts/.spec.ts + __tests__/<name>.test.tsx. Both с stacks ограничением. Override через [tausik.verify] config для нестандартных setups (Bazel, Make, custom).

## Acceptance Criteria

- [ ] DEFAULT_GATES['phpunit'] с stacks=['php','laravel'], command='vendor/bin/phpunit', enabled=False
- [ ] DEFAULT_GATES['js-test'] с stacks=['javascript','typescript','react','next','vue','nuxt','svelte'], command='npm test --silent', enabled=False
- [ ] Documentation в gate description: упомянуть что override через [tausik.verify] config для composer/yarn/bun/pnpm runners
- [ ] tausik stack info php показывает phpunit + phpstan + phpcs
- [ ] tausik stack info typescript показывает js-test + tsc + eslint
- [ ] Negative scenarios: phpunit skipped на main.go (test); js-test skipped на main.py (test)
- [ ] Tests test_stack_php_js.py: (a) gates registered; (b) STACK_GATE_MAP integration; (c) stack info exposure; (d) cross-stack filtering

## Plan

## Rollback

## Journal

- 2026-04-25T12:32:13Z [implementation] — AC verified: 1. phpunit gate ✓ (test_phpunit_registered, test_in_stack_gate_map PASSED) 2. js-test gate ✓ (test_js_test_registered PASSED) 3. Override docs в descriptions ✓ (test_descriptions_mention_override PASSED) 4. tausik stack info php/typescript ✓ (TestStackInfo 2 PASSED) 5. Negative cross-stack filtering ✓ (TestStackFiltering 4 PASSED) 6. Tests test_stack_php_js.py 10/10 PASSED + 92/92 test_gates regression OK
