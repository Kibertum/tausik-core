---
slug: sign-layer-over-agent-plugins
title: "Подпись поверх Agent Plugins: закрыть пробел, который стандарт объявил своей будущей работой"
status: planning
epic: standards-window
story: intoto-and-plugins
complexity: complex
role: architect
stack: null
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/**"
  - "docs/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Существует работающий tausik plugin sign / verify для формата Agent Plugins v1.0.0, и предложение по нему внесено в спецификацию со ссылкой на живую реализацию.

## Acceptance Criteria

1. Основание процитировано и проверено: FUTURE_CONSIDERATIONS.md спецификации Agent Plugins, раздел Provenance verification, дословно — «v1.0.0 does not specify how clients or users can verify the origin or integrity of a plugin. A future version may define: cryptographic signature verification for published plugins; attestation chains linking a published plugin to its source repository and build; client policies for requiring signatures from trusted publishers».
2. `tausik plugin sign <dir>` строит DSSE-конверт поверх plugin.json и digest дерева плагина; `tausik plugin verify` проверяет офлайн, без установки TAUSIK у проверяющего.
3. Формат НЕ меняет plugin.json и не ломает совместимость: подпись кладётся в reverse-domain-директорию, которую спецификация прямо разрешает.
4. Инструмент проверен на РЕАЛЬНЫХ плагинах из публичных каталогов, не на своих фикстурах. Число проверенных названо.
5. НЕГАТИВНЫЙ сценарий: плагин с испорченным деревом, подменённым plugin.json и просроченной подписью ОТВЕРГАЕТСЯ каждым из трёх случаев по отдельности, с разными кодами отказа.
6. НЕГАТИВНЫЙ сценарий: инструмент, не сумевший вынести вердикт (нечитаемый файл, отсутствующий ключ), БЛОКИРУЕТ, а не пропускает.
7. ЗАВИСИМОСТЬ: ход выполняется ПОСЛЕ закрытия задачи offline-checkable-is-claimed-but-only-a-service-is-shipped. Публиковать инструмент проверки, ссылаясь на README, обещающий несуществующую офлайн-проверку, ЗАПРЕЩЕНО.

## Plan

## Rollback

Инструмент отдельный, ядра не касается; откатывается удалением подкоманды

## Journal
