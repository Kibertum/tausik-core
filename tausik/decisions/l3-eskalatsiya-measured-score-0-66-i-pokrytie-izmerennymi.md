---
slug: l3-eskalatsiya-measured-score-0-66-i-pokrytie-izmerennymi
task: v15-l3-risk-trigger
date: "2026-06-12"
edges: []
---

## Decision

L3-эскалация: measured score >= 0.66 И покрытие измеренными факторами >= 0.75 весов (4 из 5)

## Rationale

Селективная эскалация Walko ~1%: тонкие подмножества (ac+churn=0.35, casual-паттерн td+ac+sec=0.60) дают high на рутинных закрытиях — найдено живым boundary-флейком 0.6667 в полном suite. Эскалируем только при широкой измеренной картине.
