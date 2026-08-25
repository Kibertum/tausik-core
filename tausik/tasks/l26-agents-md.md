---
slug: l26-agents-md
title: "Довести поддержку AGENTS.md (сейчас начата и брошена)"
status: done
epic: landscape-2026-h2
story: l26-ecosystem
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - AGENTS.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "tests/test_update_claudemd_agents.py"
scope_paths:
  - AGENTS.md
  - "tests/test_update_claudemd_agents.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/service_claudemd.py"
  - "scripts/claudemd_writer.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-23T19:51:10Z"
---

## Goal

AGENTS.md выиграл слой always-on проектного контекста: свыше 60000 репозиториев, читается 30+ инструментами, под управлением Linux Foundation (AAIF) с 2025-12-09, намеренно без фронтматтера и схемы. Сложившийся паттерн: AGENTS.md как источник правды плюс тонкий CLAUDE.md со ссылкой на него. У TAUSIK поддержка НАЧАТА И БРОШЕНА — update-claudemd 2026-07-18 выдал предупреждение, что маркер DYNAMIC:START в AGENTS.md не найден, и пропустил файл. Задача: определить, кто источник правды, и довести генерацию до конца, чтобы предупреждение исчезло. Заодно проверить рекомендацию держать CLAUDE.md компактным (ориентир около 200 строк) — он грузится в КАЖДОЙ сессии, в отличие от скиллов, которые подгружаются по требованию.

## Acceptance Criteria

AC1. Определён и зафиксирован источник правды (decision): статическое тело обоих файлов — из bootstrap_templates.build_full_body (единый источник, CLAUDE.md/AGENTS.md — пиринговые рендеры для разных аудиторий); DYNAMIC-секция — из TAUSIK DB через update-claudemd, зеркалится в оба файла (resolve_sibling_targets). Паттерн «тонкий CLAUDE.md-указатель на AGENTS.md» НЕ принят — обоснование зафиксировано.
AC2. Генерация update-claudemd доведена до конца: предупреждение «маркер DYNAMIC:START в AGENTS.md не найден» больше не возникает — прогон update-claudemd проходит без warning (fails-then-passes).
AC3. Тест подтверждает наличие корректных DYNAMIC-маркеров и успешную запись динамической секции в целевой файл; регрессионный тест на build_full_body (шаблон новых проектов содержит маркеры).
AC4. Проверен ориентир компактности CLAUDE.md (~200 строк): текущее число строк зафиксировано (70) и решение принято.
AC5 (НЕГАТИВ/ГРАНИЦА): apply_dynamic_section на файл БЕЗ маркера возвращает (warning-msg, changed=False) и НЕ пишет файл; вызов update-claudemd на проекте без AGENTS.md не падает (sibling пропускается, не ошибка).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert; обновляется только CLAUDE.md как раньше

## Journal

- 2026-07-23T19:51:06Z [implementation] — AC verified: 1. ✓ источник правды зафиксирован (decision #167): build_full_body статика + TAUSIK DB dynamic зеркалится в оба; паттерн тонкого указателя отклонён 2. ✓ warning 'marker not found in AGENTS.md' исчез (fails-then-passes: до фикса warning был, после — update-claudemd чист, AGENTS.md dynamic заполнен) 3. ✓ test_update_claudemd_agents::TestRepoAndTemplateHaveMarkers (живые файлы + все context-tier шаблона содержат маркеры), 12 passed 4. ✓ CLAUDE.md 95 строк < 200 5. ✓ NEGATIVE: apply_dynamic_section без маркера→(warning,False) без записи (test_no_marker_is_skipped_not_error); update-claudemd без AGENTS.md не падает (test_no_agents_md_returns_only_primary). verify #1215 pytest PASS.
