---
slug: vosem-defektov-dostovernosti-signalov-obyavleny-vne-1-8
task: r18-orphans-triage-and-boundary
date: "2026-08-03"
edges: []
---

## Decision

Восемь дефектов достоверности сигналов ОБЪЯВЛЕНЫ ВНЕ 1.8 вслух, а не молчанием места хранения: task-update-accepts-empty-required-field, verification-checklist-detector-misses-the-form-it-asked-for, tool-call-syntax-leaks-into-entity-text, complexity-proxy-counts-state-projection, calibration-window-too-small-to-forecast, verify-cache-miss-reads-as-git-mismatch-instead-of-a-reason, ruff-format-is-not-gated-and-86-files-diverged, schema-index-drift-fresh-vs-migrated. Все восемь — реальные дефекты, ни один не отрицается. Основание выноса: ни один не меняет ПОВЕДЕНИЕ, которое получает пользователь 1.8; все портят сигнал, который фреймворк показывает СЕБЕ. Наоборот, три дефекта общей базы (origin_project с именами клиентов, невалидированный TAUSIK_HOME, формат тегов) ОСТАВЛЕНЫ В 1.8 и переведены в kb-global: они портят то, что 1.8 выпускает.

## Rationale

Переезд в истории эпика arch-debt-post-18 ('архитектурный долг ПОСЛЕ 1.8') сам по себе объявляет задачу вне релиза. Если сделать это молча, мы меняем одну невидимость на другую: вместо 'невидима для roadmap' получаем 'вынесена местом хранения'. #217 требует обратного — выносить отдельными решениями. Разделительная линия проведена по признаку 'портит выпускаемое поведение или собственный сигнал', а не по тяжести.
