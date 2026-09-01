---
slug: obem-1-9-44-posle-smeny-205-zakryta-odna-zavedeno-dve-po
task: null
date: "2026-09-01"
edges: []
---

## Decision

ОБЪЁМ 1.9 = 44 ПОСЛЕ СМЕНЫ #205: ЗАКРЫТА ОДНА, ЗАВЕДЕНО ДВЕ ПО РЕШЕНИЮ ВЛАДЕЛЬЦА. Обе новые задачи найдены ЗАМЕРОМ внутри закрытой, ни одна не пришла со стороны. Первая — write-gate-does-not-treat-a-newline-as-a-command-separator: блокирующий ACL обходится строкой echo перед записью, проверено настоящим хуком, 723996 байт легли вне объёма. Вторая — tests-call-bash-by-bare-name-windows-ci-answers-wsl-stub: лента верификации релиза на GitHub красная шесть дней, три прогона подряд, падают только Windows-полосы. Обе отнесены к истории gates-declare-what-they-prevent. Счёт по шести историям: gates-declare-what-they-prevent 15, evidence-primitives 8, renar-debt-implemented-wrong 8, renar-contract-contour 5, test-evidence-not-test-volume 4, standards-drift-detection 3. Точки остатка: 35, 38, 37, 39, 42, 40, 42, 44 — равновесие смены #204 трендом не стало, пополнение снова превысило закрытие.

## Rationale
