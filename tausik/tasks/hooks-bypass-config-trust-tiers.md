---
slug: hooks-bypass-config-trust-tiers
title: "Два хука читают config.json сырым json.load в обход трастовых тиров — user/managed настройки молча игнорируются"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "NEW tausik_utils.load_effective_config; edit scripts/hooks/session_cleanup_check.py (_session_warn_min) + scripts/hooks/tool_output_truncation_nudge.py (_resolve_threshold); tests for both hooks; CHANGELOG.md + CHANGELOG.ru.md. NOTE: task originally cited session_cleanup_check.py:31-38 + tool_output_truncation_nudge.py:46-55 — confirmed correct."
scope_exclude: "DEFERRED (the task lumped these in — out of scope, separate steps): unifying the two config-path sources (tausik_utils.tausik_config_path vs project_config.get_config_path); the three .tausik dir resolvers; the TAUSIK_DIR/push-ticket divergence in cli_push_ok.py / git_push_gate.py. config_trust.py is at its 400-line cap so the helper goes in tausik_utils, NOT config_trust. Do NOT modify config_trust's resolve/enforce logic."
relevant_files:
  - "scripts/tausik_utils.py"
  - "scripts/hooks/session_cleanup_check.py"
  - "scripts/hooks/tool_output_truncation_nudge.py"
  - "tests/test_session_cleanup_check.py"
  - "tests/test_tool_output_truncation_nudge.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T15:09:04Z"
---

## Goal

scripts/hooks/session_cleanup_check.py:31-38 и scripts/hooks/tool_output_truncation_nudge.py:46-55 берут путь через tausik_utils.tausik_config_path() и затем json.load'ят файл НАПРЯМУЮ, минуя config_trust.resolve(). Следствие: ~/.tausik/config.json (user-тир) и $TAUSIK_MANAGED_CONFIG (managed-тир) не действуют на session_warn_threshold_minutes и tool_output_truncation_threshold — то есть ровно на те две настройки, которые оператор скорее всего захочет задать машинно-глобально. config_trust.py:13 документирует слоение как КОНТРАКТ; эти два хука его не реализуют, и это подрывает трастовую модель не в частности, а в принципе (тир существует ровно настолько, насколько его читают все потребители). Фикс: хуки зовут project_config.load_config(tausik_dir); если возражение — вес импорта в PreToolUse-хуке, вынести stdlib-only config_trust.resolve_from_disk(project_dir). Смежно в том же классе: два «единственных источника истины» для пути конфига (tausik_utils.tausik_config_path и project_config.get_config_path) и три резолвера каталога .tausik, из которых $TAUSIK_DIR уважает только один (project_config.find_tausik_dir), а cli_push_ok.py:28 и hooks/git_push_gate.py:98 — нет: при заданном TAUSIK_DIR push-тикет пишется и читается в РАЗНЫХ .tausik.

## Acceptance Criteria

1. New tausik_utils.load_effective_config(project_dir) reads <project_dir>/.tausik/config.json as the project tier and merges the user (~/.tausik) + managed ($TAUSIK_MANAGED_CONFIG) tiers via config_trust.resolve (lazy import — no cycle, keeps tausik_utils import-light). Any read problem degrades the project tier to {} (never crashes); trust-tier rejections logged. 2. session_cleanup_check._session_warn_min uses load_effective_config instead of raw json.load, so a user/managed session_warn_threshold_minutes now takes effect. 3. tool_output_truncation_nudge._resolve_threshold uses load_effective_config (config key first, then env, then default 250 preserved), so a user/managed tool_output_truncation_threshold now takes effect. 4. Project-tier-only behavior byte-identical (pure widening). 5. Regression tests: (a) a user/managed-tier value takes effect in each hook, (b) project-tier-only unchanged, (c) malformed/missing config → safe fallback, hook never crashes. 6. Full suite green, 0 warnings. NEGATIVE/BOUNDARY: 7. Malformed project config.json (bad JSON, non-dict root) → load_effective_config returns the trusted-tier merge (or {}) and each hook falls back to its default; never raises.

## Plan

## Rollback

git revert — removes load_effective_config and restores each hook's raw json.load. Pure additive helper + two call-site swaps; no schema/behavior change for single-tier users.

## Journal

- 2026-07-26T15:08:55Z [implementation] — AC verified: 1. ✓ tausik_utils.load_effective_config: reads project .tausik/config.json + config_trust.resolve (lazy import, no cycle); read problem→{}, rejections logged. test_tausik_utils passing 2. ✓ session_cleanup_check._session_warn_min uses load_effective_config; test_user_tier_value_now_takes_effect (90) passes 3. ✓ tool_output_truncation_nudge._resolve_threshold uses load_effective_config, order config>env>default preserved; test_resolve_threshold_from_user_tier (88) passes 4. ✓ project-only unchanged: test_project_tier_value + test_resolve_threshold_from_config_json green 5. ✓ user-tier takes effect / project-only unchanged / malformed→fallback tests both hooks; autouse fixture isolates TAUSIK_USER_CONFIG+MANAGED so suite never reads real ~/.tausik 6. ✓ full suite 5996 passed 24 skipped 0 failed 0 warnings 7. ✓ NEGATIVE: test_malformed_project_falls_back (both hooks) — bad JSON → default, no crash
