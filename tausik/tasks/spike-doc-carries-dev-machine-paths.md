---
slug: spike-doc-carries-dev-machine-paths
title: "Документ спайка несёт абсолютные пути машины и роняет гейт публикации"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: gmcp-spike-roots
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/research/global-mcp-spike.md"
scope_paths:
  - "docs/ru/research/global-mcp-spike.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T22:13:48Z"
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

Документ docs/ru/research/global-mcp-spike.md проходит гейт публикации: сырые логи сохраняют доказательную силу, но путь машины в них заменён, потому что абсолютный путь разработчика — класс утечки публичного снапшота (память #710).

## Acceptance Criteria

1. test_publication_snapshot.py::TestTheLiveTree::test_no_leak_class_survives_on_the_snapshot зелёный. 2. НЕГАТИВНЫЙ: замена не выхолащивает доказательство — в логе по-прежнему видно, что cwd РАВЕН корню проекта и что CLAUDE_PROJECT_DIR пуст; иначе документ перестаёт доказывать то, ради чего писался. 3. Сказано ЧТО заменено и почему, прямо в документе, а не только в истории коммитов.

## Plan

## Rollback

git revert; правка текстовая, поведения нет.

## Journal

- 2026-09-28T22:12:23Z [implementation] — AC-1: ✓ tests/test_publication_snapshot.py::TestTheLiveTree::test_no_leak_class_survives_on_the_snapshot зелёный; полная лента 12197 прошли, 30 пропущены. Находка была честной: гейт назвал 'dev-machine path' и один файл. AC-2 НЕГАТИВНЫЙ: ✓ заменены только ПРЕФИКСЫ путей. В логе по-прежнему видно, что cwd равен корню проекта (и это помечено прямо в логе стрелкой), что у одного сервера --project относительный, а у другого абсолютный и указывает на ДРУГОЙ проект, и что CLAUDE_PROJECT_DIR пуст. Все три вывода документа держатся. AC-3: ✓ врезка перед итоговой таблицей говорит, что заменено, чем и почему, со ссылкой на память #710.
- 2026-09-28T22:13:38Z [implementation] — Root cause (documentation): сырой лог вставлен в документ дословно, вместе с абсолютными путями машины, на которой снят. Класс утечки публичного снапшота — тот же, что память #710 записала про журнал задачи; документ исследования оказался вторым местом, куда лог попадает целиком, и правило про журнал на него никто не распространил. Prevention: правило формулируется не про журнал, а про ЛЮБОЕ место, куда попадает сырой вывод — при вставке лога префиксы путей заменяются сразу, а в документе пишется, что заменено. Проверять это отдельным гейтом не нужно: гейт публикации уже ловит класс и поймал именно так.
