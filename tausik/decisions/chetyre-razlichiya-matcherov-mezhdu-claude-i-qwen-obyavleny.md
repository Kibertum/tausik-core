---
slug: chetyre-razlichiya-matcherov-mezhdu-claude-i-qwen-obyavleny
task: cross-model-parity-has-no-gate
date: "2026-09-07"
edges: []
---

## Decision

ЧЕТЫРЕ РАЗЛИЧИЯ МАТЧЕРОВ МЕЖДУ claude И qwen ОБЪЯВЛЕНЫ, А НЕ УСТРАНЕНЫ. activity_event и task_call_counter у qwen ловят каждый инструмент, у claude — списки из 10 и 5; task_done_verify у qwen ловит ещё task_done_v2, Bash и PowerShell; tool_output_truncation_nudge у qwen шире. Выравнивать нельзя ни в какую сторону: сузить qwen — молча укоротить уже измеренные сессии, расширить claude — сломать базу экономии 1.9 (решение #338), калиброванную на числе claude.

## Rationale

Предмет гейта кроссмодельности — НАЗВАНО ли различие, а не устранено. У Cursor точки расширения нет вовсе, поэтому требование одинаковости невыполнимо в принципе, а гейт, который его предъявляет, выключают. Различие с зубами здесь одно: закрытие задачи через CLI перепроверяется хуком на qwen и не перепроверяется на claude — но QG-2 отрабатывает внутри самой команды task done на обоих хостах, поэтому путь CLI верифицирован и без хука.
