---
slug: obem-1-9-29-posle-smeny-212-finalnyy-schet-smeny-snizhenie
task: null
date: "2026-09-04"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 29 ПОСЛЕ СМЕНЫ #212, ФИНАЛЬНЫЙ СЧЁТ СМЕНЫ, снижение с 31. Пересчитано КОМАНДОЙ по шести историям: gates-declare-what-they-prevent 8 (7 planning + 1 BLOCKED), renar-debt-implemented-wrong 4, renar-contract-contour 6, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 3. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31,29. Арифметика: закрыто ЧЕТЫРЕ, заведено ДВА, 31-4+2=29. Решение #313 (объём 30) ОТМЕНЯЕТСЯ этим: оно записано до закрытия четвёртой задачи.

## Rationale

Закрыты conformance-replaces-default-derived-from-a-date и git-show-worktree (renar-contract-contour), our-only-spec-is-derived-without-either-allowed-source-field и check-adapt-supersession-gate-has-no-subject-yet (renar-debt-implemented-wrong). Заведены git-show-worktree (закрыта в ту же смену) и next-version-reads-the-journal-tip-not-its-history — обе найдены адверсариальным ревью, обе с премисой, подтверждённой замером ДО заведения. Две из четырёх задач изменились ПО ЗАМЕРУ прямо в работе и стали честнее: check-adapt-supersession откладывалась четыре смены как гейт без предмета, а инвентарь ПО СХЕМЕ нашёл носитель adapts.parent_adapt, которого никто не искал. Ни одного контроля без предмета не построено — это и есть предмет релиза 1.9.
