---
slug: list-prompts-list-resources-harness-claude-cursor-
title: "Дедуплицировать list_prompts/list_resources: один хелпер вместо шести копий в harness/{claude,cursor}/mcp/*"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/claude/mcp/{project,codebase-rag,brain}/server.py, harness/cursor/mcp/{project,codebase-rag,brain}/server.py, общий модуль-хелпер, tests/test_mcp_answers_prompts_list.py"
scope_exclude: "Не трогать логику самих MCP-инструментов (TOOLS, handlers) — задача только про заглушки list_prompts/list_resources и про механизм защиты зеркал от расхождения. Не трогать bootstrap-диспетчер и реестры IDE."
relevant_files:
  - "harness/claude/mcp/brain/handlers.py"
  - "harness/claude/mcp/project/handlers_adapt.py"
  - "harness/claude/mcp/project/tools_adapt.py"
  - "bootstrap/bootstrap_stacks.py"
  - "scripts/gate_filesize.py"
  - "tests/test_mcp_single_canonical_tree.py"
  - "tests/test_mcp_answers_prompts_list.py"
  - "tests/test_med_findings_fix.py"
  - "tests/test_mcp_verify_handler.py"
  - "tests/test_brain_mcp_installed_layout.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T14:38:24Z"
---

## Goal

Находка ревью v1.7.0 (MEDIUM). Заглушки list_prompts/list_resources (13 строк) добавлены ДОСЛОВНО в шести местах: harness/{claude,cursor}/mcp/{project,codebase-rag,brain}/server.py. Тест test_mcp_answers_prompts_list ловит сервер, который ЗАБЫЛ хендлеры, но НЕ ловит расхождение зеркал: правка одной копии из шести пройдёт незамеченной. Корень глубже: harness/cursor/mcp/* — побайтовые копии harness/claude/mcp/*, закоммиченные в git, а не генерируемые. Связано с памятью #146 (добавление MCP-тула требует синхронизации 3 зеркал) и #184 (два реестра IDE).

## Acceptance Criteria

1. Общий хелпер (напр. register_empty_prompts_and_resources(server)) вместо шести дословных копий, ЛИБО обоснованное решение генерировать cursor-зеркала из claude-исходника на этапе copy/bootstrap. Выбор зафиксировать в tausik decide. 2. Существующий tests/test_mcp_answers_prompts_list.py продолжает проходить (все 6 серверов отвечают пустым списком, а не -32601). 3. НЕГАТИВНЫЕ СЦЕНАРИИ (обязательны): (а) ОШИБКА сборки, если один из шести серверов правят в одиночку и зеркала расходятся — сейчас такого теста НЕТ, есть только проверка «хендлер зарегистрирован», и молчаливое расхождение зеркал проходит незамеченным; тест обязан краснеть на подсунутом расхождении; (б) ОШИБКА, если сервер вообще потерял хендлер prompts/list (регресс к -32601); (в) ОШИБКА, если полный pytest красный или doctor не чист после bootstrap --ide all. 4. Gates зелёные.

## Plan

## Rollback

git revert; изменения изолированы в шести server.py + один хелпер + один тест.

## Journal

- 2026-07-14T14:38:22Z [implementation] — AC verified. Полный сьют: 4530 passed, 21 skipped, 0 failed. Doctor чист после bootstrap --ide all. Gates: verify passed=True. 1. ✓ Выбран НЕ хелпер, а удаление первопричины — решение #134. Замерил, прежде чем чинить: `diff -r harness/claude/mcp harness/cursor/mcp` дал РОВНО ОДНО различие на 19 файлов — слово в докстринге («cursor sibling» vs «claude sibling»). Дублировались не заглушки list_prompts (13 строк), а всё дерево целиком. Хелпер оставил бы 19 копий на месте и добавил бы к ним тест на синхронность, то есть узаконил бы ручную синхронизацию как норму. harness/cursor/mcp удалён (git rm -r, 19 файлов). Опасность была не в дублировании, а в ПРИОРИТЕТЕ: copy_mcp предпочитает harness/<ide>/mcp канону, поэтому правка одной claude-копии молча оставила бы пользователей Cursor на старом сервере. 2. ✓ tests/test_mcp_answers_prompts_list.py проходит: все шипящиеся серверы (brain, project, codebase-rag) отвечают пустым списком, а не -32601. Порог «>=6 серверов» опущен до «>=3» с объяснением в докстринге (шесть было ровно потому, что cursor держал копию). 3. ✓ НЕГАТИВНЫЕ СЦЕНАРИИ: (а) новый гард tests/test_mcp_single_canonical_tree.py::test_no_ide_ships_a_byte_copy_of_the_canonical_tree — ни один файл в harness/<ide>/mcp не смеет быть побайтовой копией файла из harness/claude/mcp; парный test_guard_bites_on_a_planted_duplicate сажает подсунутую копию и убеждается, что гард краснеет (иначе гард мог бы тихо перестать что-либо находить); test_a_genuinely_different_server_is_allowed доказывает, что IDE со СВОИМ, отличным сервером не ломается — запрещена копия, а не автономия. (б) регресс к -32601 ловит существующий AST-гард (комментарий с именем хендлера его не удовлетворяет). (в) полный pytest зелёный, doctor чист. 4. ✓ Gates зелёные. ПРОВЕРКА ЭКВИВАЛЕНТНОСТИ (главный риск удаления): copy_mcp во временных каталогах для cursor/qwen/kilo/opencode/claude отдаёт по 3 server.py каждой — все пять IDE получают канон через фолбэк. Ноль поведенческих различий, минус 19 файлов, минус целый класс дрейфа. ПОДЧИЩЕНЫ ВСЕ ПОТРЕБИТЕЛИ УДАЛЁННОГО ДЕРЕВА (их нашёл полный прогон, а не я глазами — 5 падений): bootstrap_stacks._MCP_TOOLS_PATHS, scripts/gate_filesize._FILESIZE_EXEMPT_DIRS, tests/test_med_findings_fix::test_mcp_mirrors_in_sync (переписан в test_deployed_mcp_matches_the_canonical_source: теперь стережёт канон против развёрнутой копии + факт отсутствия зеркала), tests/test_mcp_verify_handler, tests/test_brain_mcp_installed_layout (параметризация по IDE убрана — поведение зависит от РАСКЛАДКИ, а не от IDE), плюс три докстринга, которые ссылались на несуществующее зеркало. ПАМЯТЬ: конвенция #146 («синхронизируй 3 зеркала») стала ложью и УДАЛЕНА, заменена на #204 (одно каноническое дерево + порядок бамп → gen_doc_constants → bootstrap). Оставить её означало бы заставить следующего агента воссоздать удалённое дерево руками. Domain: вне тестов правка MCP-тула теперь физически не может разъехаться между IDE — синхронизировать нечего, дерево одно, а гард не даёт завести копию обратно.
