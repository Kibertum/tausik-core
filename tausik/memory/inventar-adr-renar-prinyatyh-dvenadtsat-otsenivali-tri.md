---
slug: inventar-adr-renar-prinyatyh-dvenadtsat-otsenivali-tri
title: "Инвентарь ADR RENAR: принятых двенадцать, оценивали три; оценки сложности 1.9"
type: context
tags:
  - "1.9"
  - adr
  - renar
  - sizing
task: null
edges: []
---

Прочитаны статусы ВСЕХ 22 ADR локального корпуса ../../standards/renar/research/decisions/ (сессия #189). ПРИНЯТЫХ ДВЕНАДЦАТЬ: 001, 003, 005, 006, 007, 009, 011 (accepted-pending-adr-012 — условие выполнено, так как 012 accepted), 012, 013, 020, 021, 022, 023. SUPERSEDED: 002, 004. PROPOSED: 010, 015, 016, 017, 018, 019, 024 — последние шесть не реализуются по решению #255.
СЛЕДСТВИЕ ПЕРВОЕ: контрактный контур ОБЯЗАТЕЛЕН, а не желателен — он стоит на 011/012/013, и все три приняты. Двусторонняя подпись ACTZ делается так, чтобы односторонний случай ADR-017 (proposed) позже ДОБАВЛЯЛСЯ, а не ломал сделанное.
СЛЕДСТВИЕ ВТОРОЕ И НЕПРИЯТНОЕ: объём 1.9 собран по трём ADR из двенадцати принятых. ADR-020, 021, 022, 023 не оценивались никогда, и два из них лежат вплотную к самым дорогим блокам релиза: 023 «полнота покрытия SPEC» — к задаче TC как артефакта, 022 «контролируемый синтаксис требований» — к контрактному контуру. Заведено задачей four-accepted-adrs-were-never-assessed; TC и ACTZ поставлены ПОСЛЕ неё ребром.
ОЦЕНКИ СЛОЖНОСТИ, ВЫСТАВЛЕННЫЕ В #189 (семнадцать задач 1.9 были без оценки): complex — actz, final-tz, at-acceptance, separation-of-duties, adapt-dual-signature, tc-as-a-first-class, p8, one-implementation-per-command; medium — at-red-routing, spec-closed-list, p9, nothing-detects-standard-moved, our-evidence-otel; simple — test-proliferation (детектор уже есть с флагом --check), pytest-asyncio, full-lane, ci-never-runs. После этого в 1.9 НЕ ОСТАЛОСЬ неоценённых задач.
