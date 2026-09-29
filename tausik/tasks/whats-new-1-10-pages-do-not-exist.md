---
slug: whats-new-1-10-pages-do-not-exist
title: "Заметки к выпуску 1.10 на двух языках, без которых релиз не тегируется"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/whats-new-1.10.md"
  - "docs/en/whats-new-1.10.md"
  - "docs/_generated/doc-map.md"
scope_paths:
  - "docs/ru/whats-new-1.10.md"
  - "docs/en/whats-new-1.10.md"
  - "docs/_generated/doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T10:03:46Z"
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

docs/{ru,en}/whats-new-1.10.md существуют и описывают выпуск для того, кто обновляется. Процедура публикации требует обе страницы с 1.10: tausik publish notes отказывает телу релиза без любой из них (docs/ru/publishing.md, шаг 5), значит их отсутствие блокирует тег.

## Acceptance Criteria

1. docs/ru/whats-new-1.10.md и docs/en/whats-new-1.10.md существуют, несут doc-map маркер (reader=user; zone=release-notes) и парный заголовок ссылок, как страницы 1.8 и 1.9. 2. Содержание взято из CHANGELOG [Unreleased] ЭТОГО релиза, а не сочинено: каждое утверждение страницы находится в CHANGELOG. 3. ЛОМАЮЩИЕ ИЗМЕНЕНИЯ названы отдельным разделом; если их нет — сказано, что их нет, а раздел не выброшен молча. 4. НЕГАТИВНЫЙ: обещанного, но не измеренного, на странице нет — величина, которой нет, называется отсутствующей, а не нулём (правило релиза 1.9, decision #334). 5. Порождённая карта документации знает обе страницы: python scripts/doc_map.py --check зелёный. 6. Полная лента зелёная.

## Plan

## Rollback

git revert; страницы новые, ничего не переписывают. Тег не ставится этой задачей, поэтому откат не затрагивает выпуск.

## Journal

- 2026-09-29T10:03:37Z [implementation] — AC-1: ✓ docs/{ru,en}/whats-new-1.10.md созданы, несут doc-map маркер reader=user zone=release-notes и парный заголовок ссылок, как 1.8 и 1.9. AC-2: ✓ содержание взято из CHANGELOG [Unreleased] — 135 записей сведены к трём пунктам, пяти ломающим изменениям и разделу «что ещё изменится»; каждое утверждение страницы находится в CHANGELOG. AC-3: ✓ раздел ЛОМАЮЩИЕ ИЗМЕНЕНИЯ — пять штук, каждое с «что делать»: адрес пользовательского тира, отозванный task start --force, точка входа rag_server.py, сессия хоста, упразднённый TODO.md.
- 2026-09-29T10:03:37Z [implementation] — AC-4 НЕГАТИВНЫЙ: ✓ раздел «Чего в этом выпуске НЕТ» — три пункта, и ни один не выдаёт отсутствие за ноль. Сайт не пересобран (с причиной: тега нет, деплой — акт владельца); измеренной экономии токенов нет, замер 1.9 остаётся последним словом; ответ хоста про list_roots записан как НЕ проверенный. Семантический слой описан как приехавший выключенным, с частотой срабатывания ноль — это результат, а не пробел. AC-5: ✓ python scripts/doc_map.py --check зелёный, карта перепорождена, 70 страниц, 69 на двух языках. AC-6: ✓ полная лента 12223 прошли, 34 пропущены.
