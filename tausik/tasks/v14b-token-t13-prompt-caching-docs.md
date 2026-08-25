---
slug: v14b-token-t13-prompt-caching-docs
title: "B-token-T1.3: Verify Anthropic prompt caching enabled + docs"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/validate_prompt_caching.py (NEW), tests/test_validate_prompt_caching.py (NEW), tests/fixtures/sample_transcript_with_cache.jsonl (NEW), docs/en/architecture.md, docs/ru/architecture.md, docs/ru/troubleshooting.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/hooks/session_metrics.py (don't modify existing parser — keep validation separate per AC#1), MCP handlers, project_service.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T14:12:40Z"
---

## Goal

Anthropic prompt caching verified active in TAUSIK Claude flow + docs explain how to verify cache hits/misses. This task is a HARD prerequisite for v14b-baseline-token-metrics (otherwise measurements are noisy due to cache hit/miss skew).

## Acceptance Criteria

1. Validation script reads a sample API response and asserts both cache_creation_input_tokens and cache_read_input_tokens fields are parsed. 2. docs/en/architecture.md + docs/ru/architecture.md document where caching is applied (CLAUDE.md, system prompt, MCP tool descriptions, etc.) and which prompts get cache breakpoints. 3. docs/ru/troubleshooting.md explains how to verify cache hit rate (read API response, compare cache_read vs cache_creation). 4. CHANGELOG entry. 5. This task closes BEFORE v14b-baseline-token-metrics starts (dependency).

## Plan

[{"step": "Read Anthropic prompt-caching docs (already in claude-api skill knowledge) \u2014 confirm Claude Code's default caching behavior", "done": true}, {"step": "Locate where TAUSIK constructs prompts (skills, system prompt) \u2014 identify cache-breakpoint candidates", "done": true}, {"step": "Write validation script: parse sample API response usage block; assert cache fields present", "done": true}, {"step": "docs/en/architecture.md + docs/ru/architecture.md: section on caching strategy", "done": true}, {"step": "docs/ru/troubleshooting.md: how-to-verify cache hit rate", "done": true}, {"step": "CHANGELOG entry", "done": true}]

## Rollback

## Journal

- 2026-05-04T14:11:17Z [implementation] — Implementation done: scripts/validate_prompt_caching.py (parse_caching/classify/format_report/main, 4 exit codes), tests/test_validate_prompt_caching.py (11 tests covering parser/classifier/CLI), docs/{en,ru}/architecture.md "Prompt Caching" section (cacheable surfaces + invalidators + script usage), docs/{en,ru}/troubleshooting.md "Prompt caching not active" entry, CHANGELOG.md + CHANGELOG.ru.md bilingual Added entry. Tests 11/11 green; mypy clean on both new files.
- 2026-05-04T14:12:06Z [implementation] — AC verified: 1. ✓ scripts/validate_prompt_caching.py parses sample API response and asserts cache_creation_input_tokens + cache_read_input_tokens — covered by test_extracts_both_cache_fields, test_handles_top_level_usage, test_handles_missing_cache_fields, test_explicit_zero_cache_field_still_counted_as_present (tests/test_validate_prompt_caching.py) 2. ✓ docs/en/architecture.md + docs/ru/architecture.md document where caching applies (system prompt + tool schemas, CLAUDE.md, MCP tool descriptions, SKILL.md) and what invalidates prefix (esp. tausik_update_claudemd mid-session) 3. ✓ docs/en/troubleshooting.md + docs/ru/troubleshooting.md "Prompt caching not active" entry explains exit-code semantics + maps low/zero hit-rate symptoms to causes; provides the run command for verification 4. ✓ CHANGELOG.md ### Added + CHANGELOG.ru.md ### Добавлено bilingual entry 5. ✓ Closing this task before v14b-baseline-token-metrics — task_list status=planning will show the dependency available now
