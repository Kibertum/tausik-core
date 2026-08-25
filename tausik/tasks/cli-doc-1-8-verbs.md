---
slug: cli-doc-1-8-verbs
title: "Document 1.8 verbs in cli.md (state/sync/memory graph --format)"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: "docs/ru/cli.md, docs/en/cli.md"
scope_exclude: null
relevant_files:
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:02:05Z"
---

## Goal

Ship doc+command parity before 1.8: docs/ru/cli.md (and EN) have no 'state export/import' or 'sync' entry, and 'memory graph' omits '--format mermaid'. CLAUDE.md forbids arg-guessing, so an undocumented verb is a dead end for the agent. Document all shipped 1.8 verbs.

## Acceptance Criteria

AC1. docs/ru/cli.md и docs/en/cli.md содержат раздел про `tausik state export` (флаги --out, --check) и `tausik state import` (флаги --out, --dry-run) с примерами вызова.
AC2. Оба cli.md документируют `tausik sync` как алиас `state import` (команда после git pull/checkout).
AC3. Строка `memory graph` в обоих cli.md дополнена флагом `--format {table,mermaid}` (был только --type/--id/--relation); default table (сверено с project_parser.py:214).
AC4. НЕГАТИВ: docs_lint / doc constants --check зелёные — нет ссылок на несуществующие флаги; счётчики команд в доке совпадают с кодом.
AC5. EN и RU синхронизированы структурно — новые разделы присутствуют на обоих языках с одинаковым набором подкоманд/флагов.

## Plan

## Rollback

## Journal

- 2026-07-26T21:58:30Z [implementation] — Сверено с кодом: state export (--out/--check), state import & sync alias (--out/--dry-run) в project_parser_state.py; memory graph --format {table,mermaid} default table в project_parser.py:214 (НЕ text/mermaid). Доки cli.md ru/en не содержат state/sync и не упоминают --format у memory graph. Правлю доки под фактический CLI.
- 2026-07-26T22:01:36Z [implementation] — AC1 ✓ Раздел "Состояние в git"/"State in git" в docs/ru/cli.md + docs/en/cli.md: state export (--out/--check), state import (--out/--dry-run) с примерами. AC2 ✓ sync документирован как алиас state import в обоих. AC3 ✓ memory graph дополнен --format {table,mermaid} default table в обоих (сверено project_parser.py:214). AC4 ✓ doc constants --check OK; tests/test_doc_drift_scanners.py 23 passed; task-done gate bootstrap_drift PASS (мирроры .claude синхронны). AC5 ✓ EN/RU структурно симметричны — оба получили секцию state/sync + строку --format. Docs-parity для уже-changelogged команд → no_changelog.
- 2026-07-26T22:02:03Z [implementation] — AC1 ✓ Раздел "Состояние в git"/"State in git" в docs/ru/cli.md + docs/en/cli.md: state export (--out/--check), state import (--out/--dry-run) с примерами. AC2 ✓ sync документирован как алиас state import в обоих. AC3 ✓ memory graph дополнен --format {table,mermaid} default table в обоих (сверено project_parser.py:214). AC4 ✓ doc constants --check OK; tests/test_doc_drift_scanners.py 23 passed; bootstrap_drift PASS. AC5 ✓ EN/RU структурно симметричны. Verify run #1444 (no-tests-expected, docs-only), receipt signed. Docs-parity для уже-changelogged команд → no_changelog.
