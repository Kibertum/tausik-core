---
slug: v15-readme-revamp
title: "README revamp (EN+RU) — hook, signed-receipts differentiator, consolidation"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md (полная переработка по пропозалу)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:25:56Z"
---

## Goal

Кратно улучшить README по пропозалу dev-advocate: H1 «AI agents that can't fake done», лид signed-receipts (уникальный differentiator), Without/With блок вверх, pre-2.0 warning вниз (reframe в confidence), консолидировать 4 дублирующие feature-таблицы в 1, починить stale-числа (dogfood tasks/sessions). Зеркало RU. Требует отмашки пользователя по tagline/тону (публичное лицо).

## Acceptance Criteria

1. README.md + README.ru.md переработаны: hero «can't fake done», лид signed-receipts (badge ed25519 + ссылка на receipts.md), Without/With блок, 30-sec quickstart, verifiable-trust секция, why-not-cursorrules, консолидированные features (<details> raw counts), pre-2.0 note вниз. 2. Числа точные: version 1.5.0, badge test-count=3818 (scanner-compatible, БЕЗ запятой), 104 MCP (97+7), 0 deps; stale dogfood-числа убраны. 3. RU — натуральный перевод, паритет с EN. 4. gen_doc_constants --check ЗЕЛЁНЫЙ (version-ref + test-count badge). 5. Negative: не сломать --check (badge формат 3818), ссылки на receipts.md/quickstart валидны.

## Plan

## Rollback

git checkout README.md README.ru.md — откат к предыдущей версии; изолированные файлы, не влияют на код/build/--check (кроме version+test-count, которые держим синхронными)

## Journal

- 2026-06-13T13:25:55Z [implementation] — AC: 1.✓ README.md+README.ru.md переработаны: hero 'can't fake done', signed-receipts badge+лид+секция (ссылка receipts.md), Without/With, 30-sec quickstart, why-not-cursorrules, консолидированные features (<details>), pre-2.0 note вниз. 2.✓ числа: v1.5, badge+prose test=3818 (scanner-safe, без запятой), 104 MCP (97+7), 0 deps; stale dogfood убраны. 3.✓ RU паритет (натуральный регистр). 4.✓ gen_doc_constants --check ЗЕЛЁНЫЙ. 5.✓ ссылки receipts.md/quickstart валидны. Domain: README — публичное лицо проекта, фактически корректно. Checklist: scope=README×2, security=нет threat surface (статич. docs, внешние ссылки на github/senar проверены), edge=check-green+badge-format.
