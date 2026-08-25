---
slug: opencode-bootstrap-generator
title: "OpenCode: генератор opencode.json (MCP + instructions + файл правил)"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "bootstrap/bootstrap_opencode.py (новый), tests/test_opencode_bootstrap.py (новый)"
scope_exclude: "bootstrap/bootstrap_config.py (IDE_DIRS/SCAFFOLD_IDES) и bootstrap/bootstrap.py (dispatch) — их трогает финальная задача opencode-ide-support; docs/** — дока обновляется только когда поддержка реально есть; .opencode/plugins/** — задача opencode-qg0-plugin"
relevant_files:
  - "bootstrap/bootstrap_opencode.py"
  - "tests/test_opencode_bootstrap.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T13:02:47Z"
---

## Goal

Шаг 1 из 3 к поддержке OpenCode (см. gotcha #201, решение #131; далее opencode-qg0-plugin → opencode-ide-support). Написать bootstrap/bootstrap_opencode.py, генерирующий конфиг OpenCode. НЕ включать opencode в SCAFFOLD_IDES в этой задаче — заявление о поддержке делает только финальная задача, после появления принуждения; иначе воспроизведём первопричину инцидента (дока обещает — кода нет).  ОБРАЗЕЦ: bootstrap/bootstrap_kilo.py — структура mcp-стансы у Kilo и OpenCode СОВПАДАЕТ ({type:"local", command:[...], enabled:true}), можно переиспользовать форму _SERVERS/_resolve_server/_merge_into_file.  ЛОВУШКА, НА КОТОРОЙ ЛЕГКО ПОГОРЕТЬ: Kilo пишет пути через ${workspaceFolder} — OpenCode такую подстановку НЕ ПОДДЕРЖИВАЕТ (там только {env:VAR} и {file:path}). Слепое копирование bootstrap_kilo даст мёртвый конфиг. Пути — АБСОЛЮТНЫЕ.

## Acceptance Criteria

1. bootstrap/bootstrap_opencode.py::generate_opencode_config(project_dir, target_dir, venv_python, lib_dir, config) пишет/мерджит opencode.json в КОРНЕ проекта (не в .opencode/). Ключ `mcp`: стансы tausik-project / codebase-rag / tausik-brain вида {type:"local", command:[<abs python>, <abs server.py>, "--project", <abs project_dir>], enabled:true}. Сервер, чей server.py не найден, ПРОПУСКАЕТСЯ (как в bootstrap_kilo._resolve_server) — не эмитить мёртвую команду. 2. Пути абсолютные: тест проверяет, что в command нет подстроки "${workspaceFolder}" (OpenCode её не раскроет). 3. Ключ `tools` НЕ ПИШЕТСЯ НИКОГДА: в схеме OpenCode он принимает только boolean ({"bash": false}); объект там = ConfigInvalidError, ровно это уронило хост пользователя. Тест: сгенерированный конфиг не содержит ключа `tools` ни при каких входных данных. 4. Ключ `instructions` (массив путей, OpenCode их МЕРДЖИТ с AGENTS.md) содержит путь к файлу правил TAUSIK. Файл правил генерируется из bootstrap_templates.build_full_body (то же тело, что у CLAUDE.md/AGENTS.md) — по умолчанию .opencode/tausik-rules.md. 5. ИДЕМПОТЕНТНОСТЬ: повторный прогон не дублирует запись в instructions (массив не растёт) и не переписывает тело файла правил в цикле. 6. СОХРАННОСТЬ ЧУЖОГО: существующий opencode.json с пользовательскими ключами (model, provider, agent, permission) и пользовательскими mcp-серверами — все сохраняются; TAUSIK трогает только свои три стансы + instructions. 7. НЕГАТИВНЫЕ СЦЕНАРИИ (tests/test_opencode_bootstrap.py): (а) битый/невалидный JSON в opencode.json не роняет bootstrap (см. _merge_into_file в bootstrap_kilo: except JSONDecodeError → пересоздать); (б) отсутствующий venv_python → фолбэк "python"; (в) двойной прогон: instructions не растёт, чужие ключи целы; (г) генератор не эмитит `tools` даже если он был в существующем конфиге как boolean — существующий boolean-`tools` пользователя ДОЛЖЕН сохраниться нетронутым (не путать: не создавать свой, но и не удалять чужой). 8. Gates зелёные: tausik verify --task opencode-bootstrap-generator.

## Plan

## Rollback

git revert. Задача чисто аддитивна: новый модуль + новый тест, ни один существующий путь исполнения не меняется (dispatch-ветка появится позже), поэтому откат не затрагивает другие IDE.

## Journal

- 2026-07-14T13:02:29Z [implementation] — Написан bootstrap/bootstrap_opencode.py (186 строк): generate_opencode_config() мерджит opencode.json в КОРНЕ проекта (mcp-стансы + instructions), generate_opencode_rules() пишет .opencode/tausik-rules.md из build_full_body(ide="opencode"). Все три ловушки закрыты кодом и тестом: (1) пути в command абсолютные, ${workspaceFolder} не появляется нигде (тест ищет подстроку в сыром тексте); (2) ключ tools не эмитится никогда, но чужой boolean-tools сохраняется нетронутым; (3) правила доставляются через instructions (OpenCode их МЕРДЖИТ с AGENTS.md), AGENTS.md для opencode не генерируем — docstring это фиксирует для следующей задачи. Идемпотентность: instructions не растёт (проверка по членству, не append), тело правил при повторном прогоне не переписывается (пользовательская правка выживает). Битый JSON и non-dict JSON → пересоздание, не падение. tests/test_opencode_bootstrap.py: 18 passed. В SCAFFOLD_IDES opencode НЕ добавлен — заявление о поддержке принадлежит финальной задаче.
- 2026-07-14T13:02:46Z [implementation] — AC verified прогоном tests/test_opencode_bootstrap.py (18 passed): 1. ✓ generate_opencode_config(project_dir, target_dir, venv_python, lib_dir, config) пишет opencode.json в корне проекта — TestMcpStanzas::test_writes_config_at_project_root_not_in_opencode_dir (проверяет и что в .opencode/ файла НЕТ). Стансы {type:"local", command:[python, server.py, "--project", dir], enabled:true} — test_three_servers_local_and_enabled. Ненайденный server.py пропускается — test_missing_server_is_skipped_not_emitted_dead; фолбэк на lib_dir — test_falls_back_to_lib_dir_canonical. 2. ✓ Пути абсолютные: test_no_workspacefolder_anywhere (подстрока "${workspaceFolder}" отсутствует в сыром тексте конфига) + test_command_entries_are_absolute (os.path.isabs на server.py и на значении --project). 3. ✓ Ключ tools не пишется никогда — test_generator_never_emits_tools; чужой boolean-tools {"bash": false} выживает — test_users_boolean_tools_survives_untouched. 4. ✓ instructions содержит путь к файлу правил (.opencode/tausik-rules.md), файл генерируется из bootstrap_templates.build_full_body(ide="opencode") — TestRulesFile::test_rules_file_carries_the_shared_body + test_config_and_rules_agree_on_the_path (ссылка в конфиге указывает на реально записанный файл). 5. ✓ Идемпотентность: три прогона подряд — instructions не растёт (test_instructions_does_not_grow_on_rerun); тело правил не переписывается, правка пользователя выживает (test_rules_body_not_rewritten_on_rerun). 6. ✓ Сохранность чужого: model/provider/agent/permission/чужой mcp-сервер/чужой instructions-элемент целы после двойного прогона — test_rerun_preserves_foreign_keys_and_servers. 7. ✓ Негативные: (а) битый JSON — test_broken_json_does_not_crash_bootstrap, non-dict JSON — test_non_dict_json_is_replaced; (б) venv_python=None → "python" — test_missing_venv_python_falls_back_to_bare_python; (в) двойной прогон — см. AC 5/6; (г) чужой boolean-tools не удаляется — см. AC 3. 8. ✓ Gates: tausik verify --task opencode-bootstrap-generator passed=True (hadolint, pytest). Domain: сгенерированный opencode.json валиден по схеме OpenCode вне тестов — ключ tools отсутствует (единственная причина ConfigInvalidError у пользователя), команды MCP запускаются абсолютным интерпретатором по абсолютному пути (OpenCode не раскрывает переменные рабочей папки), правила приезжают через instructions, который дока OpenCode обещает МЕРДЖИТЬ с чужим AGENTS.md. Заявление о поддержке OpenCode не сделано: SCAFFOLD_IDES не тронут, гард test_docs_no_fake_npm_packages остаётся зелёным.
