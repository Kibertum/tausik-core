---
slug: redoc-1-8-final
title: "Итоговая редокументация фреймворка под релиз 1.8 (вся пользовательская документация ↔ код)"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: tech-writer
stack: python
tier: substantial
call_budget: 150
defect_of: null
scope: "docs/ru/*, docs/en/*, README.md, CHANGELOG*.md. ТОЛЬКО документация — код/схему/гейты НЕ трогать (если найдено расхождение, где код прав — завести отдельный баг-таск, не чинить здесь)."
scope_exclude: "Изменение кода/схемы/гейтов; borrow-фичи, ещё не влитые (документируются в своих задачах); генерация нового функционала"
relevant_files:
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
  - "docs/en/skill-bundles.md"
  - "docs/ru/skill-bundles.md"
  - "docs/en/cost-telemetry.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/troubleshooting.md"
  - README.md
  - README.ru.md
  - "scripts/tausik_version.py"
  - pyproject.toml
  - "tests/test_doctor_doc_covers_every_check.py"
  - "docs/_generated/constants.json"
scope_paths:
  - "docs/"
  - README.md
  - README.ru.md
  - AGENTS.md
  - "tests/"
  - "scripts/"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-28T16:01:03Z"
---

## Goal

Финальный документационный проход перед релизом 1.8: привести ВСЮ пользовательскую документацию в соответствие с фактическим состоянием после 1.8. Охват: docs/ru + docs/en (architecture, quickstart, cli, agent-contract), README, CHANGELOG-консолидация. Что задокументировать: git-native round-trip (state export/import, tausik sync, lifecycle triggers, team-state-in-git), все НОВЫЕ CLI-команды и флаги, borrow-фичи по мере реализации (tool-output-rollup, rag-contextual-chunk-prefix, mcp-scope-tools-exposure, graph-mermaid-render), обновлённые гейты/конвенции/хуки. Сверить доки с кодом (doc-drift, doc constants --check, docs_lint), убрать устаревшее. Reconcile с kb-docs-swarm (использовать роевой механизм по зонам, если готов) — это ФИНАЛЬНЫЙ проход, а не дубль. Запустить в самом конце 1.8, когда все фичи влиты.

## Acceptance Criteria

1. Все новые команды 1.8 (tausik state export/import с флагами, tausik sync) задокументированы в docs/{en,ru}/cli.md с примерами. 2. Round-trip и эпик team-state-in-git описаны в architecture.md + quickstart.md (что едет в git, раскладка tausik/, sync после pull). 3. Borrow-фичи (rollup, contextual-prefix, mcp-scope-tools, mermaid) задокументированы по мере реализации — на момент запуска задачи покрыть все ВЛИТЫЕ. 4. doc-drift зелёный: tausik doc constants --check + docs_lint + drift провенанс без расхождений доки↔код. 5. НЕГАТИВ: нет ссылок на несуществующие команды/флаги/файлы — проверка автоматическим сканером (docs_lint stale-mention = 0 для затронутых доков). 6. README отражает 1.8 (headline-фича — командное состояние в git). 7. EN/RU синхронизированы (нет раздела, живущего только на одном языке). 8. CHANGELOG [Unreleased] консолидирован и готов к датированию релиза.

## Plan

## Rollback

Чистая документация. Откат: git revert коммита. Не трогает код/поведение, поэтому риск только косметический. doc-drift гейт ловит регрессию доков.

## Journal

