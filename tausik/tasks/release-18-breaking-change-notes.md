---
slug: release-18-breaking-change-notes
title: "BREAKING CHANGE трастовых тиров обязан попасть в release notes 1.8, не только в CHANGELOG"
status: planning
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
relevant_files: []
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
