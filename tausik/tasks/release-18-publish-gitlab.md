---
slug: release-18-publish-gitlab
title: "Выкладка 1.8: README под фактический релиз, PDF списка изменений на русском, публикация в GitLab и тег v1.8.0"
status: active
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: tech-writer
stack: null
tier: substantial
call_budget: 120
defect_of: null
scope: null
scope_exclude: "scripts/** — содержание релиза заморожено, эта задача только доносит его наружу"
relevant_files:
  - README.md
  - README.ru.md
  - "docs/en/whats-new-1.8.md"
  - "docs/ru/whats-new-1.8.md"
  - "docs/_generated/constants.json"
  - "tests/test_breaking_change_count_converges.py"
  - "scripts/docs_lint.py"
  - "scripts/audit_stale_docs.py"
  - "scripts/gen_doc_constants.py"
scope_paths:
  - README.md
  - README.ru.md
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/_generated/*.json"
  - "tests/test_breaking_change_count_converges.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
completed_at: null
---

## Goal

Довести 1.8 до опубликованного тега v1.8.0 в GitLab: README перестаёт называть заголовком релиза не тот заголовок, список изменений выходит человекочитаемым PDF на русском, 26 коммитов уезжают в origin, тег ставится на проверенное дерево.

## Acceptance Criteria

1. README.md называет заголовком 1.8 то же, что whats-new и заметки к тегу — общую базу знаний и конец серверной сессии — и упоминает шесть ломающих изменений со ссылкой на whats-new.
2. Русский README синхронен английскому по этому блоку, либо зафиксировано его отсутствие.
3. Список изменений 1.8 на русском собран в PDF, файл открывается, в исходнике ровно шесть заголовков ломающих.
4. Полный прогон pytest эксклюзивно: 0 failed, 0 errors.
5. Ветка release/1.8-batch-s126 отправлена в origin (GitLab), тег v1.8.0 создан и отправлен.
6. НЕГАТИВНЫЙ сценарий: расхождение счёта ломающих хотя бы в одном из шести мест БЛОКИРУЕТ тег; пуш и тег ЗАПРЕЩЕНЫ до устранения.
7. НЕГАТИВНЫЙ сценарий: непустой git status или ненулевой failed/errors в прогоне БЛОКИРУЮТ пуш и тег.

## Plan

## Rollback

git tag -d v1.8.0 && git push origin :refs/tags/v1.8.0; правки README и PDF откатываются git revert одного коммита.

## Journal

- 2026-08-04T06:59:09Z [implementation] — Старт: doctor All clean, дерево чистое, тега v1.8.0 нет, 26 коммитов не отправлены. Сходимость ломающих пересчитана вручную в пяти местах: 6=6=6=6=6.
- 2026-08-04T07:20:17Z [implementation] — Полный прогон ЭКСКЛЮЗИВНО: 6949 passed, 24 skipped, 140 deselected, 0 failed, 0 errors, 1046.89s. Критерий 4 закрыт. Ревью доков до тега нашло ТРИ расхождения, каждое блокирует тег по критерию 6-7: (A) whats-new EN и RU во вступлении говорят ПЯТЬ ломающих, а секций ШЕСТЬ. Тест test_breaking_change_count_converges сравнивает только заголовки '### N.' и число в прозе не видит — ровно тот провал, который описан в его же докстринге. (B) whats-new EN и RU в ломающем 2 требуют руками перенести базу (mkdir+mv), а код с 1.8 подхватывает её сам: adopt_legacy_store_if_present копирует со старого адреса при первом обращении и НЕ переносит. Заметки к тегу говорят верно, документация — нет. Исключение: при заданном TAUSIK_HOME автоподхват не выполняется, и вот там перенос действительно на пользователе. (C) README EN и RU называют заголовком 1.8 'состояние проекта едет в git', а заметки к тегу и whats-new — общую базу знаний и конец серверной сессии. Плюс бейдж '6630 тестов' при живых 6949.
