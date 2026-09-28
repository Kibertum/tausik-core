---
slug: todo-md-otstal-na-dva-reliza-i-vytesnen
title: "TODO.md отстал на два релиза и вытеснен порождённым ROADMAP.md"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/publication_snapshot.py"
  - "tests/test_publication_snapshot.py"
  - "tests/test_publish_cli.py"
  - "tests/test_docs_links_resolve.py"
  - "tests/conftest.py"
  - "docs/en/publishing.md"
  - "docs/ru/publishing.md"
scope_paths:
  - TODO.md
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T15:44:54Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

У вопроса «куда идёт TAUSIK» один адрес: либо TODO.md поддерживается, либо его роль переходит порождённому ROADMAP.md и он уходит. Сейчас документ утверждает, что выпущен 1.7.0 и в работе 1.8.

## Acceptance Criteria

1. Названо решение: поддерживать или упразднить. 2. Если упразднить — ссылки на TODO.md из docs publishing и publication_snapshot сняты вместе с файлом, иначе останется висячая цитата. 3. Висячая ссылка на отсутствующий tausik_systemwide_analysis.md исчезает в любом из двух исходов. 4. НЕГАТИВНЫЙ: содержимое про 2.0 (Global MCP, решение #94) не теряется — оно переезжает в решение или в эпик, а не пропадает вместе с файлом.

## Plan

## Rollback

git revert: TODO.md возвращается вместе со ссылками на него; содержимое про 2.0 к тому моменту уже записано решением, поэтому откат ничего не теряет.

## Journal

- 2026-09-28T15:41:49Z [implementation] — AC verified. AC-1 (упразднить или обновить): упразднён — git rm TODO.md; его работу делает порождённый ROADMAP.md, решение записано. AC-2 (ссылки сняты вместе с файлом): publication_snapshot.EXCLUDED_FROM_PUBLIC_SNAPSHOT потерял строку TODO.md, docs/{en,ru}/publishing.md переписали строку таблицы на TAUSIK-plan-1.9.md, живые тесты conftest.DORMANT_ON_PUBLIC_SNAPSHOT, test_docs_links_resolve, test_publication_snapshot (3 места), test_publish_cli — все переведены на существующий файл. Сводка grep по исходникам: ни одной живой ссылки, остались только CHANGELOG (история) и порождённые профили. AC-3 (правило не переживает файл): test_the_rules_are_the_ones_decision_368_named зафиксировал суженный список — молчаливое возвращение правила упадёт тестом. AC-4 (ничего не потеряно): содержание 2.0 живёт в решении #94 и активных эпиках v2-global-mcp/v2-client. Лента: 12053 passed, 30 skipped, 0 deselected, 185s. Гейт comment_history_refs сработал на моём же комментарии (235 > 234) — переписал без номера решения, номер живёт в журнале и CHANGELOG.
