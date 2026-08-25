---
slug: opencode-fail-open-doctor-traversal-rules-path
title: "Разбор находок ревью OpenCode: тихий fail-open, ложное обещание doctor, traversal в rules_path"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/opencode/plugins/tausik-qg0.js, scripts/service_doctor_opencode.py, bootstrap/bootstrap_opencode.py, tests/test_opencode_qg0_plugin.py, tests/test_doctor_opencode.py, tests/test_opencode_bootstrap.py, tests/test_docs_no_fake_npm_packages.py"
scope_exclude: "Не трогать: bootstrap/bootstrap.py и bootstrap_config.py (диспетчер и реестры уже закрыты и проверены), scripts/ide_utils.py, доку (docs/**) — находки ревью её не касаются. Дедупликацию six-way boilerplate в harness/{claude,cursor}/mcp/*/server.py (MEDIUM из ревью) в эту задачу НЕ включать — это отдельный рефакторинг с широким радиусом, заводится отдельной задачей."
relevant_files:
  - "harness/opencode/plugins/tausik-qg0.js"
  - "scripts/service_doctor_opencode.py"
  - "bootstrap/bootstrap_opencode.py"
  - "tests/test_opencode_qg0_plugin.py"
  - "tests/test_doctor_opencode.py"
  - "tests/test_opencode_bootstrap.py"
  - "tests/test_docs_no_fake_npm_packages.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-14T14:02:08Z"
---

## Goal

Закрыть находки адверсариального ревью диффа v1.7.0 ПЕРЕД релизом. Две HIGH бьют в самое сердце принципа «нулевая толерантность к тихим ошибкам»: (1) fail-open в QG-0-плагине молчит — любой сбой CLI тихо выключает принуждение навсегда, следа не остаётся; (2) doctor печатает «writes without an active task are refused», не проверив существование CLI-враппера, от которого плагин зависит — то есть выдаёт ЛОЖНОЕ обещание. Плюс MEDIUM: path traversal в config.opencode.rules_path (произвольная запись файла из подсунутого .tausik/config.json), тавтологичный assert в tests/test_docs_no_fake_npm_packages.py:167 (не может упасть), фолбэк на относительный "python" вопреки заявленному инварианту абсолютных путей, и молчаливая замена битого opencode.json без предупреждения.

## Acceptance Criteria

1. Fail-open в harness/opencode/plugins/tausik-qg0.js больше не молчит: сбой CLI пишет диагностику (console.warn/stderr), видимую в логе OpenCode. Тест под Node проверяет, что при cliFails запись пропускается И диагностика выдана. 2. scripts/service_doctor_opencode.py проверяет существование CLI-враппера (.tausik/tausik и .tausik/tausik.cmd на Windows), от которого плагин зависит на КАЖДУЮ запись; без него — не «refused», а fail с объяснением, что принуждение фактически выключено. Тест: враппера нет → doctor не заявляет, что записи блокируются. 3. _rules_path() в bootstrap_opencode.py отвергает traversal: '..'-сегменты и абсолютные пути, резолвящиеся вне project_dir, откатываются к дефолту с предупреждением. Тест: rules_path='../../../evil.md' не пишет за пределы project_dir. 4. tests/test_docs_no_fake_npm_packages.py:167 — тавтология (True != B) or B заменена настоящим утверждением. 5. Фолбэк интерпретатора резолвится абсолютно (shutil.which), либо doctor предупреждает о неабсолютном command[0]. 6. Битый opencode.json при замене печатает предупреждение — потеря пользовательских ключей не должна быть невидимой. 7. Полный pytest зелёный; tausik doctor чистый. НЕГАТИВНЫЙ СЦЕНАРИЙ: каждый фикс сопровождается тестом, который падает БЕЗ фикса.

## Plan

## Rollback

git revert коммита; фиксы изолированы в трёх модулях и их тестах, откат не затрагивает диспетчер bootstrap и реестры IDE.

## Journal

