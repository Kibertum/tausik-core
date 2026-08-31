---
slug: inventar-adr-renar-pereschitannyy-mashinoy-prinyatyh
title: "Инвентарь ADR RENAR, пересчитанный машиной: принятых тринадцать, оценено семь, непроверенных шесть"
type: context
tags:
  - adr
  - conformance
  - inventory
  - renar
task: four-accepted-adrs-were-never-assessed
edges:
  - relation: supersedes
    target_type: memory
    target: inventar-adr-renar-prinyatyh-dvenadtsat-otsenivali-tri
---

ЗАМЕНЯЕТ СЧЁТ ИЗ ПАМЯТИ #432 («принятых двенадцать, оценивали три»). Снято машинно со статусов ВСЕХ 22 файлов ../../standards/renar/research/decisions/ в сессии #191, а не по памяти.

СОСТАВ КОРПУСА (номера 008 и 014 отсутствуют физически):
  accepted (12): ADR-001, 003, 005, 006, 007, 009, 012, 013, 020, 021, 022, 023
  accepted-pending-adr-012 (1): ADR-011 — условие ВЫПОЛНЕНО, так как 012 accepted => фактически принятых ТРИНАДЦАТЬ
  superseded (2): ADR-002, 004
  proposed (7): ADR-010, 015, 016, 017, 018, 019, 024 — не реализуются по решению #255
  12 + 1 + 2 + 7 = 22, сходится.

ОЦЕНЕНО СЕМЬ: ADR-011, 012, 013 (на них построен эпик 1.9) и ADR-020, 021, 022, 023 (задача four-accepted-adrs-were-never-assessed, решение #278).

НЕПРОВЕРЕННЫХ ШЕСТЬ: ADR-001 implements-edge-br-subsystem, ADR-003 ai-agent-as-primary-author, ADR-005 core-concept-overview, ADR-006 adapt-reactive, ADR-007 adapt-temporal-multiplicity-supersession, ADR-009 adversarial-review-record. Поиск по БД по каждому даёт НОЛЬ результатов при заведомо исправном поиске (контрольные «ADR-020» и «ADR-013» находят задачи, память и решения).

ЧЕМУ ЭТОТ ПЕРЕСЧЁТ УЧИТ, И ЭТО ГЛАВНОЕ. Задача four-accepted-adrs-were-never-assessed заводилась ПРОТИВ частичного чтения корпуса — и сама стояла на частичном счёте: её посылка «не оценивались четыре» молча считала шесть остальных разобранными. Пропуск оказался вдвое больше заявленного. Неписаная оценка неотличима от отсутствующей: «наверное, смотрели раньше» есть тот же тихий пропуск, только в отчёте о его устранении.

Задача на остаток: [[six-more-accepted-adrs-have-no-assessment-record]]. Смежное: [[nothing-detects-that-the-standard-moved-under-us]] — механизм, чтобы отставание находила проверка, а не человек с глазами.
