---
slug: geyt-ne-sumevshiy-ispolnitsya-vozvraschaet-gateoutcome
task: claudemd-state-gate-reports-passed-when-it-could-not-run
date: "2026-08-31"
edges: []
---

## Decision

ГЕЙТ, НЕ СУМЕВШИЙ ИСПОЛНИТЬСЯ, ВОЗВРАЩАЕТ GateOutcome.could_not_run И БЛОКИРУЕТ; ЛЕГАСИ-ПАРА (True, "unavailable") ЗАПРЕЩЕНА КАК ФОРМА ОТВЕТА НА ИСКЛЮЧЕНИЕ. Честные пропуски уходят через not_applicable, каждое пустое состояние — СВОИМ reason_code, а не одним общим. Три fail-CLOSED сайта (gate_qg0_check:101, gate_qg0_renar:28, gate_registry:482) под правило НЕ подпадают: их `return True` означает «проверка остаётся включена».

## Rationale

Замер #192: claudemd_state_drift, severity=block, записан как {"outcome":"PASSED","passed":true} с собственным текстом «check unavailable (RuntimeError: Database schema v48 is newer than code v47)». Проверка объявила своё невыполнение и была подписана доказательством; отличить строку от настоящего прохода мог только человек глазами. SENAR 1.4 §8.6(e): отсутствие отрицательной находки не есть положительный вердикт. Механизм для этого уже стоял с v47 (gate_outcome + coerce + gate_runs.outcome/reason_code) — сломано было то, что импл гейта возвращал легаси-пару, которую coerce ОБЯЗАН прочесть как PASSED. Отсюда правило адресуется имплам, а не runner. Один общий код на четыре пустых состояния отвергнут: он переносит неразличимость, а не снимает её.
