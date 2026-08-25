---
slug: brain-search-proactive
title: "Proactive brain_search перед WebSearch/WebFetch"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/brain_search_proactive.py (new), tests/test_brain_search_proactive_hook.py (new), bootstrap/bootstrap_generate.py (+hook registration)"
scope_exclude: "scripts/brain_search.py (reused read-only), scripts/brain_config.py (reused read-only), WebFetch hook caching — это brain-webfetch-hook (PostToolUse, отдельная задача)"
relevant_files:
  - "scripts/hooks/brain_search_proactive.py"
  - "tests/test_brain_search_proactive_hook.py"
  - "bootstrap/bootstrap_generate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T10:54:38Z"
---

## Goal

PreToolUse hook на WebSearch/WebFetch: запускает brain_search_local по query. Если есть cache hit с fetched_at > now - ttl — возвращает кеш вместо сетевого запроса (deny + reason). TTL per-category из config.

## Acceptance Criteria

AC1: scripts/hooks/brain_search_proactive.py — новый PreToolUse хук на matcher 'WebSearch|WebFetch'.
AC2: Brain disabled (cfg.enabled=false) → exit 0 без side-effects.
AC3: Brain mirror DB отсутствует → exit 0 (graceful skip).
AC4: WebSearch с query где есть свежий cache hit (fetched_at > now - ttl_web_cache_days) → exit 2, stderr показывает [notion_page_id] url, fetched_at, и hint как override'нуть.
AC5: WebFetch с url — точный URL match ИЛИ FTS на prompt в web_cache → exit 2 при свежем кеше.
AC6: Stale cache (fetched_at старше ttl) → exit 0 (allow net fetch).
AC7: Нет совпадений → exit 0.
AC8: Bypass marker 'refresh: web_cache' в последнем user-turn → exit 0 (override).
AC9: Зарегистрирован в bootstrap_generate.generate_settings_claude + generate_settings_cursor.
AC10: tests/test_brain_search_proactive_hook.py — покрыть AC2-AC8 + edge cases (malformed stdin, missing fields).
AC11: ruff + mypy scripts/ clean.
AC12: pytest tests/test_brain_search_proactive_hook.py -v → 100% pass.

## Plan

## Rollback

## Journal

- 2026-04-24T10:44:37Z [implementation] — AC verified: 1. scripts/hooks/brain_search_proactive.py создан ✓ 2. test_brain_disabled_exits_zero ✓ 3. test_mirror_db_missing_exits_zero + test_no_tausik_db_exits_zero ✓ 4. test_websearch_fts_fresh_hit_blocks: stderr содержит BLOCKED, page_id, url, refresh: web_cache ✓ 5. test_webfetch_exact_url_match_blocks + test_webfetch_url_mismatch_but_prompt_fts_blocks ✓ 6. test_stale_cache_allows_fetch ✓ 7. test_no_cache_hit_allows_fetch ✓ 8. test_bypass_marker_allows_fetch ✓ 9. test_bootstrap_generate_registers_brain_search_proactive (Cursor scoped out — нет hook runtime) ✓ 10. 20/20 tests pass ✓ 11. ruff + mypy scripts/ clean ✓ 12. pytest → 20/20 pass ✓
- 2026-04-24T10:44:39Z [implementation] — Latent bug discovered: get_brain_mirror_path() при передаче merged brain dict возвращает DEFAULT_BRAIN path. Тот же баг в brain_runtime.py:41. Завёл отдельный defect brain-config-mirror-path-contract. В hook'е обошёл прямым чтением local_mirror_path из cfg + expand, чтобы не разводить side-эффекты.
- 2026-04-24T10:44:41Z [implementation] — Regression check: 96/96 pass (test_memory_pretool_block_hook, test_memory_posttool_audit_hook, test_bootstrap_generate_mcp, test_brain_classifier, test_service_knowledge_decide). Новый PreToolUse хук в settings.json встал между bash_firewall и git_push_gate, не конфликтует с existing matchers.
