---
slug: obem-1-9-32-posle-smeny-208-zakryto-shest-zavedeno-chetyre
task: null
date: "2026-09-04"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 32 ПОСЛЕ СМЕНЫ #208: ЗАКРЫТО ШЕСТЬ, ЗАВЕДЕНО ЧЕТЫРЕ (все четыре закрыты в ту же смену). Пересчитано КОМАНДОЙ по шести историям (память #515): gates-declare-what-they-prevent 8 (7 planning + 1 blocked), evidence-primitives 5, renar-debt-implemented-wrong 7, renar-contract-contour 5, test-evidence-not-test-volume 4, standards-drift-detection 3. Закрыто из плана: ar-existence-is-probed-by-three-guessed-table-names, epic-and-story-descriptions-cannot-be-updated. Заведено и закрыто: review-208-open-channel-is-never-asserted (L3 на починку #207), snapshot-test-races-the-clock-on-linux и pwsh-channel-backslash-script-path-unresolved-on-posix (первый пайплайн 1.9 на Linux, #6658), review-208-doc-counts-blind-and-update-guards (плановое L3 по пяти закрытым). Третье сокращение подряд, на два; источники пополнения — ревью и CI, разведка ноль. Пайплайны GitLab 6658 красный (2 Linux-падения) -> 6663, 6665 зелёные; push 40 коммитов сделан по явному «да» владельца.

## Rationale
