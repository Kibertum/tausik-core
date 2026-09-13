---
slug: slow-lane-is-red-and-nobody-ran-it
title: "Полная лента (-m '') красная: 22 теста — 15 зовут удалённый с Notion параметр brain_enabled, 3 ждут brain-навык, 4 читают живую базу или историю чужого проекта; с 07.09 её никто не запускал"
status: planning
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "tests/test_caveman_wiring_integration.py, tests/test_bootstrap_skills_coverage.py, tests/test_dead_symbols_stay_dead.py, tests/test_renar_normative_inapplicability.py, tests/test_repo_coherence.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Код bootstrap и навыков не менять — правятся тесты, отставшие от дерева; push запрещён."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #252, процедура .gitlab-ci.yml на этой машине (клон --depth 50, bootstrap --no-detect --ide all, pytest -m ''): 22 failed, 10116 passed, 160 skipped. Локально `pytest tests/test_caveman_wiring_integration.py tests/test_bootstrap_skills_coverage.py -m ''`: 18 failed. Полная лента GitLab (tests-full) не исполнялась с 07.09 — stage skipped из-за красной быстрой; «10084 passed» из журналов — быстрая лента (-m 'not slow'). Причины по группам: (1) 15 × tests/test_caveman_wiring_integration.py — bootstrap_ide(..., brain_enabled=False): параметр удалён вместе с Notion (77703c4a), slow-тест не обновлён; плюс _RULES_FILE не знает codex (AssertionError: scaffolded IDEs with no rules file declared here: ['codex']); (2) 3 × tests/test_bootstrap_skills_coverage.py — test_critical_skills_present ждёт навык brain, test_brain_included_with_notion_config, test_external_skills_coexist; (3) tests/test_dead_symbols_stay_dead.py::…[two_modules_helper] — предпосылка «_now_iso определён в нескольких модулях» исчезла (1 модуль), тест проверяет не то; (4) tests/test_renar_normative_inapplicability.py::test_the_live_project_still_holds_the_premise — «the declaration covers no live SPEC» на СВЕЖЕЙ базе клона: читает живую БД этого проекта, на CI/чистом клоне её нет; (5) tests/test_repo_coherence.py::TestALensThatFindsNothingIsBroken::test_it_sees_the_known_rotted_evidence_class — то же: линза ищет известный класс гнили в живой бухгалтерии, на свежей базе его нет. Починка: (1) и (2) — тесты приводятся к дереву без Notion (снять brain_enabled, снять brain из критичных, добавить codex в _RULES_FILE с AGENTS.md); (3) — параметризация на живой пример имени, встречающегося в ≥2 модулях, или построение фикстуры; (4) и (5) — тесты, которым нужна живая бухгалтерия, пропускаются с причиной на базе без данных (как test_no_silent_db_gated_skips требует объявлять) — либо строят свою; ни один не остаётся заложником машины. Проверка: полная лента в свежем клоне по процедуре CI зелёная.

## Acceptance Criteria

AC-1: tests/test_caveman_wiring_integration.py и tests/test_bootstrap_skills_coverage.py зелёные с -m '' на этом дереве; ни один не ссылается на brain/Notion; _RULES_FILE покрывает все SCAFFOLD_IDES (codex → AGENTS.md). AC-2: НЕГАТИВ: тест каталога навыков по-прежнему даёт ошибку, если из развёрнутого профиля исчезает любой из 13 core-навыков (мутация: убрать один SKILL.md из временного профиля). AC-3: test_dead_symbols_stay_dead::…[two_modules_helper] проверяет предпосылку по живому дереву (имя, встречающееся в ≥2 модулях, находится, а не захардкожено) или строит свою фикстуру. AC-4: тесты, читающие живую бухгалтерию (renar premise, coherence lens), на базе без данных пропускаются с причиной, а на живой базе этого проекта по-прежнему проходят. AC-5: полная лента (-m '') в свежем клоне по процедуре .gitlab-ci.yml — 0 failed на этой машине; числа passed/skipped в журнале. AC-6: signed verify; CHANGELOG EN/RU.

## Plan

## Rollback

git revert; тесты вернутся к чтению удалённых параметров.

## Journal
