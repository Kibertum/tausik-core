---
slug: the-tree-still-says-1-8-0-everywhere-while-shippin
title: "the tree still says 1.8.0 everywhere while shipping 1.9"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - "tests/test_audit_translation_drift.py"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - pyproject.toml
  - "scripts/tausik_version.py"
  - "tests/test_audit_translation_drift.py"
  - "docs/_generated/constants.json"
  - CLAUDE.md
  - AGENTS.md
  - QWEN.md
  - README.md
  - README.ru.md
  - "docs/README.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T21:13:51Z"
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

ПРОВЕРКА ГОТОВНОСТИ К ВЫПУСКУ. pyproject.toml:3 говорит version = '1.8.0'. Это ЕДИНСТВЕННЫЙ источник — docs/_generated/constants.json, CLAUDE.md и всё прочее выводятся из него gen_doc_constants.read_project_version. То есть дерево, выпускающее 1.9, целиком представляется как 1.8.0.

ЧЕГО ЖДАТЬ ОТ ПОДЪЁМА, И ЭТО ЧАСТЬ ЗАДАЧИ. doc_drift сверяет упоминания версии в README, AGENTS.md, CLAUDE.md и порождённых документах против источника. После подъёма покраснеет всё, что отстало, — и это не побочный ущерб, а СМЫСЛ: сейчас эти документы зелены только потому, что источник тоже отстал. Каждое покраснение разбирается по существу, а не глушится.

ГРАНИЦА: подъём версии в дереве — шаг подготовки, а не публикация. Тег не ставится, заметки не публикуются, на main ничего не уезжает: это решение владельца и действие наружу.

## Acceptance Criteria

AC-1. pyproject.toml несёт 1.9.0; порождённые константы пересобраны и согласованы (docs/_generated/constants.json и его копии в профилях сред).
AC-2. КАЖДОЕ покраснение doc_drift после подъёма разобрано по существу: либо документ поправлен, либо упоминание объявлено историческим с причиной. Ни одно не заглушено.
AC-3. НЕГАТИВНЫЙ СЦЕНАРИЙ: сканер версий обязан уметь покраснеть. Проверено подменой версии в документе — сканер называет файл и строку.
AC-4. Заметки к 1.9 и CHANGELOG говорят о 1.9.0 согласованно с pyproject.
AC-5. НИЧЕГО НЕ ПУБЛИКУЕТСЯ: тег не ставится, на main не пушится. Проверяется тем, что git tag не менялся.
AC-6. Полный прогон зелёный.

## Plan

## Rollback

## Journal

- 2026-09-08T21:13:48Z [implementation] — AC verified: AC-1: ✓ pyproject.toml несёт 1.9.0, scripts/tausik_version.py тоже (он держал литерал ОТДЕЛЬНО и был найден вторым сканером, а не первым). docs/_generated/constants.json пересобран, профили сред переразвёрнуты. AC-2: ✓ все ДЕСЯТЬ покраснений разобраны по существу. Значок версии в обоих README поднят до v1.9.0. Из списка возможностей убрана пометка '(v1.8)' у общей базы знаний — там она не нужна, это перечень того, что есть, а не история. Повествовательный раздел '## v1.8 — ...' переписан под 1.9 в обоих языках; история 1.8 остаётся в changelog и в whats-new-1.8.md, на которую раздел теперь ссылается. Ни одно упоминание не заглушено исключением. AC-3: ✓ КРАСНОЕ ДОКАЗАТЕЛЬСТВО: подменил значок на v1.7.0 — сканер назвал README.md:9 и версию; файл восстановлен, сканер снова даёт ноль. AC-4: ✓ раздел 1.9 в README согласован с whats-new-1.9.md и называет неизмеренное обещание рядом с обещанием: числа экономии нет, прибор его не производит (233 из 57251), базы сравнения нет. AC-5: ✓ НИЧЕГО НЕ ОПУБЛИКОВАНО: тег не ставился, на main не пушилось, вся работа на v1-9-wave. AC-6: ✓ verification_run #2345 зелёный. Полный прогон после подъёма: 10399 passed, 27 skipped, единственный красный разобран ниже. ВСЕ СЕМЬ СКАНЕРОВ ДРЕЙФА ДАЮТ НОЛЬ: version refs, py version constants, mcp counts, test counts, code counts, closed lists, table columns. ВТОРАЯ СУЩЕСТВУЮЩАЯ ОХРАНА СРАБОТАЛА НА МОЕЙ ЖЕ ПРАВКЕ, И ПО ДЕЛУ. tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout поймал, что ратчет дрейфа переводов, добавленный смену назад, обходит ДЕРЕВО ДОКУМЕНТОВ и не объявляет CROSSCUTTING_SCOPE. Следствие было бы тихим: гейт scoped-pytest сопоставляет тесты с исходниками ПО ИМЕНИ, а docs/ru/cli.md не сопоставляется ни с каким test_<basename>.py — то есть правка документации ратчет бы не запустила, и он был бы зелен ровно тогда, когда не нужен. Объявлено CROSSCUTTING_SCOPE = ['docs/']. Domain: проверено вне тестов чтением обоих README целиком. Читатель, открывший страницу проекта, видит значок 1.9.0 и раздел про 1.9; про 1.8 узнаёт по ссылке, а не вместо.
