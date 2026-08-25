---
slug: nikogda-ne-obhodit-qg-2-cherez-auto-verify-gates-disable-v
title: "Никогда не обходить QG-2 через auto_verify/gates_disable в config.json"
type: convention
tags:
  - discipline
  - dogfooding
  - qg-2
  - senar
  - verify
task: v14-strategic-review-10-1-4
edges: []
---

При разработке самого TAUSIK категорически запрещено обходить QG-2 (`task done`) через правки `auto_verify` или `gates_disable`/отключение gates в `.tausik/config.json`. Это обман фреймворка и нарушение dogfooding.

Why: Пользователь поймал на этой практике в сессии #41/#42. Если task_done висит часами — это БАГ gate runner (scoped pytest, verify cache, parallelism), а не повод его глушить. SENAR Rule 5 (verify against criteria) + Rule 9.1 (нет кода без задачи) обязывают честно проходить gates.

How to apply:
- Медленный task_done → defect-таска на service_verification.py / gate_runner / verify cache, НЕ правь config.
- При doc-only задаче — используй per-task scope/scope_exclude, не глобальный auto_verify.
- При session capacity overshoot — `task start --force` (audit trail) допустим: это другой класс гейта.
- Перед коммитом, затрагивающим config.json — проверь, не отключены ли gates, и поставь обратно если случайно отключил.
- В commit-обзорах флагов на bypass: grep `auto_verify.*false`, `gates.*disabled` в diff config.json.
