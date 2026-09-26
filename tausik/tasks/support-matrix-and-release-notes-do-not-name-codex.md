---
slug: support-matrix-and-release-notes-do-not-name-codex
title: "README/AGENTS/whats-new 1.9 не знают Codex как хост: «Codex-style … Expected / manual», «Prefer MCP if exposed», ноль упоминаний в заметках к релизу"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "README.md, README.ru.md, AGENTS.md (статическая часть, не DYNAMIC), docs/en/whats-new-1.9.md, docs/ru/whats-new-1.9.md, tests/test_release_notes_1_9.py, tests/ (новый тест списка --ide), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "DYNAMIC-блок AGENTS.md/CLAUDE.md; bootstrap; .agents/; матрица model-providers (отдельная задача codex-hard-claim-omits-the-trusted-hooks-precondition)."
relevant_files:
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
  - "tests/test_readme_names_every_scaffolded_host.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T11:45:41Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #251. README.md:159 / README.ru.md:158 таблица «Supported IDEs»: строка «Windsurf / Codex-style | MCP + rules | host-dependent | host-specific | Expected / manual»; README.md:161: «Hooks … run in Claude Code and Qwen Code»; README.md:175 / README.ru.md:174: «--ide claude|cursor|qwen|kilo», тогда как SCAFFOLD_IDES = claude, cursor, qwen, kilo, opencode, codex. AGENTS.md:47: «Codex CLI / headless agents | Prefer MCP if exposed; else mirror CLI»; таблица возможностей AGENTS.md:33-38 Codex не содержит. docs/{en,ru}/whats-new-1.9.md: grep -ci codex = 0 в обоих, при том что codex-first-class-19 — история релиза по решению #360, живая приёмка закрыта (MCP, i-have-adhd, tausik-reviewer подтверждены реальным Codex; нативный отказ — только под доверенным hook-профилем), а GitLab #17 в AC требует «RU+EN docs и support matrix». Абзац «Five environments were handed the same rules text» в whats-new считает пять хостов — теперь шесть. Починка: строка Codex в таблице обоих README (146 инструментов, 13 core + opt-in, 22 хука той же декларации, статус «First-class, live-verified; hooks enforce after the user trusts them in Codex»); строка Windsurf остаётся «Expected / manual» без Codex; предложение о хуках называет Codex с условием; список --ide равен SCAFFOLD_IDES; AGENTS.md — строка Codex в обеих таблицах с честной формулировкой (MCP да, skills в .codex/skills, hooks через .codex/hooks.json после доверия, sub-agents .codex/agents); whats-new EN/RU — раздел о Codex с границей утверждения и шесть хостов вместо пяти. Числа в новых ячейках подчиняются существующему сканеру doc_drift_tables (hooks_count, mcp_main_tools, skills_core_count), а список --ide охраняется новым тестом против SCAFFOLD_IDES.

## Acceptance Criteria

AC-1: README.md и README.ru.md содержат строку Codex в таблице поддерживаемых IDE с числами, равными constants.json (146 / 13 / 22), и статусом, называющим условие доверия хуков; строка «Codex-style» исчезла, Windsurf остался «Expected / manual». AC-2: НЕГАТИВ: предложение «Hooks … run in» в обоих README называет Codex с условием; список `--ide` в обоих README перечисляет ровно SCAFFOLD_IDES, и новый тест сверяет обе строки с bootstrap_config.SCAFFOLD_IDES — мутация «убрать opencode из README» даёт ошибку теста. AC-3: AGENTS.md: таблица возможностей и таблица «Model / host» содержат честную строку Codex (MCP, .codex/skills, .codex/hooks.json после доверия, .codex/agents); «Prefer MCP if exposed; else mirror CLI» удалено. AC-4: docs/en/whats-new-1.9.md и docs/ru/whats-new-1.9.md содержат раздел о Codex с границей утверждения (что подтверждено живым хостом, что — только под доверенным профилем) и «six hosts / шесть хостов» вместо пяти; tests/test_release_notes_1_9.py требует раздел на обоих языках (ошибка при отсутствии). AC-5: check_docs / gen_doc_constants --check зелёные; счётчик записей whats-new пересчитан тестом. AC-6: signed verify.

## Plan

## Rollback

git revert коммита документации; тест списка --ide удаляется вместе с ним.

## Journal

