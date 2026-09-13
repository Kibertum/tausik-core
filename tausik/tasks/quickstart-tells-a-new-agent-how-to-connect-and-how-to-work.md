---
slug: quickstart-tells-a-new-agent-how-to-connect-and-how-to-work
title: "Quickstart для нового АГЕНТА: как подключить фреймворк на своём хосте и как работать после подключения — точными вызовами, с ожидаемыми ответами и отказами"
status: planning
epic: release-19-renar-conformance
story: release19-clean-publication-and-onboarding
complexity: complex
role: tech-writer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "docs/en/agent-quickstart.md, docs/ru/agent-quickstart.md (новые), README.md, README.ru.md, AGENTS.md (статическая часть), docs/README.md, docs/en/quickstart.md, docs/ru/quickstart.md (ссылка и правка перечня хостов), tests/test_agent_quickstart.py (новый), docs/{en,ru}/whats-new-1.9.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "Не менять поведение фреймворка ради документа; DYNAMIC-блок AGENTS.md; harness/skills; bootstrap."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Указание владельца, смена #251: перед 1.9 привести документацию в порядок и особо — quickstart для новых агентов, чтобы они максимально чётко понимали, как подключать фреймворк и как работать с ним после подключения. ЗАМЕР: docs/{en,ru}/quickstart.md (331/329 строк) написаны для ЧЕЛОВЕКА («No prior experience with AI tools required», «open VSCode», «install Python»); хосты в Step 0 — Claude, Cursor, Qwen, Kilo, Windsurf — без Codex и OpenCode, хотя SCAFFOLD_IDES = claude, cursor, qwen, kilo, opencode, codex; AGENTS.md «Your First 60 Seconds» — ориентир, но не процедура: нет последовательности «подключить → перезапустить → проверить → сессия → задача → verify → done → handoff» с точными именами инструментов MCP и их CLI-эквивалентами, ожидаемым ответом и текстом отказа (QG-0 без AC, QG-2 без квитанции, Rule 1 из хука); нет ветвления по хосту (что делает хук, что — сам агент). Задача: новая страница docs/{en,ru}/agent-quickstart.md (и ссылка из README, AGENTS.md «Your First 60 Seconds», docs/README.md, quickstart.md) — для агента, читающего её впервые: (A) подключение: submodule + `bootstrap.py --init --ide <host>` для каждого из шести хостов, что появится, перезапуск, проверка (`tausik_status` / `.tausik/tausik status`), что делать, если MCP не виден; (B) работа: цикл в точных вызовах — session_start → task_quick/task_add с goal+AC (с негативным сценарием — иначе QG-0 откажет, и текст отказа приведён) → task_start → правки → task_log → verify (handle) → task_done с evidence и handle → handoff/session_end; для каждого шага MCP-имя, CLI-эквивалент, что придёт в ответ, какой отказ возможен и как его снять; (C) правила, которые хост исполняет за агента, и правила, которые агент исполняет сам — по матрице хостов, с условием доверия хуков для Codex; (D) память: когда memory_add / dead_end / decide, что НЕ писать в ~/.claude. Правдивость: каждое имя MCP-инструмента на странице существует в TOOLS, каждая CLI-команда — в парсере, каждая ссылка разрешается — тест; тексты отказов сняты с реального вызова (журнал), не сочинены.

## Acceptance Criteria

AC-1: docs/en/agent-quickstart.md и docs/ru/agent-quickstart.md существуют, парны, и на них ссылаются README.md, README.ru.md, AGENTS.md («Your First 60 Seconds»), docs/README.md и quickstart.md обоих языков. AC-2: раздел подключения покрывает все шесть хостов SCAFFOLD_IDES (тест сверяет перечень хостов на странице с bootstrap_config.SCAFFOLD_IDES; НЕГАТИВ: хост, убранный со страницы, краснит). AC-3: каждый `tausik_*` инструмент, названный на странице, существует в TOOLS MCP-сервера; каждая CLI-команда `tausik <cmd> [<sub>]` — в парсере (тест; НЕГАТИВ: выдуманный инструмент на странице краснит). AC-4: тексты отказов QG-0 (task start без AC/негативного сценария), QG-2 (task done без квитанции) и Rule 1 (Write без активной задачи) на странице сняты с реальных вызовов в этой смене и совпадают с текущими сообщениями по ключевой фразе (тест читает сообщение из кода/фикстуры). AC-5: страница называет условие доверия хуков для Codex и границу «хост исполняет / агент исполняет сам» по каждому хосту, согласованно с docs/en/model-providers.md (без нового hard-claim). AC-6: все ссылки страницы разрешаются (tests/test_docs_links_resolve.py из задачи docs-internal-links…). AC-7: signed verify; CHANGELOG EN/RU; whats-new 1.9 называет страницу.

## Plan

## Rollback

git revert; страницы удаляются вместе с тестом и ссылками.

## Journal
