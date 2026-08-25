---
slug: s146-review-fixes-tokenizer-date-as-minor-sum-usag
title: "s146-review-fixes: tokenizer date-as-minor, sum_usage int-crash, OTLP negative span"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/token_accounting.py"
  - "scripts/otel_export.py"
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_token_accounting.py"
  - "tests/test_otel_export.py"
  - "tests/test_mcp_self_check.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/token_accounting.py"
  - "scripts/otel_export.py"
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_token_accounting.py"
  - "tests/test_otel_export.py"
  - "tests/test_mcp_self_check.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T16:25:09Z"
---

## Goal

Исправить находки адверсариального ревью батча #146 (3 закрытые задачи: token_accounting, mcp_reaper/self_check, otel_export). Две HIGH-корректности + mediums/lows, которые тесты не ловили.

## Acceptance Criteria

AC1 (HIGH): tokenizer_era НЕ читает дату-суффикс как minor — claude-opus-4-20250514 классифицируется OLD (не NEW); регекс ограничивает minor 1-2 цифрами с границей; regression-тест на дату-суффиксный реальный id.
AC2 (HIGH): sum_usage_tokens/_iter_tokens zero-safe по факту — int() обёрнут в try/except, нечисловое значение поля (напр. 'N/A') даёт 0, не ValueError; parse_transcript не падает; тест с нечисловым полем.
AC3 (MEDIUM): OTLP-спан никогда не start>end — session_otlp_document клампит duration_ns=max(0,...), build_otlp_trace возвращает {} при end<start; тест на отрицательный duration_sec (НЕГАТИВ).
AC4: AC2-линт усилен против split-string evasion (ловит и голый \"gen_ai\"); self_check call-site обёрнут защитно; export_enabled поддерживает env-kill-switch (явный falsy TAUSIK_OTEL_EXPORT=0 жёстко выключает поверх config).
AC5: полный scoped verify зелёный; CHANGELOG EN+RU обновлены.

## Plan

## Rollback

## Journal

- 2026-07-27T16:25:06Z [implementation] — AC1: ✓ tokenizer_era regex minor capped to (\d{1,2})(?!\d) — claude-opus-4-20250514 → OLD (verified direct + test_bare_major_dated_id_is_old_not_new); 2-digit minors (opus-4-10) still NEW; dead else-branch removed. AC2: ✓ _as_int() wraps int() try/except — sum_usage_tokens({'input_tokens':'N/A'...}) → (0,5) no raise (test_non_numeric_field_does_not_raise + direct). AC3: ✓ session_otlp_document clamps duration_ns=max(0,..), build_otlp_trace returns {} on end<start (TestBackwardsSpanRejected + test_negative_duration_clamped_not_backwards). AC4: ✓ AC2 lint pattern now ["']gen_ai(?:\.|["']) catches split-string; export_enabled explicit-falsy env kill-switch (test_env_falsy_overrides_config_enabled); self_check collect() wraps enumeration → count=-1 on exception (test_enumeration_exception_degrades_to_unknown). AC5: ✓ scoped verify green run #1516 signed; CHANGELOG EN+RU review-fix entry. Domain: fixes are hardening only, no behavior removed; both HIGH bugs reproduced-then-fixed against real Anthropic id forms + malformed transcript values. Negative scenarios covered: dated id, non-numeric token field, backwards span, kill-switch, enumeration crash.