- 2026-07-14T14:02:08Z [implementation] — AC verified. Все шесть находок адверсариального ревью закрыты, каждая — с тестом, который без фикса краснеет. Полный сьют: 4531 passed, 0 failed. Doctor: All clean. Gates: verify passed=True. 1. ✓ Fail-open больше не молчит: harness/opencode/plugins/tausik-qg0.js при недоступном CLI пишет console.warn «[TAUSIK QG-0] DEGRADED: ... Allowing '<tool>' WITHOUT an active-task check ... set TAUSIK_HOOK_FAIL_SECURE=1 to block instead of allow». Тест test_fail_open_is_never_silent (драйвер перехватывает console.warn под Node): запись пропущена И диагностика выдана, в тексте есть DEGRADED и имя переменной-выхода. Парный test_healthy_path_stays_quiet — на здоровом пути молчим, чтобы предупреждение не обесценилось. 2. ✓ Doctor больше не обещает того, чего не проверял: добавлен _cli_wrapper_missing() — плагин на КАЖДУЮ запись шеллит .tausik/tausik(.cmd), без враппера запрос всегда падает и fail-open пропускает всё. Тест test_plugin_without_its_cli_is_not_called_enforcement: враппера нет → finding «fails OPEN» И ни одно сообщение не содержит «are refused». Раньше doctor в этом состоянии рапортовал «writes without an active task are refused» — прямая ложь. 3. ✓ Path traversal в rules_path закрыт: _rules_path() отвергает '..'-сегменты и абсолютные пути, а также всё, что по commonpath резолвится вне project_dir; откат к дефолту печатает WARNING. Тесты TestRulesPathIsUntrusted: три вектора ('../../../../evil.md', '..\\..\\evil.md', 'docs/../../evil.md') + абсолютный путь — ничего не пишется за пределы project_dir; отдельный тест доказывает, что честный вложенный путь (docs/rules/tausik.md) продолжает работать, т.е. гард не сломал легитимный сценарий. Вектор реален: .tausik/config.json едет вместе с репозиторием, подсунутый конфиг давал произвольную запись файла при первом же bootstrap. 4. ✓ Тавтологичный assert убран: в tests/test_docs_no_fake_npm_packages.py строка `assert table["opencode"] != (X) or X` — это (True != B) or B, истина при любом B, тест не мог упасть НИКОГДА. Заменён на настоящие утверждения (парсер читает «yes» как True и «no» как False) + прямое `assert "opencode" in SCAFFOLD_IDES`. Это была моя же находка ревьюера — фейковый тест в гарде против фейковых заявлений. 5. ✓ Фолбэк интерпретатора резолвится абсолютно: _fallback_python() через shutil.which(python3|python) → abspath; бареное "python" остаётся только если на PATH нет вообще ничего. Тест test_fallback_interpreter_is_resolved_absolutely: os.path.isabs + os.path.isfile. Причина: OpenCode сам спавнит MCP-серверы и GUI-запущенный хост может не передать им PATH — тогда сервер молча не поднимется, вопреки заявленному в модуле инварианту абсолютных путей. 6. ✓ Замена битого opencode.json объявляется: _load_existing печатает WARNING с причиной («unreadable ... Any keys it held are lost») и отдельно — для non-dict JSON. Тест test_replacing_a_broken_config_is_announced. Потеря пользовательских model/provider/agent/permission могла произойти незаметно. 7. ✓ Полный pytest зелёный (константы доки перегенерены штатным gen_doc_constants.py --write после добавления новых тестов), doctor чистый после bootstrap --ide all. НЕ ВЗЯТО В ЭТУ ЗАДАЧУ (осознанно, по scope_exclude): MEDIUM про шестикратное дублирование list_prompts/list_resources в harness/{claude,cursor}/mcp/* — заведена отдельная задача list-prompts-list-resources-harness-claude-cursor- (широкий радиус, требует решения «общий хелпер vs генерация cursor-зеркал»). LOW про mcp.update(), затирающий одноимённый пользовательский сервер, принят by design: имена tausik-project/codebase-rag/tausik-brain принадлежат TAUSIK. LOW про единственный слот кэша подписи — ревьюер сам проверил неэксплуатируемость (SQLite меняет mtime/size основного файла при коммите). Domain: вне тестов эти шесть правок означают, что сломанный CLI теперь оставляет след в логе OpenCode вместо тихого отключения принуждения, doctor перестал выдавать ложную гарантию, а подсунутый .tausik/config.json больше не пишет файлы за пределы проекта.
