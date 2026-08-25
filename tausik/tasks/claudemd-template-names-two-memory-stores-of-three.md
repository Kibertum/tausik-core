---
slug: claudemd-template-names-two-memory-stores-of-three
title: "Шаблон CLAUDE.md называет два хранилища памяти из трёх: общая база 1.8 не попала в таблицу маршрутизации"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "bootstrap/bootstrap_templates.py"
  - "bootstrap/**"
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Шаблон, который bootstrap раскладывает в КАЖДЫЙ проект, называет все три хранилища памяти и правило выбора между ними.

## Acceptance Criteria

1. Таблица маршрутизации памяти в build_full_body называет ТРИ хранилища: память проекта, общую базу знаний 1.8 и auto-memory агента. Заголовок «two systems» исправлен вместе с содержимым — он и есть утверждение.
2. Правка доезжает до ВСЕХ шаблонов, которые тикет GitLab #6 перечисляет: CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md. Форма закрывается перечислением из кода.
3. Названо, ПОЧЕМУ это не мелочь: главная возможность 1.8 отсутствует на двери, которая раскладывается в каждый проект. Это тот же дефект «главное не названо на входе», который мы правили в README, whats-new и changelog 1.8 — но эта дверь ведёт к КАЖДОМУ пользователю.
4. НЕГАТИВНЫЙ сценарий: тест сверяет число хранилищ в шаблоне с фактическим числом маршрутов памяти в коде, чтобы расхождение не могло вернуться молча.

## Plan

## Rollback

git revert коммита; правка в одном шаблоне

## Journal
