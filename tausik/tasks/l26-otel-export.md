---
slug: l26-otel-export
title: "OTel-экспорт трейсов (с поправкой на нестабильность конвенций)"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "OTel SDK dependency (stdlib-only OTLP/JSON); live collector round-trip (golden reference sample instead); .tausik/tausik.db"
relevant_files:
  - "scripts/otel_semconv.py"
  - "scripts/otel_export.py"
  - "tests/test_otel_export.py"
  - "scripts/hooks/session_metrics.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/otel_semconv.py"
  - "scripts/otel_export.py"
  - "tests/test_otel_export.py"
  - "scripts/hooks/session_metrics.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T15:44:41Z"
---

## Goal

У TAUSIK свой формат событий и метрик. Индустрия сходится на OpenTelemetry как транспорте (OTLP принимают все вендоры). ВАЖНАЯ ПОПРАВКА, проверенная по первоисточнику 2026-07-18: конвенции GenAI НЕ стабильны — вынесены в отдельный репозиторий open-telemetry/semantic-conventions-genai с НУЛЁМ опубликованных релизов, статус Development; массовые утверждения о стабильности в блогах путают релизный поезд semconv с зрелостью GenAI. Поэтому: экспортировать OTLP-спаны как ДОПОЛНИТЕЛЬНЫЙ выход (внутренние events остаются источником правды), имена атрибутов держать в одном модуле-маппере, чтобы churn конвенций не расползался по коду. Практический выигрыш: совместимость с аудит-стеком под EU AI Act и с существующими наблюдательными платформами без своего UI.

## Acceptance Criteria

AC1. OTLP-спаны экспортируются как ДОПОЛНИТЕЛЬНЫЙ выход; внутренние events остаются источником правды. Тест: экспорт включается/выключается, при выключении путь events не меняется.
AC2. Имена атрибутов GenAI собраны в ОДНОМ модуле-маппере; линт/тест подтверждает, что вне маппера нет захардкоженных semconv-имён, чтобы churn конвенций не расползался по коду.
AC3. Экспортированный спан валиден по OTLP и принимается стандартным коллектором (тест против OTLP-приёмника либо зафиксированный эталонный образец).
AC4. В маппере и доке помечено, что GenAI-конвенции нестабильны (open-telemetry/semantic-conventions-genai, 0 релизов, статус Development) — чтобы будущий churn не читался как баг.
AC5 (НЕГАТИВ/граница): при пустых/битых метриках (None, отсутствующие поля, model="") экспорт НЕ падает и НЕ портит путь events — возвращает пустой/безопасный результат, ошибка не пробрасывается в hook.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; export is additive + opt-in (disabled by default) — when off the events path is byte-identical, so nothing to undo operationally.

## Journal

- 2026-07-27T15:44:40Z [implementation] — AC1: ✓ OTLP export is additive + opt-in (off by default); export_enabled() default False; session_otlp_document() returns {} when disabled so SessionEnd events path is unchanged; wired in session_metrics.main() behind the toggle. tests/test_otel_export.py::TestExportToggle + TestSessionWiring::test_disabled_returns_empty. AC2: ✓ all gen_ai.* names centralized in scripts/otel_semconv.py; test_no_hardcoded_semconv_names_outside_mapper lints scripts/ and fails on any gen_ai. literal elsewhere. AC3: ✓ build_otlp_trace() emits valid OTLP/JSON (resourceSpans>scopeSpans>spans, 32/16-hex ids, string uint64 nanos, KeyValue attrs); golden-stable on fixed input; tests test_otlp_structure_valid + test_span_carries_genai_attributes + test_golden_document_is_stable. AC4: ✓ instability documented in otel_semconv docstring + CONVENTIONS_STATUS/SOURCE data + CHANGELOG EN/RU prose (0 releases, status Development, semantic-conventions-genai); test_instability_is_documented. AC5 (Negative): ✓ None/empty metrics and malformed trace/span ids return {} without raising; missing fields omitted not emitted; tests TestNegativePath + test_enabled_empty_metrics_still_safe. Domain: the OTLP/JSON document is a structurally valid trace any OTLP receiver ingests; stdlib-only, no OTel SDK dep. Full scoped verify green (run #1514, signed).
