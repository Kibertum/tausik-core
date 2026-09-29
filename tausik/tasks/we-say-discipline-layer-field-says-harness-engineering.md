---
slug: we-say-discipline-layer-field-says-harness-engineering
title: "Мы называем себя discipline layer, поле называет эту дисциплину harness engineering — и не находит нас"
status: blocked
epic: release-110-deferred-from-19
story: release110-owner-priorities
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
depends_on:
  - readme-is-a-wall-not-a-path
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#95"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
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

- 2026-09-29T21:27:02Z [implementation] — Text part done: 'Where it sits' paragraph (harness engineering = loop+tools+context+control; TAUSIK is NOT a harness, it is the verification/control layer on top; differentiator: nothing is done without evidence) in README.md, README.ru.md, docs/en/architecture.md, docs/ru/architecture.md. AC-1 ✓ AC-2 ✓ AC-5 ✓ (287 doc tests incl tests/test_code_counts.py) AC-6 ✓ (term absent from bootstrap/ and CLI parsers). Open: AC-3 GitHub topics on the mirror and AC-4 PRs into curated lists are OUTWARD actions -> owner.
