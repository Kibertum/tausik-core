---
slug: tests-call-bash-by-bare-name-windows-ci-answers-wsl-stub
title: "Пять тестов зовут bash по голому имени, и на windows-latest это заглушка WSL: лента верификации релиза красная шесть дней"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
role: developer
stack: python
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

НАЙДЕНО ЗАМЕРОМ В #205 ПРИ ИНВЕНТАРЕ МЕСТ ДЛЯ ci-does-not-run-on-the-release-branch. Гейт верификации релиза красный, и краснота никого не разбудила.

ЗАМЕР ПО API GITHUB. Лента Tests на main: три последних прогона ПОДРЯД суть failure — 32895740027, 32890507221, 32881343325, все от 2026-08-25. Последний зелёный — 2026-08-04. То есть шесть дней красноты на момент замера, и это ровно те коммиты, которыми публиковалась работа 1.9.

РАСКЛАД ПО ПОЛОСАМ, а не по впечатлению. Зелёные: lint, test-full, ubuntu 3.11/3.12/3.13, macos 3.11/3.12/3.13. Красные: windows-latest на 3.11, 3.12 и 3.13 — все три. Итог полосы: 5 failed, 7095 passed, 135 skipped, 128 deselected.

ПРИЧИНА ВИДНА В ЛОГЕ, НЕ УГАДАНА. Пять тестов tests/test_consumer_layout.py запускают subprocess.run([bash, ./_find_engine_file_probe.sh]) и полагают, что bash есть Git Bash. На образе windows-latest первым в PATH стоит System32\bash.exe — пусковая заглушка WSL. Дистрибутива в ней нет, поэтому rc=1, а stdout приходит в UTF-16 с текстом Windows Subsystem for Linux has no installed distributions. Тесты: test_the_memory_route_gate_is_reachable_in_a_plain_clone, test_the_search_does_not_step_into_the_parent_directory, test_the_engines_own_repo_prefers_its_source_over_the_deployed_copy, test_a_gate_that_cannot_find_itself_says_so, test_a_gate_switched_off_by_decision_stays_quiet.

ЭТО НЕ КЛАСС #204. four-tests-fail-in-a-bare-checkout чинил свежесть выгрузки и бил на всех платформах; здесь Linux и macOS зелёные, предмет — РАЗРЕШЕНИЕ ИМЕНИ bash на конкретном образе. Проверять отдельно и не считать закрытым тем фиксом.

ДВА ПРЕДМЕТА, И ВТОРОЙ ВАЖНЕЕ ПЕРВОГО. (1) Тесты обязаны брать ИМЕННО Git Bash, а не первое попавшееся имя bash, либо честно пропускаться, когда его нет, — но не краснеть про чужое. (2) КРАСНАЯ ЛЕНТА ШЕСТЬ ДНЕЙ НЕ ПРИВЕЛА НИ К ЧЕМУ. Гейт, чью красноту никто не читает, ничем не отличается от выключенного, и это тот же урок, что и вся история gates-declare-what-they-prevent.

НАЧАТЬ С ЦИФРЫ, НЕ С ПОЧИНКИ. Инвентарь мест: сколько ВСЕГО тестов зовут bash или иной интерпретатор по голому имени — мерить перечнем по tests/, а не по этим пяти. Число в заголовке ИЗМЕРЕННОЕ по одному прогону, а не граница.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита задачи; тесты возвращаются к прежнему способу вызова интерпретатора. Данных и схемы не касается.

## Journal
