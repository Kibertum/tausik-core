---
slug: documentation-is-refactored-around-one-map
title: "Вся документация перестроена вокруг одной карты: читатель, пара языков, место в навигации, числа из констант — и тест, который держит карту"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: complex
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/ru/research/*.md"
  - "docs/_generated/*"
  - README.md
  - README.ru.md
  - "scripts/doc_*.py"
  - "scripts/gen_*.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - doc-language-pairs-have-drifted-and-three-are-unpaired
completed_at: null
---

## Goal

Замер смены #266: docs/ru — 60 страниц (10 200 строк), docs/en — 59 (10 000 строк); hooks-events.md есть только по-русски, at-generation-procedure.md — только по-английски; пять пар разошлись по структуре (задача doc-language-pairs-have-drifted-and-three-are-unpaired); 13 страниц упоминают Notion, ушедший в 1.9 (configuration, knowledge-store, memory-merge-guidelines, team-state-in-git, whats-new-1.8/1.9, en/cli); исследований 13 RU против 1 EN; страницы не различают читателя (пользователь фреймворка, агент, сопровождающий ядра), а порядок чтения задан только README. Опыт 1.9: карта документации для ухода Notion (docs/ru/research/notion-departure-doc-map.md — 45 файлов, четыре зоны, шесть сквозных утверждений) сработала; здесь тот же метод для всей документации. Цель: одна карта (порождаемый файл в docs/_generated или docs/README) с полем «читатель», парой языков, местом в навигации и владельцем зоны; каждая страница либо в карте, либо удалена; сквозные утверждения (две базы знаний, нет Notion, версии стандартов, счётчики) звучат одинаково везде и берутся из constants.json; тест держит карту.

## Acceptance Criteria

1. Замер ДО в журнале: число страниц по языкам, непарные, разошедшиеся пары, страницы с Notion, страницы без читателя — командой, вывод приложен.
2. Карта документации: каждая страница docs/ru и docs/en имеет запись с читателем (user / agent / maintainer), парой, разделом навигации и зоной; тест сравнивает дерево с картой в обе стороны; НЕГАТИВНЫЙ: страница вне карты или запись без файла — красный тест.
3. Непарных страниц ноль (перевод или удаление с записью причины); разошедшиеся пары сведены (детектор паритета переводов зелёный).
4. Упоминаний Notion вне исторических записей whats-new — ноль; исторические помечены как история.
5. Сквозные утверждения (перечень в карте) проверяются тестом по тексту на каждой странице, где они звучат; числа — из constants.json, не набраны.
6. Читательские входы: три страницы-входа (пользователь, агент, сопровождающий) с порядком чтения; README ссылается на них.
7. Страницы, признанные мёртвыми, удалены с записью в CHANGELOG; ссылки на них не осталось (проверка ссылок зелёная).
8. CHANGELOG EN+RU; карта используется задачей сайта для навигации.

## Plan

## Rollback

git revert; удалённые страницы возвращаются тем же revert'ом.

## Journal
