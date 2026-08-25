---
slug: v156-github-release
title: "v1.5.6 github orphan release + commit CLAUDE.md stamp + gitlab push"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "git (gitlab push, github orphan force-push, тег, gh release); CLAUDE.md commit"
scope_exclude: "исходный код (всё уже в релиз-коммите 698f2d0)"
relevant_files:
  - CHANGELOG.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-20T08:20:55Z"
---

## Goal

Закоммитить хвостовой стамп CLAUDE.md и запушить на gitlab. Затем выложить v1.5.6 на публичное github-зеркало Kibertum/tausik-core: orphan-коммит (plumbing, фикс. сообщение), completeness-check, leak-аудит дерева, force-push через +refspec (memory #181), тег v1.5.6, gh release create с секцией CHANGELOG [1.5.6].

## Acceptance Criteria

1. CLAUDE.md стамп закоммичен и запушен на gitlab main (push-ok ticket). 2. Orphan-коммит O собран plumbing'ом из дерева HEAD с сообщением 'TAUSIK v1.5.6 — discipline layer for AI coding agents' (формат прошлых релизов). 3. Completeness: список файлов orphan == github/main + новые файлы объяснены (нет тихих потерь). 4. Leak-аудит дерева ПЕРЕД push: нет [вычеркнуто: internal-host]/glpat-/oauth2:/ghp_/sk-ключей/docs/audit/_internal/*.pem/*.key/.env. 5. Force-push github через +refspec (memory #181, без флага --force), тег v1.5.6, gh release create v1.5.6 --repo Kibertum/tausik-core с секцией CHANGELOG [1.5.6]. 6. НЕГАТИВНЫЙ: если leak-аудит находит секрет/токен — НЕ пушить на github (Ошибка блокирует выкладку), сначала вычистить дерево.

## Plan

[{"step": "\u041a\u043e\u043c\u043c\u0438\u0442 CLAUDE.md \u0441\u0442\u0430\u043c\u043f f12eee9 + push gitlab main", "done": true}, {"step": "Orphan O=6b1fe05 \u0438\u0437 \u0434\u0435\u0440\u0435\u0432\u0430 HEAD (\u0444\u0438\u043a\u0441. \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435)", "done": true}, {"step": "Completeness: \u043d\u0435\u0442 \u043f\u043e\u0442\u0435\u0440\u044c; 5 \u043d\u043e\u0432\u044b\u0445 \u0444\u0430\u0439\u043b\u043e\u0432 \u043e\u0431\u044a\u044f\u0441\u043d\u0435\u043d\u044b", "done": true}, {"step": "Leak-\u0430\u0443\u0434\u0438\u0442: \u0442\u043e\u043b\u044c\u043a\u043e false-positive (secret_scan \u043f\u0430\u0442\u0442\u0435\u0440\u043d\u044b + test-\u0444\u0438\u043a\u0441\u0442\u0443\u0440\u044b), \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0445 \u0441\u0435\u043a\u0440\u0435\u0442\u043e\u0432 \u043d\u0435\u0442", "done": true}, {"step": "Force-push github +refspec: 8084cc9\u21926b1fe05 main + \u0442\u0435\u0433 v1.5.6; \u0443\u0434\u0430\u043b\u0451\u043d \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 gh-tag", "done": true}, {"step": "gh release create v1.5.6 (CHANGELOG notes); orphan verified single-commit", "done": true}]

## Rollback

github: старый снапшот остаётся под тегом v1.5.5 (8084cc9); можно force-push обратно на предыдущий orphan. gitlab: revert стамп-коммита.

## Journal

- 2026-06-20T08:20:54Z [implementation] — AC verified: AC-1: ✓ CLAUDE.md стамп f12eee9 закоммичен (mypy OK), push gitlab main 698f2d0..f12eee9. AC-2: ✓ orphan O=6b1fe05 собран plumbing'ом из дерева HEAD, сообщение 'TAUSIK v1.5.6 — discipline layer for AI coding agents' (формат прошлых релизов). AC-3: ✓ completeness: comm -13 (github/main \ orphan) пуст — потерь нет; 5 новых файлов объяснены (4 мои v1.5.6: service_doctor_kilo.py + 3 теста; 1 prior-session qwen-design-doc). AC-4: ✓ leak-аудит: git grep по дереву — только false-positive (secret_scan.py детектор-паттерны + test fixture sk-...), реальных [вычеркнуто: internal-host]/glpat-/токенов НЕТ; .tausik/.claude вне дерева (gitignored). AC-5: ✓ force-push +refspec (без --force флага): github main 8084cc9→6b1fe05 + тег v1.5.6; gh-tag удалён локально; gh release create v1.5.6 → https://github.com/Kibertum/tausik-core/releases/tag/v1.5.6. AC-6: ✓ НЕГАТИВНЫЙ соблюдён: push на github выполнен ТОЛЬКО после прохождения leak-аудита (реальных секретов нет). Domain: orphan verified rev-list count=1, parent=none (true orphan, истории нет); локальный gitlab-тег v1.5.6=bb7ff90→698f2d0 (full history) не затронут — дуальная схема memory #181 соблюдена.
