---
slug: l26-tokenizer-calibration
title: "Поправка на смену токенизатора в калибровке бюджетов"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/token_accounting.py tests/test_token_accounting.py scripts/hooks/session_metrics.py tests/test_session_metrics_parse.py scripts/backend_tier_metrics.py CHANGELOG.md CHANGELOG.ru.md"
scope_exclude: "scripts/service_recording.py scripts/service_task_done.py scripts/backend_queries_metrics.py scripts/project_cli_metrics.py .tausik/tausik.db backend_schema.py"
relevant_files:
  - "scripts/token_accounting.py"
  - "tests/test_token_accounting.py"
  - "scripts/hooks/session_metrics.py"
  - "tests/test_session_metrics_parse.py"
  - "scripts/backend_tier_metrics.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/token_accounting.py"
  - "tests/test_token_accounting.py"
  - "scripts/hooks/session_metrics.py"
  - "tests/test_session_metrics_parse.py"
  - "scripts/backend_tier_metrics.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T15:23:19Z"
---

## Goal

Opus 4.7 и новее, Fable 5, Mythos 5 и Sonnet 5 используют НОВЫЙ токенизатор, дающий примерно на 30 процентов больше токенов на одном и том же тексте; Sonnet 4.6 и старше — прежний. Значит сравнения токенов и стоимости через эту границу невалидны без поправки. У TAUSIK есть cost-телеметрия и калибровка, и она сейчас показывает систематическое недооценивание (actual/budget=6.07 при n=10). ГИПОТЕЗА ДЛЯ ПРОВЕРКИ: часть этого недооценивания — артефакт смены токенизатора, а не плохих оценок. Задача: пометить исторические записи моделью, ввести поправочный коэффициент при сравнении через границу, перепроверить вывод о калибровке. Смежно: серверная компакция биллится отдельным шагом, и верхнеуровневые input_tokens/output_tokens ЕГО НЕ ВКЛЮЧАЮТ — нужно суммировать usage.iterations, иначе счёт занижен.

## Acceptance Criteria

AC1. Исторические cost-записи помечены токенизатором модели (новый: Opus 4.7+/Fable 5/Mythos 5/Sonnet 5; прежний: Sonnet 4.6 и старше); тест подтверждает корректную классификацию границы.
AC2. Введён поправочный коэффициент (~+30% токенов) при сравнении токенов/стоимости ЧЕРЕЗ границу токенизатора; сравнения внутри одной эры не искажаются — тест fails-then-passes.
AC3. Вывод о калибровке перепроверен: доля систематического недооценивания (actual/budget=6.07 при n=10), объяснимая сменой токенизатора, отделена от плохих оценок; результат зафиксирован числом.
AC4. Учтён отдельный биллинг серверной компакции: верхнеуровневые input/output_tokens её НЕ включают, суммируется usage.iterations — тест, что итоговый счёт не занижен.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert the commit; new module scripts/token_accounting.py is additive (delete file + revert the ~6-line parse_transcript wiring in session_metrics.py + docstring note in backend_tier_metrics.py). No schema/migration, no DB writes — pure library + reporting layer.

## Journal

- 2026-07-27T15:23:17Z [implementation] — AC verified: 1. ✓ tokenizer_era() classifies model ids by exact boundary; label_usage_rows() marks records via derived era (no schema column). tests/test_token_accounting.py::TestTokenizerEraBoundary (opus-4-6=old vs opus-4-7=new, sonnet-4-6=old vs sonnet-5=new, fable-5/mythos-5=new) + TestLabelUsageRows, all green in scoped verify 2. ✓ normalized_token_count()+era_normalized_total() apply +30% ONLY across the era boundary; same-era total is byte-identical to naive sum. Fails-then-passes shape: TestEraNormalizedTotal.test_single_era_total_undistorted (==naive) vs test_cross_era_total_corrected (>naive). Green in scoped verify 3. ✓ Hypothesis tested and REJECTED: calibration_drift = call_actual/call_budget (tool-call counts, tokenizer-independent) → 0% of drift attributable to tokenizer. Number recorded in decision #188 + calibration_drift docstring + CHANGELOG EN/RU 4. ✓ sum_usage_tokens() folds usage.iterations[*] (server-side compaction) back into parse_transcript totals which previously omitted them. tests/test_session_metrics_parse.py::TestParseTranscriptCompactionBilling (1000/500 + iter 300/100 → 1300/600) + test_token_accounting.py::TestSumUsageTokens. Green 5. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] each carry a prose subsection 'Tokenizer-era correction, and the calibration hypothesis it disproved'
