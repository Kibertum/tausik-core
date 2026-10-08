---
slug: kalibrovochnyy-signal-calibration-drift-tokenizator
task: l26-tokenizer-calibration
date: "2026-07-27"
edges: []
---

## Decision

Калибровочный сигнал calibration_drift токенизатор-НЕЗАВИСИМ: 0% его дрейфа объяснимо сменой токенизатора 2026. Поправка +30% применяется ТОЛЬКО там, где сравниваются ТОКЕНЫ/ДОЛЛАРЫ через границу эр (usage rollups, token budgets), не к call-based калибровке.

## Rationale

Гипотеза задачи (часть недооценивания actual/budget — артефакт токенизатора) проверена и ОТКЛОНЕНА для DB-калибровки: calibration_drift = call_actual/call_budget, это счётчики ВЫЗОВОВ инструментов — целые числа, не зависящие от токенизатора. Токены там не участвуют вовсе. Смешение двух метрик (call-count vs token-count) — ложная посылка. Поправка вынесена в reporting/aggregation слой (token_accounting.era_normalized_total/normalized_token_count), НЕ в task_done lifecycle (scope_exclude service_recording.py) — это уважает medium-risk warning и держит правку в тестируемой чистой библиотеке. Смежно: серверная компакция биллится под usage.iterations[*] и не входит в верхнеуровневые input/output_tokens — sum_usage_tokens устраняет занижение в parse_transcript.
