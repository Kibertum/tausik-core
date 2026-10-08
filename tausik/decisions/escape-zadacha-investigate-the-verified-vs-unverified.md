---
slug: escape-zadacha-investigate-the-verified-vs-unverified
task: investigate-the-verified-vs-unverified-escape
date: "2026-10-06"
edges: []
---

## Decision

Escape-задача investigate-the-verified-vs-unverified-escape: политику verify оставляем как есть; агрегатную строку by_verification читать только рядом со стратами by_complexity_and_verification; risk_score не использовать для маршрутизации (AUC 0.54 в обеих руках)

## Rationale

Парадокс 9.9% (138/1400) verified против 1.5% (6/395) unverified (Fisher p=8.8e-10) — не малая выборка и не вред verify: (1) левое цензурирование — практика defect_of началась 2026-04, на доапрельские закрытия не указывает ни один дефект, а 230/395 unverified это март; (2) лечение умерло — с июля QG-2 делает verify обязательным, unverified осталось 15 закрытий за 3 месяца. Era-clean разрез 6/98=6.1% против 117/856=13.7% сохраняет разрыв на исчезающей популяции без рычага. Внутри страт сложности разрыв тоже выживает (medium p=3.6e-7), но наследует смешение эпох. risk_score не дискриминирует ни в агрегате (0.5377), ни внутри verified (0.5411); сложность одна 0.5977.