- 2026-09-13T11:38:17Z [implementation] — Сделано: README EN/RU — строки Codex CLI (146/13/22 + условие доверия) и OpenCode (один плагин QG-0), Windsurf отдельно; предложение о хуках называет Codex с условием и ссылкой на матрицу; --ide = claude|cursor|qwen|kilo|opencode|codex; RU «153 инструмента» → 146 (дрейф с двухсерверных времён). AGENTS.md — столбец Codex CLI в таблице возможностей и строка Codex CLI + строка Headless agents в таблице хостов; «Prefer MCP if exposed; else mirror CLI» снято. whats-new EN/RU — раздел «Codex is a sixth host / Codex — шестой хост» с границей доверия, и оговорка про «пять сред» (замер #225) с указанием на шестой хост. Тесты: tests/test_readme_names_every_scaffolded_host.py (6, читает SCAFFOLD_IDES; негатив — усечённый список даёт расхождение), tests/test_release_notes_1_9.py::TestTheCodexHostIsNamedWithItsBoundary (4, расстояние граница↔утверждение < 2500 символов). check_docs и gen_doc_constants --check зелёные; счётчик whats-new 235.
- 2026-09-13T11:44:36Z [implementation] — AC-1 ✓ README.md:159-161 / README.ru.md:158-160: строки Codex CLI (146 | 13 core | 22 с условием доверия | First-class, live-verified) и OpenCode; «Codex-style/Codex-подобные» отсутствует (tests/test_readme_names_every_scaffolded_host.py::test_every_scaffolded_host_has_a_row_in_the_support_table[en|ru]); Windsurf — «Expected / manual». AC-2 ✓ (НЕГАТИВ) предложение о хуках называет Codex с условием и ссылкой на матрицу; `--ide claude|cursor|qwen|kilo|opencode|codex` в обоих README; ::test_the_ide_flag_lists_exactly_the_scaffolded_hosts[en|ru] читает SCAFFOLD_IDES; ::test_a_missing_host_is_caught — усечённый список даёт расхождение. AC-3 ✓ AGENTS.md: столбец Codex CLI в таблице возможностей (MCP из .codex/config.toml, .codex/skills, .codex/hooks.json после доверия, .codex/agents), строка Codex CLI + Headless agents в таблице хостов; «Prefer MCP if exposed; else mirror CLI» удалено (grep). AC-4 ✓ docs/{en,ru}/whats-new-1.9.md — раздел «Codex is a sixth host» / «Codex — шестой хост» с границей; tests/test_release_notes_1_9.py::TestTheCodexHostIsNamedWithItsBoundary (4 теста, ошибка при отсутствии раздела или границы). AC-5 ✓ check_docs и gen_doc_constants --check зелёные; счётчик записей 235 пересчитан ::test_the_entry_figure_on_the_page_is_the_live_count. AC-6 ✓ verify #2577 подписан. Domain: агент или человек, открывший README, AGENTS.md или заметки к 1.9, видит Codex тем, чем его показал живой хост — первоклассным по MCP/навыкам/агентам и защищённым хуками только после доверия; RU README больше не обещает 153 инструмента.
- 2026-09-13T11:45:38Z [implementation] — AC-1 ✓ README.md:159-161 / README.ru.md:158-160: строки Codex CLI (146 | 13 core | 22 с условием доверия | First-class, live-verified) и OpenCode; «Codex-style/Codex-подобные» отсутствует (tests/test_readme_names_every_scaffolded_host.py::test_every_scaffolded_host_has_a_row_in_the_support_table[en|ru]); Windsurf — «Expected / manual». AC-2 ✓ (НЕГАТИВ) предложение о хуках называет Codex с условием и ссылкой на матрицу; `--ide claude|cursor|qwen|kilo|opencode|codex` в обоих README; ::test_the_ide_flag_lists_exactly_the_scaffolded_hosts[en|ru] читает SCAFFOLD_IDES; ::test_a_missing_host_is_caught — усечённый список даёт расхождение. AC-3 ✓ AGENTS.md: столбец Codex CLI в таблице возможностей (MCP из .codex/config.toml, .codex/skills, .codex/hooks.json после доверия, .codex/agents), строка Codex CLI + Headless agents в таблице хостов; «Prefer MCP if exposed; else mirror CLI» удалено (grep). AC-4 ✓ docs/{en,ru}/whats-new-1.9.md — раздел «Codex is a sixth host» / «Codex — шестой хост» с границей; tests/test_release_notes_1_9.py::TestTheUnmeasuredPromiseSaysSo::test_the_caveat_sits_next_to_the_promise[ru-codex|en-codex] (граница рядом с утверждением, ошибка при отсутствии) и ::TestTheCodexHostIsNamedWithItsBoundary::test_the_host_count_is_not_left_at_five; дубль формы снят по храповику dedupe — параметризация вместо второго теста. AC-5 ✓ check_docs и gen_doc_constants --check зелёные; счётчик записей 235 пересчитан ::test_the_entry_figure_on_the_page_is_the_live_count. AC-6 ✓ verify #2577 подписан. Domain: агент или человек, открывший README, AGENTS.md или заметки к 1.9, видит Codex тем, чем его показал живой хост — первоклассным по MCP/навыкам/агентам и защищённым хуками только после доверия; RU README больше не обещает 153 инструмента.
