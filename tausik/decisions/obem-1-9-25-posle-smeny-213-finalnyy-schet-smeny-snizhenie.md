---
slug: obem-1-9-25-posle-smeny-213-finalnyy-schet-smeny-snizhenie
task: null
date: "2026-09-06"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 25 ПОСЛЕ СМЕНЫ #213, ФИНАЛЬНЫЙ СЧЁТ СМЕНЫ, снижение с 29 (решение #314) через 26 (решение #316). Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 7 (6 planning + 1 BLOCKED), renar-debt-implemented-wrong 3, renar-contract-contour 5, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 2. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29,25. ВНЕ ШЕСТИ ИСТОРИЙ 8 открытых задач (решение #310), объём не раздувают.

## Rationale

В смене закрыто четыре задачи из объёма: next-version-reads-the-journal-tip-not-its-history и заведённый по внешнему ревью дефект rev-list-simplification (обе contour, нетто 6→5), changelog-gate-double-registration-premise-unconfirmed (gates 8→7), mandatory-clauses-are-constants-published-as-earned (renar-debt 4→3), doc-values-of-closed-lists-have-no-guard (standards-drift 3→2). Внеисторийных стало 8: закрыты powershell-channel-cannot-read-python-dash-c, changelog-gate-switch-is-outside-config-trust-guards и её docs-дефект guarded-key-added-without-its-spec-entry, заведена l3-dispatch-does-not-carry-the-author-model.
