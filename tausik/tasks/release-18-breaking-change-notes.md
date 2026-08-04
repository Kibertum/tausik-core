---
slug: release-18-breaking-change-notes
title: "BREAKING CHANGE трастовых тиров обязан попасть в release notes 1.8, не только в CHANGELOG"
status: blocked
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 12
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/ru/whats-new-1.8.md"
  - "docs/en/whats-new-1.8.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Релизы этого проекта — git-теги (v1.4.2 … v1.7.0); отдельного файла release notes нет, значит заметки к тегу собираются вручную. Поломка из коммита 6bdd4f5 (трастовые тиры конфигурации) описана в CHANGELOG.md, CHANGELOG.ru.md и docs/{ru,en}/config-trust-tiers.md, но ни один из этих текстов не показывается пользователю при обновлении. Риск: проект, отключавший гейт в .tausik/config.json, узнаёт о поломке из красного пайплайна, а не из заметок к релизу. Суть изменения: project-тир конфига теперь может только ужесточать надзор, поэтому ранее отключённый гейт после обновления окажется включённым, а ключ будет назван в tausik doctor. Миграция: перенести настройку в ~/.tausik/config.json либо в файл из $TAUSIK_MANAGED_CONFIG. Задача — проследить при сборке 1.8, что раздел BREAKING CHANGE с этой миграцией присутствует в заметках к тегу v1.8.0 на обоих языках, а не остаётся только в CHANGELOG. Задача осознанно держится в planning до момента сборки релиза.

## Acceptance Criteria

