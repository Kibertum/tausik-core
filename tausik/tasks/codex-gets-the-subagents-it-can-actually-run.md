---
slug: codex-gets-the-subagents-it-can-actually-run
title: "Сабагенты не доезжают до Codex: copy_subagents отказывает всем, кроме Claude, а у Codex они есть"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "harness/claude/subagents/* (canonical source must not change)"
relevant_files:
  - "bootstrap/bootstrap_copy.py"
  - "tests/test_subagent_reviewer.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "bootstrap/bootstrap_copy.py"
  - "tests/test_subagent_reviewer.py"
  - "tests/test_bootstrap_codex.py"
  - ".codex/agents/*"
  - ".claude/agents/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-09T17:16:17Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #241. bootstrap_copy.copy_subagents начинается со строки `if ide != "claude": return 0`, а её docstring объясняет это тем, что у Cursor и Qwen нет понятия именованного сабагента. Для Codex это НЕВЕРНО: строка .codex/agents присутствует в бинаре codex.exe, и в этом проекте уже лежат четыре файла .codex/agents/*.toml - tausik-reviewer, tausik-gate-fixer, tausik-external-reviewer, tausik-coherence-judge. Написаны они НЕ нашим bootstrap-ом (codex до сегодняшнего дня отсутствовал в SCAFFOLD_IDES), поэтому в свежем клоне их не будет вовсе.

ЧТО ЭТО ЗНАЧИТ ДЛЯ ПЕРЕКЛЮЧЕНИЯ. Сабагенты - не украшение: tausik-gate-fixer читает отказ гейта и возвращает план починки, tausik-reviewer даёт состязательное ревью, tausik-external-reviewer - валидатор SENAR Rule 4 на ДРУГОЙ модели. Хост без них теряет разделение обязанностей, ради которого они и заведены.

ФОРМАТЫ РАЗНЫЕ, И ЭТО СУТЬ ЗАДАЧИ, А НЕ ДЕТАЛЬ. Claude читает harness/claude/subagents/*.md с YAML-заголовком; Codex - .toml с ключами name, description, developer_instructions. Копированием файла задача не решается: нужна КОНВЕРСИЯ из одного источника, иначе появятся две копии инструкции сабагента, и они разойдутся - ровно тот класс, против которого в этой же истории написан AC-5 у задачи про хуки.

## Acceptance Criteria

AC-1 После bootstrap --ide codex в .codex/agents/ лежат те же сабагенты, что у claude — сравнение по ИМЕНАМ, а не по числу. AC-2 Источник ОДИН: файлы Codex получаются конверсией из harness/claude/subagents/, а не второй копией текста; тест краснеет, если инструкция разошлась между форматами. AC-3 Конверсия сохраняет то, чем сабагент и является: имя, описание и ПОЛНЫЙ текст инструкции — проверяется тем, что содержательный кусок инструкции присутствует в обоих форматах. AC-4 НЕГАТИВ: хост, у которого понятия сабагента НЕТ (cursor, qwen), по-прежнему получает ноль — расширение не смеет начать сыпать файлы всем подряд. AC-5 Повторный прогон не плодит копий и не затирает файлы, отредактированные пользователем, — либо затирает ОСОЗНАННО и об этом сказано.

## Plan

## Rollback

Расширение copy_subagents конверсией в TOML; откат — git revert. Каталог .codex в .gitignore и пересоздаётся bootstrap-ом.

## Journal

- 2026-09-09T17:11:27Z [planning] — Measured task premise: copy_subagents has Claude-only guard; Codex agent TOMLs are outside bootstrap and may be absent in fresh clone. Starting implementation.
- 2026-09-09T17:14:04Z [implementation] — Implemented Codex TOML conversion from canonical Claude subagent Markdown. Added tests for all canonical agent names, descriptions, full instructions, overwrite policy, and non-agent hosts. Bootstrap --ide codex deployed four agents; scoped tests passed.
- 2026-09-09T17:14:45Z [implementation] — AC evidence: bootstrap --ide codex reported Sub-agents: 4 copied. tests/test_subagent_reviewer.py asserts canonical name equality, TOML name/description/full instructions, deterministic overwrite on rerun, and cursor/qwen/windsurf no-op. Verification receipt #2380: ruff PASS; scoped pytest PASS (35 modules).
- 2026-09-09T17:14:54Z [implementation] — AC verified: 1. ✓ bootstrap --ide codex copied all four canonical agents; test preserves names, descriptions, full instructions, rerun overwrite, and non-agent-host no-op. Verification receipt #2380 (ruff PASS; scoped pytest PASS).
- 2026-09-09T17:15:41Z [implementation] — Added matched EN/RU changelog entry required by QG-2; re-verifying expanded relevant file set.
- 2026-09-09T17:16:14Z [implementation] — AC verified: 1. ✓ Canonical Markdown produces four Codex TOML agents with equal names, descriptions and full instructions; rerun replacement and Cursor/Qwen/Windsurf no-op are covered. QG-2 changelog entries are matched in EN/RU. Verification receipt #2382: ruff PASS; scoped pytest PASS (36 modules).
