---
slug: quickstart-tells-a-new-agent-how-to-connect-and-how-to-work
title: "Quickstart для нового АГЕНТА: как подключить фреймворк на своём хосте и как работать после подключения — точными вызовами, с ожидаемыми ответами и отказами"
status: done
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
relevant_files:
  - "docs/en/agent-quickstart.md"
  - "docs/ru/agent-quickstart.md"
  - "tests/test_agent_quickstart.py"
  - README.md
  - README.ru.md
  - AGENTS.md
  - "docs/README.md"
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T14:19:01Z"
resolution: null
resolution_reason: null
---

## Goal

Указание владельца, смена #251: перед 1.9 привести документацию в порядок и особо — quickstart для новых агентов, чтобы они максимально чётко понимали, как подключать фреймворк и как работать с ним после подключения. ЗАМЕР: docs/{en,ru}/quickstart.md (331/329 строк) написаны для ЧЕЛОВЕКА («No prior experience with AI tools required», «open VSCode», «install Python»); хосты в Step 0 — Claude, Cursor, Qwen, Kilo, Windsurf — без Codex и OpenCode, хотя SCAFFOLD_IDES = claude, cursor, qwen, kilo, opencode, codex; AGENTS.md «Your First 60 Seconds» — ориентир, но не процедура: нет последовательности «подключить → перезапустить → проверить → сессия → задача → verify → done → handoff» с точными именами инструментов MCP и их CLI-эквивалентами, ожидаемым ответом и текстом отказа (QG-0 без AC, QG-2 без квитанции, Rule 1 из хука); нет ветвления по хосту (что делает хук, что — сам агент). Задача: новая страница docs/{en,ru}/agent-quickstart.md (и ссылка из README, AGENTS.md «Your First 60 Seconds», docs/README.md, quickstart.md) — для агента, читающего её впервые: (A) подключение: submodule + `bootstrap.py --init --ide <host>` для каждого из шести хостов, что появится, перезапуск, проверка (`tausik_status` / `.tausik/tausik status`), что делать, если MCP не виден; (B) работа: цикл в точных вызовах — session_start → task_quick/task_add с goal+AC (с негативным сценарием — иначе QG-0 откажет, и текст отказа приведён) → task_start → правки → task_log → verify (handle) → task_done с evidence и handle → handoff/session_end; для каждого шага MCP-имя, CLI-эквивалент, что придёт в ответ, какой отказ возможен и как его снять; (C) правила, которые хост исполняет за агента, и правила, которые агент исполняет сам — по матрице хостов, с условием доверия хуков для Codex; (D) память: когда memory_add / dead_end / decide, что НЕ писать в ~/.claude. Правдивость: каждое имя MCP-инструмента на странице существует в TOOLS, каждая CLI-команда — в парсере, каждая ссылка разрешается — тест; тексты отказов сняты с реального вызова (журнал), не сочинены.

## Acceptance Criteria

AC-1: docs/en/agent-quickstart.md и docs/ru/agent-quickstart.md существуют, парны, и на них ссылаются README.md, README.ru.md, AGENTS.md («Your First 60 Seconds»), docs/README.md и quickstart.md обоих языков. AC-2: раздел подключения покрывает все шесть хостов SCAFFOLD_IDES (тест сверяет перечень хостов на странице с bootstrap_config.SCAFFOLD_IDES; НЕГАТИВ: хост, убранный со страницы, даёт ошибку теста). AC-3: каждый tausik_* инструмент, названный на странице, существует в TOOLS MCP-сервера; каждая CLI-команда — в парсере (тест; НЕГАТИВ: выдуманный инструмент на странице даёт ошибку). AC-4: тексты отказов QG-0 (task start без AC/негативного сценария), QG-2 (task done без квитанции/доказательства) и Rule 1 (Write без активной задачи) на странице сняты с реальных вызовов в этой смене и совпадают с текущими сообщениями по ключевой фразе (тест читает фразу из кода). AC-5: страница называет условие доверия хуков для Codex и границу «хост исполняет / агент исполняет сам» по каждому хосту, согласованно с docs/en/model-providers.md (без нового hard-claim). AC-6: все ссылки страницы разрешаются (tests/test_docs_links_resolve.py). AC-7: signed verify; CHANGELOG EN/RU; whats-new 1.9 называет страницу.

## Plan

## Rollback

git revert; страницы удаляются вместе с тестом и ссылками.

## Journal