AC1. В заметках к тегу v1.8.0 присутствует раздел BREAKING CHANGE на ОБОИХ языках (EN+RU), а не только в CHANGELOG.md/CHANGELOG.ru.md.
AC2. Секция про трастовые тиры присутствует по смыслу: project-тир может только УЖЕСТОЧАТЬ надзор; гейт, отключённый в .tausik/config.json, после обновления снова включён; tausik doctor называет отклонённый ключ; миграция в ~/.tausik/config.json или $TAUSIK_MANAGED_CONFIG (коммит 6bdd4f5).
AC3. Секция про схему чека verify v1→v2 присутствует: поля declared_scope_status/undeclared_files/undeclared_count; старые чеки v1 валидны, но их область читается как непроверенная; внешние читатели чеков должны знать про новые поля.
AC4. Проверка выполнена на реальном теге v1.8.0 (не на черновике): заметки к тегу содержат обе секции на обоих языках.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-18T16:25:43Z [planning] — Решение #141 зафиксировало объём релиза 1.8: эпики landscape-2026-h2 (20 задач) + shared-knowledge (15). Ориентир ~30 сессий. Значит эта задача ждёт долго — проследить, что к моменту сборки в release notes попадут ОБА ломающих изменения, а не только трастовые тиры: (1) project-тир конфига может только ужесточать, ранее отключённый гейт окажется включённым, миграция в ~/.tausik/config.json или $TAUSIK_MANAGED_CONFIG; (2) схема чека tausik-receipt/v1 → v2 с полями declared_scope_status/undeclared_files/undeclared_count — старые чеки остаются валидными, но их область читается как непроверенная, а внешние читатели чеков должны знать про новые поля. Второе добавлено в сессии #114 задачей l26-verify-git-diff-wire.
- 2026-07-21T10:02:31Z [planning] — ПОДГОТОВЛЕН ГОТОВЫЙ К ВСТАВКЕ ЧЕРНОВИК release notes v1.8.0 (сессия #127). Задача остаётся в planning до сборки тега — закрыть при создании тега v1.8.0, проверив, что секция ниже попала в заметки к тегу на ОБОИХ языках. --- EN: BREAKING CHANGES (v1.8.0) --- 1. Config trust tiers — project-tier config can only TIGHTEN supervision, never loosen it. A gate you disabled in `.tausik/config.json` (project tier) is IGNORED after upgrade and the gate runs enabled again. `tausik doctor` names the rejected key. MIGRATION: move the override to the user tier `~/.tausik/config.json` or to the file named by `$TAUSIK_MANAGED_CONFIG`. (commit 6bdd4f5) 2. Verify receipt schema v1 → v2 — receipts gained `declared_scope_status`, `undeclared_files`, `undeclared_count`. Old v1 receipts stay VALID but their scope now reads as UNVERIFIED (narrower than the change). External tools that parse receipts must handle the new fields. (l26-verify-git-diff-wire, session #114) --- RU: ЛОМАЮЩИЕ ИЗМЕНЕНИЯ (v1.8.0) --- 1. Трастовые тиры конфига — project-тир может только УЖЕСТОЧАТЬ надзор, не ослаблять. Гейт, отключённый в `.tausik/config.json` (project-тир), после обновления ИГНОРИРУЕТСЯ и снова работает включённым. `tausik doctor` называет отклонённый ключ. МИГРАЦИЯ: перенесите настройку в user-тир `~/.tausik/config.json` или в файл из `$TAUSIK_MANAGED_CONFIG`. (коммит 6bdd4f5) 2. Схема чека verify v1 → v2 — в чеках появились `declared_scope_status`, `undeclared_files`, `undeclared_count`. Старые чеки v1 остаются ВАЛИДНЫМИ, но их область теперь читается как НЕПРОВЕРЕННАЯ (уже изменения). Внешние читатели чеков должны знать про новые поля. (l26-verify-git-diff-wire, сессия #114) ПРОВЕРКА ПРИ ЗАКРЫТИИ: обе секции присутствуют в release notes тега v1.8.0 (EN+RU), не только в CHANGELOG.md/CHANGELOG.ru.md. Источник истины по трастовым тирам: docs/{ru,en}/config-trust-tiers.md.
- 2026-08-03T12:43:50Z [implementation] — СОДЕРЖАНИЕ ГОТОВО, ПРОВЕРКА НА ТЕГЕ — ЗА ВЛАДЕЛЬЦЕМ. AC-1: ✓ docs/ru/whats-new-1.8.md и docs/en/whats-new-1.8.md — раздел ЛОМАЮЩИЕ ИЗМЕНЕНИЯ / BREAKING CHANGES на обоих языках, вне CHANGELOG. AC-2: ✓ пункт 3 обеих страниц — трастовые тиры, project-тир только ужесточает, doctor называет ключ, миграция в ~/.tausik/config.json либо (коммит 6bdd4f5). AC-3: ✓ пункт 4 обеих страниц — но НЕ v1→v2, как было в устаревшем черновике, а v1/v2→v3. AC-5 (CHANGELOG): ✓ CHANGELOG.md и CHANGELOG.ru.md, прозаическая запись. AC-4: НЕ ВЫПОЛНЕН И НЕ МОЖЕТ БЫТЬ ВЫПОЛНЕН АГЕНТОМ. Он требует проверки на РЕАЛЬНОМ теге v1.8.0; создание тега — действие владельца. Задача блокируется на этом, а не закрывается: закрыть её сейчас значило бы отчитаться о проверке, которой не было. ЧТО НАШЛОСЬ ПРИ СБОРКЕ, И РАДИ ЧЕГО СТОИЛО ЧИТАТЬ ВСЕ ЧЕТЫРЕ ПОДРЯД. (1) ЧЕРНОВИК БЫЛ БЫ НЕВЕРЕН В ТЕГЕ. Подготовленный в сессии #127, он называл схему квитанции «v1 → v2»; в #159 она стала v3. Плюс он не знал о #221 и #222, принятых позже. Ломающих не два, а четыре. Черновик заменён целиком. (2) ВЗАИМОДЕЙСТВИЕ ДВУХ ЛОМАЮЩИХ, которого не видно ни в одном по отдельности. Миграция трастовых тиров велит перенести послабление в ~/.tausik/config.json. Но именно каталог ~/.tausik убирает изменение #222: find_tausik_dir идёт вверх и ищет РОВНО имя .tausik, поэтому каталог в домашней папке снова захватит обнаружение проекта для всего, что под ней. Проверено по коду: config_trust.user_config_path() возвращает C:/Users/<user>/.tausik/config.json, то есть создаёт этот каталог. Обе страницы называют выходы: TAUSIK_USER_CONFIG (каталог не создаёт) либо управляемый тир. Найдено чтением двух миграций ДРУГ ПРОТИВ ДРУГА, а не по очереди.
