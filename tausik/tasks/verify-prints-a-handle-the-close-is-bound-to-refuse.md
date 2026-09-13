---
slug: verify-prints-a-handle-the-close-is-bound-to-refuse
title: "GitLab #15: в проекте без ключа verify чеканит и печатает verify-handle с готовой командой, а task done его отвергает «carries no receipt»"
status: done
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
relevant_files:
  - "scripts/verify_run_record.py"
  - "scripts/render_verify.py"
  - "scripts/service_gates.py"
  - "tests/test_verify_handle_integration.py"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T12:53:22Z"
---

## Goal

Тикет GitLab #15 (владелец, kibertum-org на 1.8.0): `verify --task … --no-tests-expected` в проекте без `tausik key init` печатает «Receipt: not emitted — no project key», а двумя строками ниже «Verify handle: 159.…  Present it: task done … --verify-handle 159.…»; предъявление ровно этой команды даёт «QG-2 … verify run #159 carries no receipt, so there is nothing to validate». Инструкция гарантированно ведёт в отказ — лишний цикл для агента, следующего напечатанному буквально. ЗАМЕР, смена #251: scripts/verify_run_record.py:164-190 — `entitled` считается из describe_run_command + exit_code + files + allow_handle и НЕ зависит от исхода emit_signed_receipt; `_mint` вызывается при `entitled and expires_at` даже когда статус выпуска квитанции ≠ STATUS_SIGNED. scripts/render_verify.py::handle_lines печатает «none — not presentable (no declared files, all gates skipped, or a security-sensitive scope)» — причины «нет ключа» в перечне нет. Побочное наблюдение тикета — MCP и CLI расходятся в том, презентабелен ли прогон без исполнившегося гейта — проверить и, если расходятся, свести к одному месту. Починка: handle чеканится ТОЛЬКО когда квитанция подписана; без ключа handle не печатается вовсе, вместо блока «Present it:» — одна строка с причиной («no project key — run `tausik key init` for signed receipts, or close without --verify-handle») и верной командой закрытия; условие презентабельности читают и CLI, и MCP из одной функции.

## Acceptance Criteria

AC-1: в проекте без ключа `verify --task` не чеканит handle (verify_handle отсутствует в отчёте) и печатает одну строку с причиной «no project key» и верной командой закрытия без --verify-handle; блок «Present it:» отсутствует. AC-2: в проекте с ключом поведение прежнее: handle чеканится, печатается, принимается task done (существующие тесты test_verify_handle_integration зелёные). AC-3: НЕГАТИВ: провал подписи при наличии ключа (STATUS ≠ signed) тоже не чеканит handle — условие «квитанция подписана» одно, не «ключ есть». AC-4: MCP tausik_verify и CLI отвечают одинаково на прогоне без ключа (HANDLE: none с той же причиной) — доказано тестом, читающим оба рендера одной фикстурой. AC-5: мутация — вернуть чеканку без проверки статуса квитанции — краснит тест AC-1. AC-6: signed verify; CHANGELOG EN/RU; docs/{ru,en}/receipts.md называют условие.

## Plan

## Rollback

git revert; handle снова чеканится без квитанции (прежнее поведение).

## Journal

- 2026-09-13T12:51:13Z [implementation] — Сделано: verify_run_record чеканит хендл только при receipt_status == STATUS_SIGNED; иначе handle_out['no_handle_reason'] = no-key | error | expiry-unavailable | mint-failed → details → service_gates report → render_verify.handle_lines печатает «Verify handle: none — no project key … Close without --verify-handle: task done <slug> --ac-verified» (одна строка для no-key, другая для провала подписи); CLI и MCP делят verify_lines — расхождения из тикета нет по построению. МУТАЦИЯ: возврат условия «entitled and expires_at» → 3 новых теста красные. Ревью tausik-reviewer: 2 high — вставка абзаца ломала таблицу receipts.md (обе языковые) и сливала два разных сообщения в одно; исправлено (абзац после таблицы, оба сообщения названы); medium — литерал 'no-key' заменён константой STATUS_NO_KEY; 2 low — причины для expiry-unavailable и mint-failed добавлены. docs/{en,ru}/receipts.md, CHANGELOG EN/RU, whats-new 239.
- 2026-09-13T12:53:18Z [implementation] — AC-1 ✓ tests/test_verify_handle_integration.py::TestAKeylessRunEarnsNoHandle::test_no_key_means_no_handle_and_the_report_says_why — в проекте без ключа report без verify_handle, no_handle_reason == no-key; ::test_the_rendered_line_gives_the_command_that_works — «Verify handle: none — no project key …» и `task done t --ac-verified`, блока «Present it:» нет. AC-2 ✓ прежние 9 тестов файла (keyed project: чеканка, приём, одноразовость) зелёные без правок; verify этого (keyed) проекта чеканит #2587. AC-3 ✓ (НЕГАТИВ) ::test_a_signing_failure_with_a_key_present_earns_no_handle_either — STATUS_ERROR при наличии ключа → хендла нет, причина error; условие — «чек подписан», не «ключ есть». AC-4 ✓ CLI (project_cli_verify) и MCP (handlers_verification._handle_verify) рисуют одним render_verify.verify_lines — подтверждено ревьюером grep-ом по harness/claude/mcp/project: второго рендера хендла нет; тест рендера читает verify_lines той же фикстурой. AC-5 ✓ мутация «if entitled and expires_at:» → 3 failed, восстановление → 64 passed (журнал). AC-6 ✓ verify #2587 подписан; CHANGELOG EN/RU; docs/{en,ru}/receipts.md называют оба сообщения после таблицы отказов (ревью: абзац внутри таблицы ломал её — перенесён). Domain: агент в проекте без ключа больше не получает инструкцию, ведущую в гарантированный отказ; хендл — утверждение о подписанном чеке, и без чека его нет.
