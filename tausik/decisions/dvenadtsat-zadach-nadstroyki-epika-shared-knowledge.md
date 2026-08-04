---
slug: dvenadtsat-zadach-nadstroyki-epika-shared-knowledge
task: r18-scope-boundary-shared-knowledge
date: "2026-08-03"
edges: []
---

## Decision

Двенадцать задач надстройки эпика shared-knowledge ВЫНЕСЕНЫ В 1.9 явным решением, а не молча (исполнение #217): brainh-audit, brainh-semantic-search, brainh-capture-ux, l26-memory-decay, kb-global-promote, km-stable-identity-backfill, km-topics-aliases-index, km-retrieval-first-write-path, km-memory-lint-report, km-promote-mechanical-checks-blocking, lanes-changelog-fragments, brainh-reliability. Ни одна не блокирует тег: ядро общей базы закрыто и несёт entry_uuid нативно, замер #187 показал извлечение на потолке, гейт changelog работает на последовательной полосе.

## Rationale

Проверено по каждой: post-#217 решения, называющего эти задачи, НЕ существует ни одного. #191 переспецифицировал semantic-search, но не поместил в релиз; #195 выносил decay, но #202 вернул; #154 объявлял km-stable-identity-backfill блокером kb-global-schema, а kb-global-schema закрыта и knowledge_db.py несёт entry_uuid на всех трёх общих таблицах — основание разряжено. Правильно вынесенные задачи 1.9 несут префикс [1.9] в заголовке; ни у одной из этих его нет.
