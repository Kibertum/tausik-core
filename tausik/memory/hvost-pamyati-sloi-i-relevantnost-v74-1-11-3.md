---
slug: hvost-pamyati-sloi-i-relevantnost-v74-1-11-3
title: "Хвост памяти: слои и релевантность (v74, 1.11.3)"
type: context
tags:
  - "memory,tail,relevance,layers,hygiene"
task: memory-tail-by-relevance-not-recency
edges: []
---

memory-tail-by-relevance-not-recency закрыт: миграция v74 дала memory hit_count/last_hit_at/layer/pinned + memory_hygiene_snapshots. Чтение = явный memory show (поиск НЕ считается). Слои: core (pinned или >=20 чтений), hot >=8, warm >=2, cold (1 чтение или свежая), frozen (0 чтений и >90 дней). CLI: memory hygiene (dry-run по умолчанию, --yes со снапшотом, --revert одним ходом), memory pin/unpin. Хвост CLAUDE.md остаётся по свежести, пока в config.json не стоит memory_tail_by_relevance=true — opt-in осознанно: счётчики стартуют с нуля, включать после накопления. AC1-числа: 18 строк на 895 записей; за 60 сессий хвост обернулся полностью (0 общих id), 16.5% записей мелькнули один раз. Доказательство: tests/test_memory_hygiene.py (20 passed) + verify #3567.
