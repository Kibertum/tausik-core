---
slug: release-19-notes-page-does-not-exist-yet
title: "Заметок к 1.9 не существует: восемь изменений поведения живут только в CHANGELOG"
status: done
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
relevant_files:
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
scope_paths:
  - "docs/ru/whats-new-1.9.md"
  - "docs/en/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-08T10:02:53Z"
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

AC1. СТРАНИЦЫ СУЩЕСТВУЮТ В ОБЕИХ ЯЗЫКОВЫХ ВЕРСИЯХ И СРАЗУ. docs/ru/whats-new-1.9.md и docs/en/whats-new-1.9.md появляются одним заходом — одноязычный выпуск 1.8 уже показал, чем кончается «потом переведём».

AC2. РАЗДЕЛ ЛОМАЮЩИХ ИЗМЕНЕНИЙ ЕСТЬ ЕДИНСТВЕННЫЙ ИСТОЧНИК ТЕКСТА ТЕГА. Он назван таковым на самой странице, чтобы текст в теге и текст в репозитории не могли разойтись — ровно тот дефект, которым заблокирована release-18-breaking-change-notes.

AC3. СОСТАВ ОТОБРАН ЗАМЕРОМ ПО ЖИВОМУ CHANGELOG, А НЕ СПИСКОМ ИЗ ЗАДАЧИ. Замер #189 назвал восемь изменений; с тех пор в Unreleased накопилось 163 записи. Страница, собранная по устаревшему списку, была бы тем же классом дефекта, который она чинит.

AC4. КАЖДОЕ НАЗВАННОЕ ИЗМЕНЕНИЕ ОТВЕЧАЕТ НА ВОПРОС «КАСАЕТСЯ ЛИ ЭТО МЕНЯ». Формат 1.8 сохраняется: было / стало / кого касается. Перечисление без этого ответа заставляет читателя проверять всё.

AC5 (НЕГАТИВНЫЙ). СТРАНИЦА НЕ ПЕРЕСКАЗЫВАЕТ CHANGELOG. 163 записи в заметки не переносятся; отбирается то, что меняет опыт обновления, и это правило записано на самой странице. Пересказ полного списка сделал бы страницу нечитаемой и неотличимой от файла, который пользователь и так не открывает.

AC6 (НЕГАТИВНЫЙ). НИ ОДНО ИЗМЕНЕНИЕ НЕ ОБЪЯВЛЯЕТСЯ ЛОМАЮЩИМ БЕЗ ОСНОВАНИЯ. В Unreleased ровно одна запись помечена ЛОМАЮЩИМ; раздел не раздувается за счёт того, что таковым не является. Проверяется сверкой с разметкой CHANGELOG.

AC7. МАШИНА СВЕРЯЕТ, ЧТО СТРАНИЦА НЕ ОТСТАЛА. Тест требует существования обеих страниц, наличия раздела ломающих изменений и того, что КАЖДАЯ запись, помеченная ЛОМАЮЩИМ в CHANGELOG, названа на странице. Иначе следующее ломающее изменение снова останется только в CHANGELOG.

AC8. ГРАНИЦА. Язык заметок к тегу здесь не решается (release-notes-language-policy-is-unstated); слом умолчания хуков в список не вносится до исхода своей задачи; сам тег не выставляется.

## Plan

## Rollback

Две новые страницы документации, кода не трогают. Откат — удаление файлов; поведение продукта не зависит от них.

## Journal

- 2026-09-08T10:02:21Z [implementation] — Верификационный чек-лист (SENAR Rule 5): AC-1: ✓ tests/test_release_notes_1_9.py::TestThePagesExistInBothLanguagesAtOnce::test_the_page_is_there AC-2: ✓ tests/test_release_notes_1_9.py::TestThePagesExistInBothLanguagesAtOnce::test_it_says_the_section_is_the_source_of_the_tag_text AC-3: ✓ состав отобран по живому CHANGELOG (163 записи в Unreleased против восьми из замера #189); схема 44 → 58 взята сравнением с тегом v1.8.0, а не из списка AC-4: ✓ формат «было / стало / касается ли это меня» сохранён у ломающего изменения, как в 1.8 AC-5: ✓ tests/test_release_notes_1_9.py::TestThePageIsNotTheChangelog::test_it_carries_far_fewer_entries_than_the_changelog AC-6: ✓ tests/test_release_notes_1_9.py::TestTheBreakingSectionIsNotPadded::test_it_holds_no_more_items_than_the_changelog_marks AC-7: ✓ tests/test_release_notes_1_9.py::TestEveryBreakingEntryReachesTheNotes::test_each_one_is_named_on_the_page AC-8: ✓ язык заметок к тегу не решался, слом умолчания хуков в список не внесён, тег не выставлялся Domain: страницы проверены не только тестом — состав сверен с настоящим CHANGELOG обоих языков и с настоящей историей git (SCHEMA_VERSION у тега v1.8.0 равен 44, сейчас 58, отсюда «четырнадцать миграций»). Полный набор 9923 passed. Negative: AC-5 и AC-6 — негативные и прогнаны: страница краснеет, если превратится в копию CHANGELOG, и краснеет, если раздел ломающих раздуется сверх того, что CHANGELOG таковым помечает.
