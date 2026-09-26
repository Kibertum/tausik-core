---
slug: session-metrics-sums-usage-once-per-content-block
title: "session_metrics.parse_transcript sums usage once per JSONL entry, and Claude Code writes one entry per content block — tokens_total is inflated ~1.8×"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/hooks/session_metrics.py, tests/"
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/token_rows.py"
  - "tests/test_usage_once_per_message.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:28:58Z"
resolution: null
resolution_reason: null
---

## Goal

Measured in session #263 on the replay transcripts of v14b-rag-nudge-replay-benchmark: Claude Code writes an assistant message with N content blocks (thinking, text, tool_use…) as N JSONL entries sharing one message.id and one identical usage object; parse_transcript adds that usage N times. Condition B: 52 assistant messages lie in 321 entries; deduplicated by message.id input+output = 31,613, the meter recorded tokens_total = 57,135 (1.81×). Condition A: 44 messages, meter 47,221 vs deduplicated ~26,822. Every row of session_usage_metrics, the cost_usd derived from it, and the calibration/capacity views that read it carry this inflation; the ratio depends on how many blocks a message has, so it is not a constant to divide out. Fix: aggregate usage per message.id (or requestId) — last-seen usage per id — in parse_transcript and extract_token_rows, then regression-test with a synthetic three-block message; decide separately whether historical rows are re-derived from surviving transcripts or marked as pre-fix.

## Acceptance Criteria

AC-1: parse_transcript and extract_token_rows count each message.id once (last usage seen wins); a synthetic transcript with one three-block assistant message yields its usage exactly once. AC-2: on the real B replay transcript (sha256 in docs/ru/research/_internal/rag-replay/2026-09-14/B/transcript.sha256) the meter's tokens_total equals 31,613, the deduplicated sum. AC-3 (negative): a test with two DIFFERENT messages sharing nothing but the same content-block shape still counts both. AC-4: a decision is recorded on historical session_usage_metrics rows (re-derive or mark pre-fix) — not silently left inflated.

## Plan

## Rollback

git revert; the change is in-memory aggregation only, no schema.

## Journal

- 2026-09-23T19:26:01Z [implementation] — AC-1: ✓ tests/test_usage_once_per_message.py::test_one_three_block_message_is_counted_once
- 2026-09-23T19:26:01Z [implementation] — AC-1: ✓ tests/test_usage_once_per_message.py::test_tool_rows_split_one_message_usage_across_its_tool_uses
- 2026-09-23T19:26:01Z [implementation] — Сделано: parse_transcript копит usage по message.id (последний побеждает) и суммирует один раз; token_rows.extract_token_rows группирует записи одного сообщения и делит его usage на все tool_use сообщения (_rows_for). session_metrics.py 498 строк. Живой транскрипт B смены #263 (sha256 совпал) даёт tokens_total = 31 613 = дедуплицированная сумма из usage.json. Решение #384 о старых строках: не пересчитываются, объявлены завышенными в docs/en|ru/cost-telemetry.md (в тексте решения ошибочно упомянута страница session-active-time — верная страница cost-telemetry).
- 2026-09-23T19:26:02Z [implementation] — AC-2: ✓ tests/test_usage_once_per_message.py::test_the_replay_transcript_of_session_263_meters_the_deduplicated_sum
- 2026-09-23T19:26:02Z [implementation] — AC-3: ✓ tests/test_usage_once_per_message.py::test_two_different_messages_of_the_same_shape_both_count
- 2026-09-23T19:26:02Z [implementation] — AC-4: ✓ решение #384, docs/en|ru/cost-telemetry.md, CHANGELOG EN+RU
