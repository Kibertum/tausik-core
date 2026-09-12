---
slug: verify-ownership-test-explicit-utf8
title: "Явно указать UTF-8 в тесте ownership verifier"
status: active
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_verify_commit_ownership.py"
  - "tests/test_hook_encoding.py"
scope_paths:
  - "tests/test_verify_commit_ownership.py"
  - "tausik/tasks/verify-ownership-test-explicit-utf8.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить воспроизводимый failure test_hook_encoding: тест ownership verifier открывает текстовый файл с явной UTF-8 кодировкой, сохранив своё поведение.

## Acceptance Criteria

AC-1: tests/test_verify_commit_ownership.py не содержит чтения текстового файла без explicit encoding='utf-8'. AC-2: encoding gate проходит на реальном файле. AC-3 (negative): fixture semantics и ownership assertions не меняются.

## Plan

[{"step": "\u0412\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u0435\u0441\u0442\u0438 encoding gate \u043d\u0430 \u0446\u0435\u043b\u0435\u0432\u043e\u043c \u0442\u0435\u0441\u0442\u0435.", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0442\u043e\u043b\u044c\u043a\u043e \u044f\u0432\u043d\u044b\u0439 UTF-8 \u0430\u0440\u0433\u0443\u043c\u0435\u043d\u0442 \u043a \u0447\u0442\u0435\u043d\u0438\u044e fixture.", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c targeted ownership \u0438 encoding tests, \u0437\u0430\u0442\u0435\u043c signed verify.", "done": false}]

## Rollback

Revert the one test-fixture encoding argument.

## Journal

- 2026-09-12T10:54:05Z [implementation] — Reproduction no longer finds an encoding-inheritance violation in the current ownership test: targeted encoding gate and ownership suite are green. No source edit is justified; inspect provenance before declaring the originally reported failure resolved.
- 2026-09-12T10:54:21Z [implementation] — Added explicit encoding='utf-8' to the subprocess fixture helper. Targeted encoding gate plus ownership suite pass; ruff is clean.