- 2026-09-13T14:18:01Z [implementation] — ЗАМЕР в свежем проекте-потребителе (scratchpad/qs, bootstrap --init --ide claude): тексты отказов сняты живьём — QG-0 «cannot start — missing acceptance_criteria», QG-0 «AC has no negative scenario», QG-2 «cannot complete — acceptance criteria not verified», QG-2 «has 2 acceptance criteria but no verification evidence», Rule 1 из развёрнутого task_gate.py «BLOCKED: No active task. TAUSIK requires a task before code changes (SENAR Rule 1)», verify без ключа «Verify handle: none — no project key, so no signed receipt…»; полный цикл session start → task quick → start → update --relevant-files → log → verify (ruff+pytest scoped, green) → done → session end пройден. Страницы EN/RU: подключение по шести хостам с тем, что появляется и что принуждает (Codex — только после доверия), цикл вызовами MCP|CLI с ответами, граница «хост/агент», память, хосты без slash-команд. tests/test_agent_quickstart.py (21): перечень хостов = SCAFFOLD_IDES; каждый tausik_* ∈ TOOLS (146); каждая CLI-команда парсится (build_parser); каждая цитата отказа — в коде (gate_qg0_check, gate_ac_check, hooks/task_gate, render_verify); негатив — выдуманный инструмент ловится. Ссылки: README EN/RU, AGENTS.md (пункт 0 и карта), docs/README.md, quickstart.md EN/RU (шесть хостов вместо пяти), whats-new EN/RU раздел.
- 2026-09-13T14:18:22Z [implementation] — AC-1 ✓ docs/en/agent-quickstart.md + docs/ru/agent-quickstart.md с переключателями; ссылки из README.md:179, README.ru.md:178, AGENTS.md (пункт 0 «Your First 60 Seconds» и карта документации), docs/README.md (обе таблицы), docs/{en,ru}/quickstart.md (врезка «Are you the agent?/Вы — агент?»); tests/test_docs_links_resolve.py::test_the_switcher_points_at_the_pair[agent-quickstart.md-agent-quickstart.md]. AC-2 ✓ tests/test_agent_quickstart.py::test_the_host_row_is_exactly_what_bootstrap_scaffolds[en|ru] читает bootstrap_config.SCAFFOLD_IDES и требует строку таблицы на каждый --ide; (НЕГАТИВ) убранный хост даёт ошибку сравнения списков. AC-3 ✓ ::test_every_tool_named_exists[en|ru] (TOOLS, 146), ::test_every_cli_command_named_parses[en|ru] (build_parser); (НЕГАТИВ) ::test_a_made_up_tool_would_be_caught. AC-4 ✓ ::test_each_quoted_refusal_is_what_the_code_prints[6 фраз × en|ru] — фразы сняты живьём в scratchpad/qs (журнал) и найдены в scripts/gate_qg0_check.py, gate_ac_check.py, hooks/task_gate.py, render_verify.py. AC-5 ✓ ::test_codex_is_named_with_its_trust_condition[en|ru]; таблица «что принуждает» согласована с enforcement-coverage и матрицей model-providers (без нового hard). AC-6 ✓ tests/test_docs_links_resolve.py::test_every_relative_link_resolves[docs/en/agent-quickstart.md|docs/ru/agent-quickstart.md]. AC-7 ✓ verify #2607 подписан; CHANGELOG EN/RU; whats-new EN/RU раздел «The agent's own quickstart / Быстрый старт самого агента». Domain: свежий агент на любом из шести хостов получает процедуру подключения и цикл, где каждый ответ и отказ — реальный вывод этой версии, а не пересказ.
- 2026-09-13T14:18:58Z [implementation] — AC-1 ✓ docs/en/agent-quickstart.md + docs/ru/agent-quickstart.md с переключателями; ссылки из README.md:179, README.ru.md:178, AGENTS.md (пункт 0 «Your First 60 Seconds» и карта документации), docs/README.md (обе таблицы), docs/{en,ru}/quickstart.md (врезка «Are you the agent?/Вы — агент?»); tests/test_docs_links_resolve.py::test_the_switcher_points_at_the_pair[agent-quickstart.md-agent-quickstart.md]. AC-2 ✓ tests/test_agent_quickstart.py::test_the_host_row_is_exactly_what_bootstrap_scaffolds[en|ru] читает bootstrap_config.SCAFFOLD_IDES и требует строку таблицы на каждый --ide; (НЕГАТИВ) убранный хост даёт ошибку сравнения списков. AC-3 ✓ ::test_every_tool_named_exists[en|ru] (TOOLS, 146), ::test_every_cli_command_named_parses[en|ru] (build_parser); (НЕГАТИВ) ::test_a_made_up_tool_would_be_caught. AC-4 ✓ ::test_each_quoted_refusal_is_what_the_code_prints[6 фраз × en|ru] — фразы сняты живьём в scratchpad/qs (журнал) и найдены в scripts/gate_qg0_check.py, gate_ac_check.py, hooks/task_gate.py, render_verify.py. AC-5 ✓ ::test_codex_is_named_with_its_trust_condition[en|ru]; таблица «что принуждает» согласована с enforcement-coverage и матрицей model-providers (без нового hard). AC-6 ✓ tests/test_docs_links_resolve.py::test_every_relative_link_resolves[docs/en/agent-quickstart.md|docs/ru/agent-quickstart.md]. AC-7 ✓ verify подписан; CHANGELOG EN/RU; whats-new EN/RU раздел. Domain: свежий агент на любом из шести хостов получает процедуру подключения и цикл, где каждый ответ и отказ — реальный вывод этой версии, а не пересказ.
