---
slug: obem-1-9-30-posle-smeny-212-snizhenie-s-31-pereschitano
task: null
date: "2026-09-04"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 30 ПОСЛЕ СМЕНЫ #212, снижение с 31. Пересчитано КОМАНДОЙ по шести историям (память #515): gates-declare-what-they-prevent 8 (7 planning + 1 BLOCKED), renar-debt-implemented-wrong 5, renar-contract-contour 6, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 3. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,30. Арифметика сходится: закрыто ТРИ (conformance-replaces-default-derived-from-a-date и git-show-worktree в renar-contract-contour, our-only-spec-is-derived-without-either-allowed-source-field в renar-debt-implemented-wrong), заведено ДВА, оба в renar-contract-contour, оба НАЙДЕНЫ АДВЕРСАРИАЛЬНЫМ РЕВЬЮ на починку и оба с ПОДТВЕРЖДЁННОЙ ЗАМЕРОМ премисой: git-show-worktree (закрыта в ту же смену) и next-version-reads-the-journal-tip-not-its-history (остаётся открытой). 31 - 3 + 2 = 30.

## Rationale

Ревью на сами починки окупилось третий раунд подряд (память #536): из двух заведённых задач одна найдена и закрыта в ту же смену, вторая несёт замер, доказывающий переиспользование версии v1 при --write с ветки main. Ни одна из двух не есть пополнение объёма догадкой — обе премисы проверены командой до заведения. Внеисторийных задач по-прежнему ВОСЕМЬ (решение #310), объём они не раздувают и релиз не блокируют; doctor из-за них даёт единственный WARN, и это прямое следствие решения, а не поломка.
