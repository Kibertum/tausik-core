---
slug: obem-1-9-31-posle-smeny-211-snizhenie-s-32-pereschitano
task: null
date: "2026-09-04"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 31 ПОСЛЕ СМЕНЫ #211, снижение с 32. Пересчитано КОМАНДОЙ по шести историям (память #515): gates-declare-what-they-prevent 8 (7 planning + 1 blocked), renar-debt-implemented-wrong 6, renar-contract-contour 6, evidence-primitives 4, test-evidence-not-test-volume 4, standards-drift-detection 3. Точки: 35,38,37,39,42,40,42,43,39,34,32,28,32,31.

Закрыто две. migration-docstrings-claim-an-unverified-fts-effect дало историю test-evidence-not-test-volume 5 -> 4. adapt-delta-leaves-an-orphan-when-the-guard-refuses заведена и закрыта в ту же смену как defect_of нашей же работы #210 (найдена плановым L3), поэтому renar-debt-implemented-wrong осталась 6: +1 и -1 внутри смены, как было с четырьмя доковыми носителями в #210.

ЗАВЕДЕНЫ ВНЕ ШЕСТИ ИСТОРИЙ по решению #310, объём НЕ раздувают: firewall-reads-heredoc-body-as-a-command и transaction-owners-mostly-do-not-check-ownership. Внеисторийных теперь ВОСЕМЬ. Владелец может перенести любую в историю; перенос каждой поднимет объём на единицу.

## Rationale
