---
slug: odin-sink-odin-obschiy-guard-a-ne-proverka-per-path-install
title: "Один sink → один общий guard, а не проверка per-path (install/activate дрейф)"
type: pattern
tags:
  - fail-open
  - guard
  - install-activate-drift
  - security
  - skills
task: review-s146-skill-activate-fail-open-gate-filesize
edges: []
---

Когда ДВА+ пути ведут в один и тот же sink (skill install/copy_skill И activate/skill_activate копируют в .claude/skills/), security-контроль обязан быть ОДНИМ общим guard'ом, который зовут все пути — не дублироваться и не жить на одном пути. Рецидив-класс: у TAUSIK этот дрейф install/activate случался ТРИЖДЫ — сначала strip-filter (skill_tree_ignore), потом проверка ed25519-подписи, потом (сессия #146) invisible-Unicode скан — каждый раз контроль сначала жил только в copy_skill, а skill_activate имел свою копию shutil.copytree и оставался незащищённым. Фикс: skill_content_scan.assert_skill_tree_clean зовут ОБА. Правило: (1) контроль на sink = один helper на sink; (2) регресс-тест на КАЖДЫЙ путь (test_skill_activate_supply_chain зеркалит test_skill_content_scan); (3) для security-скана контента декод всегда errors=replace, не strict (strict молча пропускает файл с битым байтом, а copytree его всё равно приземляет = fail-open); (4) охват скана = ВСЕ файлы, доезжающие до sink, не только .md. См. [[podpis-dokazyvaet-kto-kontent-skan-chto]].
