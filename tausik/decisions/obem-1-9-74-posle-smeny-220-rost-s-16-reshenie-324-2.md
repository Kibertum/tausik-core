---
slug: obem-1-9-74-posle-smeny-220-rost-s-16-reshenie-324-2
task: null
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 74 ПОСЛЕ СМЕНЫ #220, РОСТ с 16 (решение #324) — владелец отменил узкое чтение решения #256 по объёму (решение #325). Пересчитано КОМАНДОЙ по 16 историям: gates-declare-what-they-prevent 5, renar-contract-contour 5, evidence-primitives 3, test-evidence-not-test-volume 3, renar-debt-implemented-wrong 0, standards-drift-detection 0, guarantees-are-not-claude-only 12, knowledge-records-what-failed-19 8, proof-and-positioning-outward 7, github-primary-gitlab-mirror 0, verification-off-the-critical-path 3, the-loop-closes-outward 7, evidence-is-durable 4, parallel-work-runs-without-collisions 5, context-carries-over-between-sessions 6, agent-output-discipline 6. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25,23,21,20,22,20,18,16,74.

## Rationale

Решение #325 объявило волю владельца прозой, но не в формате, который читает scripts/release_roadmap.py: композиция релиза читается substring-совпадением слагов историй в НОВЕЙШЕМ решении, называющем ≥2 истории (COMPOSITION_MIN_STORIES), а #325 не называет 5 подысторий release-19-agent-effectiveness и не называет 6 исходных историй буквально. Без этого решения `tausik doc roadmap` собрал бы карту всего по 4 историям вместо 16. Это решение — техническое исправление формата под тем же выбором владельца, не новый выбор.
