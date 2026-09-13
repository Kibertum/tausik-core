---
slug: support-matrix-and-release-notes-do-not-name-codex
title: "README/AGENTS/whats-new 1.9 не знают Codex как хост: «Codex-style … Expected / manual», «Prefer MCP if exposed», ноль упоминаний в заметках к релизу"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #251. README.md:159 / README.ru.md:158 таблица «Supported IDEs»: строка «Windsurf / Codex-style | MCP + rules | host-dependent | host-specific | Expected / manual»; README.md:161: «Hooks … run in Claude Code and Qwen Code»; README.md:175 / README.ru.md:174: «--ide claude|cursor|qwen|kilo», тогда как SCAFFOLD_IDES = claude, cursor, qwen, kilo, opencode, codex. AGENTS.md:47: «Codex CLI / headless agents | Prefer MCP if exposed; else mirror CLI»; таблица возможностей AGENTS.md:33-38 Codex не содержит. docs/{en,ru}/whats-new-1.9.md: grep -ci codex = 0 в обоих, при том что codex-first-class-19 — история релиза по решению #360, живая приёмка закрыта (MCP, i-have-adhd, tausik-reviewer подтверждены реальным Codex; нативный отказ — только под доверенным hook-профилем), а GitLab #17 в AC требует «RU+EN docs и support matrix». Абзац «Five environments were handed the same rules text» в whats-new считает пять хостов — теперь шесть. Починка: строка Codex в таблице обоих README (146 инструментов, 13 core + opt-in, 22 хука той же декларации, статус «First-class, live-verified; hooks enforce after the user trusts them in Codex»); строка Windsurf остаётся «Expected / manual» без Codex; предложение о хуках называет Codex с условием; список --ide равен SCAFFOLD_IDES; AGENTS.md — строка Codex в обеих таблицах с честной формулировкой (MCP да, skills в .codex/skills, hooks через .codex/hooks.json после доверия, sub-agents .codex/agents); whats-new EN/RU — раздел о Codex с границей утверждения и шесть хостов вместо пяти. Числа в новых ячейках подчиняются существующему сканеру doc_drift_tables (hooks_count, mcp_main_tools, skills_core_count), а список --ide охраняется новым тестом против SCAFFOLD_IDES.

## Acceptance Criteria

AC-1: README.md и README.ru.md содержат строку Codex в таблице поддерживаемых IDE с числами, равными constants.json (146 / 13 / 22), и статусом, называющим условие доверия хуков; строка «Codex-style» исчезла, Windsurf остался «Expected / manual». AC-2: предложение «Hooks … run in» в обоих README называет Codex с условием; список `--ide` в обоих README перечисляет ровно SCAFFOLD_IDES, и новый тест сверяет обе строки с bootstrap_config.SCAFFOLD_IDES (мутация — убрать opencode из README — краснит). AC-3: AGENTS.md: таблица возможностей и таблица «Model / host» содержат честную строку Codex (MCP, .codex/skills, .codex/hooks.json после доверия, .codex/agents); «Prefer MCP if exposed; else mirror CLI» удалено. AC-4: docs/en/whats-new-1.9.md и docs/ru/whats-new-1.9.md содержат раздел о Codex с границей утверждения (что подтверждено живым хостом, что — только под доверенным профилем) и «six hosts / шесть хостов» вместо пяти; tests/test_release_notes_1_9.py требует раздел на обоих языках. AC-5: check_docs / gen_doc_constants --check зелёные; счётчик записей whats-new пересчитан тестом. AC-6: signed verify.

## Plan

## Rollback

git revert коммита документации; тест списка --ide удаляется вместе с ним.

## Journal
