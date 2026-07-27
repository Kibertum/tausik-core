---
slug: opt-in-mehanizm-deklaratsiya-chyu-zabyvchivost-nelzya
task: scoped-pytest-blind-to-crosscutting-tests
date: "2026-07-27"
edges: []
---

## Decision

Опт-ин механизм (декларация), чью забывчивость нельзя допустить, снабжай храповиком-детектором: эвристика находит кандидатов, каждый обязан declare/opt-out/grandfather, а grandfather-база только сжимается. Так 'отсутствие привязки видимо' без ревью всех N сразу.

## Rationale

scoped-pytest cross-cutting: чистый опт-ин (CROSSCUTTING_SCOPE) воспроизвёл бы исходную слепоту молча — новый tree-iterating тест забыли бы задекларировать. Решение: test_crosscutting_registry heuristic (ITER+ANCHOR+SRC) детектит tree-iterators; frozen _GRANDFATHERED(30) для существующих, но НОВЫЙ недекларированный краснит CI. Двусторонний ratchet (как _KNOWN_ORDER_DRIFT в schema-parity): база не растёт (новое → декларация) и не гниёт (задекларированный → удалить из базы). Ключ: детектор само-исключается (регекс-литералы idiom не считаются итерацией). Grandfather позволяет не трогать все 30 сразу — non-invasive.
