---
slug: at-red-with-tc-green-routes-to-interpretation-not-code
title: "Матрица маршрутизации провалов и релизный гейт: красный AT при зелёных TC — ошибка интерпретации"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: null
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

RENAR §8A.4 и §10.4.3. Расхождение уровней проверки само указывает, где искать, и это диагностика, а не отчёт: AT красный при зелёных TC означает ошибку ИНТЕРПРЕТАЦИИ и уходит в ADAPT, а не в код; оба красные означают дефект кода; AT зелёный при красном TC означает, что тест устарел либо внутренняя норма строже контракта. Релизный гейт: продукт не предъявляется к сдаче, пока не все AT зелёные и не выведены из ДЕЙСТВУЮЩЕЙ редакции итогового ТЗ. Он НЕ смешивается с QG-4, который опционален и меряет бизнес-результат. Задача: реализовать маршрутизацию как машинный вывод из состояния двух наборов, а не как таблицу в документации, и завести релизный гейт отдельной проверкой. Смежное: тот же приём «расхождение как диагностика» взят из производственной модели решением #250 пунктом 3 — реализуется здесь один раз, а не дважды. Зависит от at-acceptance-tests-derived-by-an-isolated-agent.

## Acceptance Criteria

## Plan

## Rollback

## Journal
