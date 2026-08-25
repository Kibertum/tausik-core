---
slug: podpis-dokazyvaet-kto-kontent-skan-chto-dve-nezavisimye
title: "Подпись доказывает КТО, контент-скан — ЧТО: две независимые проверки скилла"
type: pattern
tags:
  - ed25519
  - security
  - skills
  - supply-chain
  - unicode
task: l26-skill-supply-chain-threat
edges: []
---

Для supply-chain магазина скиллов/плагинов ed25519-подпись издателя (supply_verify_install.check_skill_signature в install_skill) и КОНТЕНТ-скан прозы — ОРТОГОНАЛЬНЫ и оба обязательны. Подпись доказывает КТО опубликовал, но не ЧТО спрятано в markdown, который агент читает буквально: скрытые инструкции в U+E0000 tag-block / zero-width / bidi проходят подпись подписанного-но-скомпрометированного издателя и весь warn-adoption-путь. Детектор scripts/skill_content_scan.py (scan_skill_tree) вшит в choke point copy_skill ДО копирования файлов, блокирует. Дополняет brain_scrubbing._ZERO_WIDTH_RE (тот СТРИПает для brain-блоклиста и не знает U+E0000; здесь ДЕТЕКТИМ+БЛОКИРУЕМ). FP-контроль: ведущий BOM толерируется. Полная threat-model: docs/{en,ru}/skill-supply-chain-threat-model.md.
