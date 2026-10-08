---
slug: neobyavlennyy-scope-pustye-relevant-files-ostaetsya-ne
task: check-result-conflates-could-not-run-with-passed
date: "2026-08-25"
edges: []
---

## Decision

НЕОБЪЯВЛЕННЫЙ SCOPE (пустые relevant_files) ОСТАЁТСЯ НЕ БЛОКИРУЮЩИМ — NOT_APPLICABLE с собственным кодом причины no_scope_declared, а НЕ COULD_NOT_RUN. Различимость даётся кодом причины, а не блокировкой. Развилка задачи check-result-conflates-could-not-run-with-passed, решена в сессии #183.

## Rationale

Три замеренных основания против поднятия до COULD_NOT_RUN.

1) У ФАКТА УЖЕ ЕСТЬ ВЛАДЕЛЕЦ: сертификация нескоупленного прогона отвергается выше по течению, через verification_runs.declared_scope_status. Второй несогласованный страж того же правила разъезжается — как gate_verdict, живший в пяти местах и разошедшийся в обе стороны.

2) РАДИУС ПОРАЖЕНИЯ: run_gates зовётся (gate_runner.py:363) с пустыми files при штатном `gate_runner <trigger>` без --files, это путь commit-триггера. Блокировка покраснила бы каждый такой вызов.

3) НЕГАТИВНОЕ ОГРАНИЧЕНИЕ GOAL: законный пропуск обязан остаться выразимым; свести оба случая к блокировке значит заменить одну неразличимость другой. Пустой scope — состояние ВЫЗЫВАЮЩЕГО, не невозможность исполнения гейта.

ПОЧИНЕНО ВСЁ РАВНО: оба пропуска ехали одним сентинелом и были неразличимы; теперь это no_test_mapping и no_scope_declared. ПЕРЕСМОТРЕТЬ, если найдётся закрытие, проскочившее мимо declared_scope_status.
