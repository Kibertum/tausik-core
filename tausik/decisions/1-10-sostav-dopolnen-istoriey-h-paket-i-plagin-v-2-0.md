---
slug: "1-10-sostav-dopolnen-istoriey-h-paket-i-plagin-v-2-0"
task: null
date: "2026-09-23"
edges: []
---

## Decision

1.10 — СОСТАВ ДОПОЛНЕН ИСТОРИЕЙ H; ПАКЕТ И ПЛАГИН — В 2.0. Владелец, смена #266: «пакет и плагин надо в 2.0; с остальным согласен; перерабатывай план, задачи в GitHub и здесь и автономно приступай к разработке 1.10; включить полный рефакторинг сайта, всей документации, гигиену проекта». Исполнено: история release110-site-docs-and-hygiene (H): сайт из документации ядра релиза, карта документации, гигиеническая уборка с храповиками, плюс 13 задач гигиены из отложенных корзин; pypi-package-uvx-tausik-init, claude-code-plugin-and-catalog-listing, package-skills-and-mcp-as-one-plugin — в v2gm-packaging, sign-layer-over-agent-plugins — в v2gm-surfaces. Разработка начинается с истории E. Дополняет #376. Состав: release110-sessions-are-not-gates, release110-verification-is-cheap, release110-the-update-reaches-the-user, release110-tracker-promises, release110-rag-and-memory-tell-the-truth, release110-senar-15-claimed-honestly, release110-renar-11-first-party-and-spec-uc, release110-site-docs-and-hygiene

## Rationale

Замеры для H: сайт собран 06.07.2026 на TAUSIK 1.5.8 по старому адресу ядра, 106 ручных ссылок навигации; документация 60 RU / 59 EN с непарными и разошедшимися страницами, 13 упоминаний Notion; 4468 файлов под git, 3139 — проекция; tools.py 1075 строк.
