---
slug: obem-1-9-zafiksirovan-vladeltsem-35-zadach-strogo-po-256-v
task: roadmap-artifact-predates-decision-256
date: "2026-08-31"
edges: []
---

## Decision

ОБЪЁМ 1.9 ЗАФИКСИРОВАН ВЛАДЕЛЬЦЕМ: 35 ЗАДАЧ, СТРОГО ПО #256. В релиз входят шесть историй ядра доказательства: gates-declare-what-they-prevent (9), evidence-primitives (7), renar-debt-implemented-wrong (7), renar-contract-contour (5), test-evidence-not-test-volume (4), standards-drift-detection (3). ИЗ РЕЛИЗА ВЫХОДЯТ 52 ЗАДАЧИ: guarantees-are-not-claude-only (12), knowledge-records-what-failed-19 (8), proof-and-positioning-outward (7) и весь эпик release-19-agent-effectiveness (25). Дорожная карта ПЕРЕВЫПУСКАЕТСЯ под #256 и ставится под git.

## Rationale

Это НЕ новое решение об объёме, а буквальное чтение уже принятого #256, до сих пор не применённое к бэклогу. #256 определяет 1.9 как рефакторинг ЯДРА ДОКАЗАТЕЛЬСТВА и прямо перечисляет периферию, которая НЕ трогается: задачи, сессии, память, brain, скиллы, роли. Отсюда выходят knowledge-records-what-failed-19 (память) и весь агентский эпик (путь агента). guarantees-are-not-claude-only есть буквально вопрос «работает ли у чужих», который #256 снял с версии. proof-and-positioning-outward — позиционирование, не доказательство.

АРИФМЕТИКА ВЫБОРА: при throughput 6.38 задач/смену 87 задач это ~14 смен, 35 задач ~6. Разница в восемь смен предъявлена владельцу на входе #200, а не за две смены до релиза.

ОТВЕРГНУТО: (1) оставить все 87 — потребовало бы отменить #256, вернув снятый вопрос; (2) взять эпик RENAR целиком (62) — сохраняет guarantees-are-not-claude-only, то есть ровно то, что #256 увёз; (3) отложить развилку — планирование по устаревшей карте дороже её починки.
