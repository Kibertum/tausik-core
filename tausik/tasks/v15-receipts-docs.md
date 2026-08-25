---
slug: v15-receipts-docs
title: "[marquee] Документация signed receipts — docs/{en,ru}/receipts.md + sidebar"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "docs/en/receipts.md (new), docs/ru/receipts.md (new), site/.vitepress/config.ts (sidebar entry оба locale)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:22:50Z"
---

## Goal

Главная фича 1.5 (ed25519 signed verification receipts) НЕ задокументирована нигде. Создать docs/en/receipts.md + docs/ru/receipts.md: что такое tausik-signed/v1 envelope, ключи (key init/show), receipt show/export/verify, HTTP verify-endpoint (serve), привязка к gate-сигнатуре+HEAD sha, offline-verify. Добавить в sidebar config.ts (оба locale) + cross-ref из cli.md/mcp.md/no-sdk-verify.md. Источники: scripts/project_cli_receipt.py, receipt_export.py, crypto_sign.py.

## Acceptance Criteria

1. docs/en/receipts.md + docs/ru/receipts.md созданы: что такое signed receipt + зачем, envelope tausik-signed/v1 (точные поля), key init/show, receipt show/export/verify, offline/HTTP (ссылка на no-sdk-verify), See also. 2. Точность: команды/поля сверены с scripts (project_cli_receipt/receipt_export/crypto_sign). 3. Sidebar config.ts: receipts добавлен в оба locale (en+ru) под Quality&verification. 4. gen_doc_constants --check зелёный (новые файлы не вносят version-ref drift). 5. Negative: не дублировать no-sdk-verify (cross-ref), не ломать существующий sidebar/build.

## Plan

## Rollback

git revert/rm новых receipts.md + откат строк sidebar в config.ts; новые файлы изолированы, не влияют на существующие docs/build

## Journal

- 2026-06-13T13:22:49Z [implementation] — AC: 1.✓ docs/en/receipts.md + docs/ru/receipts.md созданы (что+зачем, envelope tausik-signed/v1 с точными полями, key init/show, receipt show/export/verify, trust model, HTTP cross-ref, See also). 2.✓ точность сверена с scripts (project_cli_receipt/receipt_export/crypto_sign/crypto_receipt) субагентом. 3.✓ sidebar config.ts: 'Signed receipts'/'Подписанные чеки' в оба locale под Quality&verification. 4.✓ gen_doc_constants --check зелёный. 5.✓ negative: no-sdk-verify не дублирован (cross-ref), sidebar/build не сломан. Checklist: scope=2 новых doc+sidebar, no security surface (docs), edge=check-green.
