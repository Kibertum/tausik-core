---
slug: l26-agents-md-istochnik-pravdy-build-full-body-statika
task: l26-agents-md
date: "2026-07-23"
edges: []
---

## Decision

l26-agents-md источник правды: build_full_body (статика) + TAUSIK DB (dynamic, зеркалится в оба); паттерн тонкого указателя отклонён

## Rationale

TAUSIK уже держит статическое тело обоих файлов в синхроне из bootstrap_templates.build_full_body (единый источник; CLAUDE.md и AGENTS.md — пиринговые рендеры для разных аудиторий: Claude vs 30+ инструментов). DYNAMIC-секция (state проекта) генерируется из TAUSIK DB через update-claudemd и зеркалится в оба файла (resolve_sibling_targets). Индустриальный паттерн «AGENTS.md-источник + тонкий CLAUDE.md-указатель» НЕ принят: он добавил бы индирекцию без выгоды — каждый хост читает свой файл, и синхронизация уже решена шаблоном. Завершение фикса: живой AGENTS.md репо предшествовал маркерам (preserve-if-exists), поэтому маркеры добавлены вручную; шаблон уже их содержит (регресс-тест). AC4: CLAUDE.md компактен — под ориентиром ~200 строк, действий не требуется.
