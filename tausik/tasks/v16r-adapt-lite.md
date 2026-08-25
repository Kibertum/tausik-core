---
slug: v16r-adapt-lite
title: "[P1] ADAPT: full RENAR §7 — forward interpretation + 7 backward findings + dual signature + delta"
status: done
epic: v16-renar-core
story: v16r-artefacts
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "scripts/backend_migrations_v36.py, scripts/backend_schema_adapts.py, scripts/backend_crud_adapts.py, scripts/service_adapts.py, scripts/project_cli_adapts.py, scripts/project_parser_adapts.py (новые); правки: backend_schema.py(SCHEMA_VERSION 36), backend_migrations.py, backend_init.py, project_backend.py, project_service.py, project.py, project_parser.py, service_task.py(task_show adapts); MCP: tools_adapt.py+handlers_adapt.py ×3 зеркала + tools.py/handlers.py ×3 регистрация; tests/test_adapts.py; doc-counts: docs/{en,ru}/mcp.md, README.md, README.ru.md, docs/README.md, AGENTS.md, gen_doc_constants.py constants.json."
scope_exclude: "gmcp-*/v2-* (global-MCP 2.0); .tausik/keys; письмо Walko; не редактировать .claude/ scripts напрямую кроме MCP-зеркал; не трогать существующие spec-таблицы (только additive)."
relevant_files:
  - "scripts/service_adapts.py,scripts/backend_crud_adapts.py,scripts/backend_migrations_v36.py,tests/test_adapts.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T21:33:20Z"
---

## Goal

