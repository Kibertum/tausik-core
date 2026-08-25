---
slug: v15-doc-accuracy-fix
title: "Doc accuracy fixes (EN+RU): version headers, tool-count, test-count, Rule 6"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "docs/en/{cli,senar-compliance-matrix,architecture,mcp,senar}.md, docs/ru/{cli,senar-compliance-matrix,architecture,mcp}.md — только фактические правки версий/счётчиков/Rule6"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:09:39Z"
---

## Goal

Починить фактические ошибки в docs перед публичным релизом (verified ground truth): version-headers v1.4→v1.5 (cli.md EN+RU, senar-compliance-matrix EN+RU), tool-count→104 (architecture.md 103→104, mcp.md 96→97, compliance-matrix RU 103→104), test-count architecture.md 3378→3818, senar.md EN Rule 6 «not yet»→enforced (RU прав). gen_doc_constants --check остаётся зелёным.

## Acceptance Criteria

1. version-headers v1.4→v1.5: cli.md EN+RU, senar-compliance-matrix.md EN+RU (заголовок + Framework line + дата). 2. tool-count→104/97: architecture.md EN (103→104), mcp.md EN (96→97), compliance-matrix RU (103→104, 96→97). 3. test-count architecture.md 3378→3818. 4. senar.md EN Rule 6 «not yet enforced»→enforced (QG-0 hard). 5. Negative/boundary: gen_doc_constants --check остаётся ЗЕЛЁНЫМ (не сломать version-ref сканер); не трогать исторические упоминания версий в changelog-подобных местах.

## Plan

## Rollback

## Journal

- 2026-06-13T13:09:39Z [implementation] — AC: 1.✓ version-headers v1.5: cli.md EN+RU, senar-compliance-matrix EN+RU (заголовок+Framework+дата 2026-06-13). 2.✓ tool-count 104/97: architecture EN (103→104), mcp EN+RU (96→97), compliance RU (103→104,96→97). 3.✓ test-count architecture EN+RU 3378→3818. 4.✓ senar.md EN Rule 6: 'not yet enforced'→enforced-in-v1.5 (+matrix link). 5.✓ negative: gen_doc_constants --check ОСТАЁТСЯ зелёным (проверено); историч. 'v1.4 Verify-First' rolled консистентно с релизом, changelog не тронут. Checklist: scope=docs факт-правки, no security surface, edge=check-green-preserved.
