---
slug: verify-prints-a-handle-the-close-is-bound-to-refuse
title: "GitLab #15: в проекте без ключа verify чеканит и печатает verify-handle с готовой командой, а task done его отвергает «carries no receipt»"
status: planning
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/verify_run_record.py, scripts/render_verify.py, harness/claude/mcp/project/ (рендер verify), tests/, docs/ru/receipts.md, docs/en/receipts.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Правила валидации handle (verify_handle_rules.py) не смягчать; freshness lookup не менять."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Тикет GitLab #15 (владелец, kibertum-org на 1.8.0): `verify --task … --no-tests-expected` в проекте без `tausik key init` печатает «Receipt: not emitted — no project key», а двумя строками ниже «Verify handle: 159.…  Present it: task done … --verify-handle 159.…»; предъявление ровно этой команды даёт «QG-2 … verify run #159 carries no receipt, so there is nothing to validate». Инструкция гарантированно ведёт в отказ — лишний цикл для агента, следующего напечатанному буквально. ЗАМЕР, смена #251: scripts/verify_run_record.py:164-190 — `entitled` считается из describe_run_command + exit_code + files + allow_handle и НЕ зависит от исхода emit_signed_receipt; `_mint` вызывается при `entitled and expires_at` даже когда статус выпуска квитанции ≠ STATUS_SIGNED. scripts/render_verify.py::handle_lines печатает «none — not presentable (no declared files, all gates skipped, or a security-sensitive scope)» — причины «нет ключа» в перечне нет. Побочное наблюдение тикета — MCP и CLI расходятся в том, презентабелен ли прогон без исполнившегося гейта — проверить и, если расходятся, свести к одному месту. Починка: handle чеканится ТОЛЬКО когда квитанция подписана; без ключа handle не печатается вовсе, вместо блока «Present it:» — одна строка с причиной («no project key — run `tausik key init` for signed receipts, or close without --verify-handle») и верной командой закрытия; условие презентабельности читают и CLI, и MCP из одной функции.

## Acceptance Criteria

AC-1: в проекте без ключа `verify --task` не чеканит handle (verify_handle отсутствует в отчёте) и печатает одну строку с причиной «no project key» и верной командой закрытия без --verify-handle; блок «Present it:» отсутствует. AC-2: в проекте с ключом поведение прежнее: handle чеканится, печатается, принимается task done (существующие тесты test_verify_handle_integration зелёные). AC-3: НЕГАТИВ: провал подписи при наличии ключа (STATUS ≠ signed) тоже не чеканит handle — условие «квитанция подписана» одно, не «ключ есть». AC-4: MCP tausik_verify и CLI отвечают одинаково на прогоне без ключа (HANDLE: none с той же причиной) — доказано тестом, читающим оба рендера одной фикстурой. AC-5: мутация — вернуть чеканку без проверки статуса квитанции — краснит тест AC-1. AC-6: signed verify; CHANGELOG EN/RU; docs/{ru,en}/receipts.md называют условие.

## Plan

## Rollback

git revert; handle снова чеканится без квитанции (прежнее поведение).

## Journal