- 2026-07-28T15:59:01Z [implementation] — AC-1: ✓ команды 1.8 задокументированы — `tausik state export/import` и `tausik sync` уже были в docs/{en,ru}/cli.md; добавлен раздел «Working With a Team» / «Работа в команде» в quickstart на обоих языках с примерами вызовов и указанием, что `tausik status` называет ОБА направления разрешения расхождения, не рекомендуя ни одного. AC-2: ✓ round-trip описан в quickstart.md (новый раздел, ссылка на team-state-in-git.md) и в architecture.md. AC-3: ✓ влитые borrow-фичи покрыты: contextual-prefix — новый раздел в architecture.md EN+RU (rag_context.py, колонка context_prefix, миграция индекса); rollup и mermaid уже документированы; mcp-scope-tools уже покрыт. AC-4: ✓ `tausik doc constants --check` — OK; `python scripts/docs_lint.py` — clean; gen_doc_constants --write прогнан, README EN+RU синхронизированы машинно. AC-5: ✓ docs_lint stale-mention = 0. Устаревшее упоминание исправлено: docs/en/troubleshooting.md утверждал «Brain in v1.4 is Notion-backed (no Docker/CouchDB/Meilisearch/Raven anymore)» — привязка к версии убрана, факт оставлен. AC-6: ✓ README EN+RU: раздел «v1.7 — pre-2.0» заменён на «v1.8 — the project's state travels in git» / «состояние проекта едет в git» с headline-фичей командного состояния в git и ссылкой на team-state-in-git.md. AC-7: ✓ EN/RU синхронизированы: каждая правка сделана парно на обоих языках. AC-8: ✓ CHANGELOG [Unreleased] консолидирован и готов к датированию. Domain: результат проверен прогоном инструментов, а не чтением. ГЛАВНАЯ НАХОДКА КАПСТОУНА: doctor.md на ОБОИХ языках утверждал «девять проверок / девять групп», тогда как команда печатает 17 меток из project_cli_doctor.py плюс Deferred AC из сервиса, а ДВЕ существующие проверки — «CLAUDE.md drift» и «Config trust tier» — не были задокументированы НИГДЕ. Число было написано рукой и дрейфовало молча, потому что ничто его не выводило. Исправлено: перечень проверок дополнен семью строками на каждом языке (Deferred AC, CLAUDE.md drift, Config trust tier, Verify-First profile, Kilo/OpenCode config, Brain config), фиксированное число из прозы удалено (часть проверок условна, поэтому НИ ОДНО число не верно), и добавлен tests/test_doctor_doc_covers_every_check.py — он ВЫВОДИТ перечень меток из исходника и требует упоминания каждой в обеих доках, плюс запрещает возвращать в прозу рукописный счётчик. Тест защищён от вырожденного прохода: test_source_still_exposes_labels_to_read падает, если рефакторинг принтера обнулит набор меток. ВТОРАЯ НАХОДКА: skill-bundles.md на обоих языках нёс статус-блок v1.4.0 с утверждением «каждый consumer-проект после ребутстрапа получает skills-official/bundles.json» — ровно то, что оказалось багом этого релиза; переписан под решение #200 с объяснением правила слияния и границы публикации. ТРЕТЬЕ: версия поднята 1.7.0 -> 1.8.0 в scripts/tausik_version.py И pyproject.toml — это потребовалось потому, что гейт версии ПОЙМАЛ мою правку README («version ref v1.8 does not match constants.json 1.7.0»), то есть механизм отработал как задуман и заставил принять решение явно, а не позволил доке разойтись с кодом. По CHANGELOG EN/RU: все записи сессий #146-#150 совпадают 1:1 (по 2/3/4/2/5); остаётся разница в 2 ЗАГОЛОВКА среди 107/105 старых записей — выборочная проверка обеих找 находок (`rm -rf ~`, `session extend`) показала, что содержание в RU присутствует, различается вёрстка заголовков, а не наличие материала. Заявляю это как проверенное выборкой, а не как точный паритет.
- 2026-07-28T15:59:59Z [implementation] — AC-4: ✓ tests/test_doctor_doc_covers_every_check.py::test_every_check_is_documented_in_both_languages — выводит перечень меток проверок ИЗ ИСХОДНИКА и требует упоминания каждой в docs/en/doctor.md и docs/ru/doctor.md; именно он ловит расхождение доки с кодом, ради которого капстоун и существует. AC-5: ✓ tests/test_doctor_doc_covers_every_check.py::test_docs_do_not_claim_a_fixed_number_of_checks — запрещает вернуть в прозу рукописный счётчик проверок, который дрейфовал молча («девять» при фактических 18). AC-7: ✓ tests/test_doctor_doc_covers_every_check.py::test_source_still_exposes_labels_to_read — защита самого теста от вырожденного прохода: если рефакторинг принтера обнулит набор меток, проверки выше стали бы тавтологически истинными. AC-8: ✓ verification_run #1571 — подписанная зелёная квитанция с [PASS] pytest по объявленной области из 17 файлов.
- 2026-07-28T16:01:20Z [done] — Negative: негативные сценарии капстоуна прогнаны как ПРОВЕРКИ ОТСУТСТВИЯ, а не наличия. (1) Отсутствие ссылок на несуществующее — `python scripts/docs_lint.py` даёт «clean», stale-mention = 0; до правки он выдавал одно устаревшее упоминание (docs/en/troubleshooting.md:48 про Brain v1.4 и Docker/CouchDB/Meilisearch/Raven). (2) Отсутствие расхождения чисел — `tausik doc constants --check` завершается «OK ... matches repository constants»; ДО бампа версии он ЛОВИЛ мою правку («README.md:188: version ref v1.8 does not match constants.json tausik_version=1.7.0») в четырёх местах, что и является доказательством работоспособности негативного пути, а не предположением о ней. (3) Отсутствие недокументированной проверки — test_every_check_is_documented_in_both_languages падал бы на любой метке, которой нет в доке; проверено мутацией: удаление строки «Deferred AC» из docs/en/doctor.md делает утверждение ложным. (4) Отсутствие вырожденного прохода — test_source_still_exposes_labels_to_read требует минимум 12 разобранных меток, иначе рефакторинг принтера сделал бы два предыдущих теста тавтологически зелёными. (5) Отсутствие возврата рукописного счётчика — test_docs_do_not_claim_a_fixed_number_of_checks ищет «nine/девять проверок» и падает на возврате любой такой формулировки.
