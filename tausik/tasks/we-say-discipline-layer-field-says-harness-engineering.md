---
slug: we-say-discipline-layer-field-says-harness-engineering
title: "Мы называем себя discipline layer, поле называет эту дисциплину harness engineering — и не находит нас"
status: planning
epic: release-110-proof-outward
story: proof-outward
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - README.md
  - README.ru.md
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

TAUSIK описан в терминах, которыми поле себя называет, и находится по ним — без потери того, чем он от поля отличается.

## Acceptance Criteria

1. Формулировка ЧЕСТНАЯ по четырёхэлементному определению харнесса (agent loop + tool interface + context management + control mechanisms): TAUSIK НЕ харнесс — цикл агента и интерфейс инструментов принадлежат Claude Code, cursor и прочим. Мы control и verification слой НАД чужими харнессами. Объявить себя харнессом было бы вторым ложным утверждением там, где мы только что чинили первое.
2. Слово discipline сохраняется как ОТЛИЧИЕ, а не как категория: категория — harness engineering, дифференциатор — verification-first.
3. Правка доезжает до обоих README, обеих главных страниц docs и до topics репозитория на зеркале.
4. Отправлены PR в кураторские списки поля (awesome-harness-engineering и аналоги) в секции, которым мы ДЕЙСТВИТЕЛЬНО соответствуем: верификация, память, права. Заявка в секцию, которой мы не соответствуем, ЗАПРЕЩЕНА — это тот же ложный сигнал, только чужими руками.
5. НЕГАТИВНЫЙ сценарий: ни одно существующее утверждение README не становится ложным ради нового словаря. Тест сходимости утверждений о числах и свойствах остаётся зелёным.
6. НЕГАТИВНЫЙ сценарий: если через год поле переименует дисциплину, переезд не должен требовать переписывания продукта — термин живёт в документах и topics, не в именах модулей и не в CLI.

## Plan

## Rollback

git revert коммита; правки только в документах

## Journal
