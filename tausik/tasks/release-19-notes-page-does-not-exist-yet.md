---
slug: release-19-notes-page-does-not-exist-yet
title: "Заметок к 1.9 не существует: восемь изменений поведения живут только в CHANGELOG"
status: planning
epic: release-19-agent-effectiveness
story: the-loop-closes-outward
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР #189: СТРАНИЦЫ ЗАМЕТОК К 1.9 НЕ СУЩЕСТВУЕТ ВООБЩЕ. В docs/ru и docs/en есть только whats-new-1.8.md; файлов whats-new-1.9.* нет ни на одном языке. У 1.8 ровно эта страница была ЕДИНСТВЕННЫМ источником текста тега (записано в notes задачи release-18-breaking-change-notes) — у 1.9 источника нет.

ЧТО ИЗ ЭТОГО СЛЕДУЕТ. Изменения поведения 1.9 сегодня живут только в CHANGELOG.md и CHANGELOG.ru.md — то есть в файле, который пользователь при обновлении не открывает. Это ТОТ ЖЕ класс, что у заблокированной release-18-breaking-change-notes (там ломающее изменение трастовых тиров осталось в CHANGELOG и не попало в заметки к тегу), но пойманный ДО выпуска, а не после. Разница принципиальная: 1.8 уже нельзя починить без перевыпуска опубликованного тега, 1.9 ещё можно.

ВОСЕМЬ ИЗМЕНЕНИЙ ПОВЕДЕНИЯ, КОТОРЫЕ ОБЯЗАНЫ ДОЕХАТЬ ДО ЗАМЕТОК (все восемь есть в CHANGELOG обоих языков, ни одного нет в заметках, потому что заметок нет):
1. ruff теперь гоняется и на триггере verify, а не только на commit (### Changed — the `ruff` gate now also runs at `verify`).
2. Гейт без реализации и без команды теперь БЛОКИРУЕТ, а не молчит (### Fixed — a gate could fail to start, and say nothing, GitLab #9).
3. Отвергнутое переопределение команды гейта БЛОКИРУЕТ, а не подменяется дефолтом (там же, коммит 5a58b50).
4. drift-7 выдаёт статус undateable-verification вместо проглатывания недатируемого (### Fixed — drift-7 dated the link, not the verification; Sortula #49 -> наш #10, коммит 6eec011).
5. SCHEMA_VERSION 46 -> 47.
6. Новая команда `tausik audit evidence` (### Added — closure-receipt citations no longer rot in silence).
7. Выборка тестов резолвером пошла по ИМПОРТАМ — область дешёвого прогона стала шире (### Changed — scoped test selection follows IMPORTS).
8. Второй детектор храповика видимости краснит новый тест, недостижимый ни по имени, ни по импорту, ни по объявлению (### Changed — the visibility ratchet gained a second detector).
ДЕВЯТЫМ ПРОСИТСЯ слом умолчания хуков — если он войдёт в 1.9; у него своя задача the-breaking-flip-announced-to-an-external-author-has-no-task, и до её исхода в список он не вносится.

ЧТО ДЕЛАЕТСЯ: страницы docs/ru/whats-new-1.9.md и docs/en/whats-new-1.9.md по образцу 1.8, с разделом ЛОМАЮЩИЕ ИЗМЕНЕНИЯ / BREAKING CHANGES как ЕДИНСТВЕННЫМ источником текста будущего тега — чтобы текст в теге и текст в репозитории не могли разойтись.

СМЕЖНОЕ, НЕ СЛИВАТЬ СЮДА: release-notes-language-policy-is-unstated (на каком языке живут заметки к тегу — 1.8 вышел одноязычным) остаётся отдельной задачей; здесь она лишь ограничение: страницы делаются на обоих языках сразу.

## Acceptance Criteria

## Plan

## Rollback

Две новые страницы документации, кода не трогают. Откат — удаление файлов; поведение продукта не зависит от них.

## Journal