Полноценный ADAPT-артефакт по renar.tech v1.0-draft §7.4-7.6 (path A, decision #102/#103 — «lite» дропнут как противоречащий §7.12.3). Forward interpretation §7.4.3 (per-ТЗ-секция) + 7 категорий backward findings (closed list §7) + dual signature §7.5 (client + architect; architect = ed25519 из v15-crypto над canonical body) + delta workflow §7.6 (parent-adapt supersede + dangling-ref guard §7.6.4).

## Acceptance Criteria

1. Schema v36: adapts + adapt_interpretations(§7.4.3) + adapt_findings(closed-7 CHECK) + adapt_signatures(role client|architect, PK adapt+role) + adapt_links(adapt↔task/spec) + fts_adapts; migration v36 чисто применяется на v35-БД (foreign_key_check пуст) И fresh-DB путь создаёт те же объекты.
2. Backward-findings категории — ровно closed-7 (contradiction/gap/hidden-assumption/feasibility/regulatory/terminology/scope), enforced на двух слоях (service ValueError→ServiceError + DB CHECK).
3. CLI `tausik adapt` create/interpret/finding/sign/show/list/delta/link/unlink/search/delete; MCP-зеркала (9 tools) синканы в 3 локации (.claude + harness/claude + harness/cursor).
4. Dual signature §7.5: architect-подпись = ed25519 (crypto_sign над canonical_bytes тела ADAPT), верифицируема; client-подпись = recorded name+ts. adapt sign role=architect без project key → ServiceError (не traceback).
5. Delta §7.6: adapt delta создаёт ADAPT с parent-adapt, родитель→superseded; NEGATIVE: link на superseded ADAPT = FATAL ServiceError (§7.6.4 dangling-ref guard).
6. task_show показывает связанные ADAPT (mirror specs). doc-counts: project MCP 107→116, обновить mcp.md/README*/docs/README/AGENTS.md + gen_doc_constants.py; check_docs/doc-drift зелёный; pytest зелёный.
NEGATIVE-сценарии (обяз.): bogus category→IntegrityError на DB-слое; sign architect без ключа→ServiceError; link на superseded→ServiceError; malformed FTS→ServiceError.

## Plan

## Rollback

git revert коммита задачи (всё additive — новые таблицы/файлы, без ALTER на существующих). Миграция v36 необратима в downgrade-смысле, но безопасна: DROP TABLE adapts/adapt_* + откат SCHEMA_VERSION→35 при необходимости. БД .tausik/tausik.db не мигрируется в проде до релиза.

## Journal

- 2026-06-13T21:01:30Z [planning] — QG-0 PREP (renar.tech v1.0-draft sverka 2026-06-14, §07-adapt). ⚠ DRIFT FOUND — see decision #102: §7.12.3 'промежуточных light-форм не существует' → RENAR has NO lite ADAPT. Task premise ('lite' artefact) is a TAUSIK divergence, NOT RENAR. BLOCK on resolution before coding: (A) full ADAPT per standard / (B) lite as documented divergence / (C) defer. CONFIRMED RENAR ADAPT spec (verbatim, for whichever path): • 7 backward-findings categories (closed list, §7): contradiction, gap, hidden-assumption, feasibility, regulatory, terminology, scope. → CHECK-constraint closed list (mirror SPEC-types pattern). • Forward interpretation (§7.4.3) fields: tz-ref 'ТЗ§N.N' (mandatory), citation/paraphrase (mandatory), engineering-interpretation (mandatory), term-mapping client→engineer (if applic), built-in-scenarios (if implied), scope-boundary in/out (mandatory). • Dual signature (§7.5): approval.client-signature{signed-by,signed-at V6-ISO} + approval.architect-signature{signed-by,signed-at}. Client confirms intent-match+answers-final; architect confirms findings-resolved+feasible. → reuse v15-crypto ed25519 (crypto_sign/crypto_keys) for agent(architect) sig; human sig = recorded name+timestamp (or detached ed25519 if human key available). • Lifecycle: ADAPT not created if reviewer verdict 'no findings, no clarifications' (§7.4.1.1); else full body §7.8.2 + dual sig + lifecycle §7.4.5. • Delta workflow (§7.6): delta-TZ 'TZ-YYYY-NNN-delta-N' (immutable, signed V6) → reviewer audits → if findings: ADAPT-NNN-delta-N with parent-adapt:ADAPT-NNN + full approval; if none: skip delta-ADAPT, BR/SR/SPEC reference source.tz-section:TZ-delta-N directly. Dangling ref to superseded ADAPT = FATAL (§7.6.4). SCOPE SKETCH (if approved, mirrors spec-types build): migration v36 (adapts table + adapt_findings child closed-7 + adapt_signatures + link adapt↔SPEC/task; FTS); backend_crud_adapts.py mixin; service_adapts.py (closed-list + sig orchestration via crypto_sign); project_cli_adapts.py (adapt create/sign/show/delta); project_parser_adapts.py; MCP tools_adapt.py+handlers_adapt.py (+3 mirrors + doc-count bump per memory #146); delta workflow + dangling-ref guard. BIG — budget full review. Naming note: if path (B), keep slug; if (A), consider renaming task to v16r-adapt (drop 'lite').
- 2026-06-13T21:17:13Z [implementation] — Path A реализован. Schema v36 (adapts+interpretations+findings(closed-7)+signatures(dual)+links+fts_adapts), backend_crud_adapts, service_adapts (sign via ed25519 над canonical body, delta supersede, §7.6.4 dangling-guard, frozen-after-sign), CLI `adapt` 12 subcmd, 9 MCP tools синканы в 3 зеркала (.claude+harness/claude+harness/cursor), task_show.adapts. project MCP 107→116. Smoke e2e зелёный: create/interpret/finding, bogus-cat→IntegrityError, dual-sign→signed+verify valid, body frozen, delta→parent superseded, link-superseded→FATAL, architect-nokey→ServiceError.
- 2026-06-13T21:32:10Z [implementation] — VERIFICATION-CHECKLIST (QG-2): [tests] pytest full suite 3804p/8s (before review-fixes) + test_adapts.py 36p (after) + spec/doc-count 37p; [lint] ruff clean на всех новых файлах; [types] mypy clean (6 файлов); [drift] gen_doc_constants --check OK (mcp counts 116/123/130 + test_count 3933), scripts-drift .claude=0; [smoke] e2e create→interpret→finding→dual-sign→verify(valid)→delta(parent superseded)→link-superseded(FATAL)→nokey(ServiceError). ADVERSARIAL REVIEW (tausik-reviewer): 3 crit/7 high triaged — FIXED: fts_adapts в FTS-rebuild loop (#5), re-sign signed ADAPT блокируется (#6), delta_n NULL guard (#7), signature_set обёрнут try/except→ServiceError (#2), тест на эфемерных ключах (CI-safe), DDL-комменты (SET NULL/полиморфная связь). ОСОЗНАННО НЕ принято: unlink/verify не в MCP (9 tools by AC; CLAUDE.md допускает CLI-only verbs); delta-atomicity (single-process SQLite, documented limitation); _canonical_body `or {}` (unreachable — adapt_sign guard'ит existence до _architect_sign).
- 2026-06-13T21:32:58Z [implementation] — AC1 ✓ schema v36 (adapts+interpretations+findings+signatures+links+fts_adapts); test_migration_v36_creates_tables_clean + test_fresh_backend_has_adapt_tables (foreign_key_check пуст). AC2 ✓ closed-7 categories на 2 слоях: test_invalid_category_rejected_at_service + _at_db (IntegrityError); test_finding_categories_closed_seven. AC3 ✓ CLI adapt 12 subcmd + 9 MCP tools синканы 3 зеркала; test_cli_parser_* + test_mcp_dispatch_registers_adapt_tools. AC4 ✓ dual-sig ed25519: test_dual_signature_completes_and_verifies (valid) + test_architect_signature_without_key_is_service_error. AC5 ✓ delta supersede + §7.6.4: test_delta_supersedes_parent + test_link_to_superseded_is_fatal. AC6 ✓ task_show.adapts: test_task_show_includes_linked_adapts; doc-counts 116/123/130 + test_count 3933, gen_doc_constants --check OK. NEGATIVE все покрыты (bogus-cat→IntegrityError, nokey→ServiceError, superseded-link→FATAL, malformed-FTS→ServiceError, re-sign→ServiceError). Full pytest 3804p/8s; ruff+mypy clean; tausik-reviewer 3crit/7high triaged+fixed.
- 2026-06-13T21:33:15Z [implementation] — VERIFICATION CHECKLIST (QG-2 substantial): - scope: только additive — 6 новых scripts + 8 wiring-правок + MCP ×3 зеркала + tests + doc-counts; spec-таблицы не тронуты; .cursor не трогался (lite-профиль, прецедент spec-задачи). - tests: full pytest 3804 passed/8 skipped; test_adapts.py 36 passed; spec+doc-count 37 passed; ruff clean; mypy clean (6 файлов). - security: architect-подпись ed25519 над canonical_bytes тела (детерминизм, верифицируема); приватный seed только в .tausik/keys (gitignore); nokey→ServiceError; closed-lists на 2 слоях (service+DB CHECK); SQL только параметризованный; signature_set обёрнут try/except→ServiceError. - edge-cases: bogus category→IntegrityError(DB); architect sign без ключа→ServiceError; link на superseded→FATAL ServiceError (§7.6.4); re-sign signed ADAPT→ServiceError; malformed FTS→ServiceError; delta_n NULL guard; body frozen after sign; FTS delete-trigger чистит индекс. - review: tausik-reviewer (adversarial) 3crit/7high — triaged, реальные пофикшены (fts_adapts rebuild, re-sign guard, delta_n guard, signature_set wrap, ephemeral-keys test); осознанные отклонения задокументированы.
- 2026-06-13T21:33:20Z [implementation] — AC1-6 ✓ + все NEGATIVE покрыты (см. checklist в notes). Full pytest 3804p/8s; ruff+mypy clean; tausik-reviewer triaged+fixed; doc-counts 116/123/130, test_count 3933.
