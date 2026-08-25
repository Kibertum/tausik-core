---
slug: mcp-handlers-god-module-split
title: "Разрезать god-модуль MCP handlers.py (1345 строк, 77 хендлеров) и снять его временный exempt"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 140
defect_of: filesize-mro-exempt-mcp
scope: "harness/claude/mcp/project/handlers.py (усечение до диспетч-таблицы + оставшиеся домены); новые harness/claude/mcp/project/handlers_<домен>.py; tausik/gates.json (снять 1 временную запись, переадресовать вторую); tests/ (тест паритета поверхности _DISPATCH); CHANGELOG.md; CHANGELOG.ru.md; docs/{ru,en}/architecture.md"
scope_exclude: "harness/claude/mcp/codebase-rag/** — отошло задаче mcp-rag-server-module-split; harness/claude/mcp/project/tools*.py — декларации схем не трогаем (постоянный exempt); handlers_skill.py / handlers_spec.py / handlers_adapt.py — уже вынесены, содержимое не переписываем; scripts/gate_filesize.py hardcoded fallback; поведение хендлеров — тела переносим как есть"
relevant_files:
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/handlers_stack.py"
  - "harness/claude/mcp/project/handlers_role.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "harness/claude/mcp/project/handlers_cq.py"
  - "harness/claude/mcp/project/handlers_render.py"
  - "harness/claude/mcp/project/server.py"
  - "scripts/gate_filesize.py"
  - "tausik/gates.json"
  - "tests/test_mcp_dispatch_surface.py"
  - "tests/test_gate_class_surface.py"
  - "tests/test_mcp_verify_handler.py"
  - "tests/test_mcp_self_check.py"
  - "tests/test_memory_block.py"
  - "tests/test_memory_compact.py"
  - "tests/test_memory_cq_rows.py"
  - "tests/test_session_open_handler.py"
  - "tests/test_agent_units_cli.py"
  - "tests/test_config_read_project_scope.py"
  - "docs/ru/architecture.md"
  - "docs/en/architecture.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T08:35:42Z"
---

## Goal

filesize-mro-exempt-mcp снял бланкетный exempt с harness/claude/mcp/ и тем самым сделал видимыми три файла свыше cap 500. Из них tools.py оправдан навсегда (988 строк, из них 968 — одна декларативная таблица схем, 0 функций: строковый cap спрашивает «не слишком ли это длинно, чтобы читать как ЛОГИКУ», а таблица — не логика). Два других — настоящие god-модули и получили ВРЕМЕННЫЕ именные исключения в tausik/gates.json с указанием на эту задачу:

- harness/claude/mcp/project/handlers.py: 1281 строка, 77 функций-хендлеров, 0 литеральных данных. Под рационал «таблица диспетча» НЕ подпадает.
- harness/claude/mcp/codebase-rag/server.py: 562 строки, 18 функций, 12% сверх cap.

Задача: разрезать их по осмысленной границе (не механически до цифры — именно это породило деформацию, которую задача-родитель измерила: подъём до 26 модулей в полосе 350-399 при 22 в 300-349) и УДАЛИТЬ обе временные записи из exempt_files. Новый гейт class_surface должен подтвердить, что разрез не породил god-класса взамен god-модуля — то есть резать надо по доменам, а не выносить хвост в *_extra.py.

ВАЖНО про порядок: сначала выбрать доменные границы (какие хендлеры образуют связную группу), и только потом резать. Критерий успеха — не «файлы стали короче», а «границу можно назвать одним словом».

## Acceptance Criteria

AC1. harness/claude/mcp/project/handlers.py под cap 500 по счётчику самого гейта (gate_filesize.count_lines), и его ВРЕМЕННАЯ запись удалена из exempt_files И из _exempt_files_reasons в tausik/gates.json. Постоянная запись tools.py не тронута. Запись codebase-rag/server.py остаётся — она отошла задаче mcp-rag-server-module-split, и её текст обновлён так, чтобы называть новую задачу-владельца, а не эту.
AC2. Гейт filesize зелёный без именного исключения для handlers.py — то есть проходит по существу, а не по списку.
AC3. Границы разреза доменные: каждый новый модуль называется одним словом предметной области (session, knowledge, task, stack, role, verification, ...), и НИ ОДИН не назван *_extra / *_misc / *_utils / *_part2. Разрез следует УЖЕ СУЩЕСТВУЮЩЕМУ в этом же пакете прецеденту: модуль экспортирует dict <DOMAIN>_HANDLERS, handlers.py делает _DISPATCH.update(...) — как handlers_spec.py и handlers_adapt.py.
AC4. Гейт class_surface зелёный: разрез не породил god-класса взамен god-модуля. Baseline в tausik/gates.json не вырос (храповик только вниз).
AC5. Поверхность MCP не изменилась: множество ключей _DISPATCH до и после разреза СОВПАДАЕТ поимённо. Пришпилено тестом, который сверяет ключи _DISPATCH с именами инструментов в tools*.py — ни один инструмент не потерян и ни один не появился молча.
AC6. Живой прогон: MCP-сервер стартует и отвечает (server.py --probe success), tausik doctor зелёный, bootstrap.py --ide all разворачивает новые модули во ВСЕ профили — проверить фактическим наличием файлов в .claude/mcp/project/ и хотя бы в одном не-claude профиле.
AC7. НЕГАТИВ: ни один хендлер не изменил поведение — разрез механически-переносящий, не переписывающий. Полный pytest без новых падений относительно baseline сессии #147 (6396 passed / 24 skipped / 0 failed).
AC8. Гейты зелёные (ruff/mypy/scoped pytest), CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью, docs/{ru,en}/architecture.md отражают новую раскладку пакета MCP-хендлеров, если она там описана.

## Plan

## Rollback

git revert коммита. Разрез механически-переносящий: тела функций не меняются, меняется только модуль-владелец и импорт. Откат восстанавливает единый handlers.py; при откате ОБЯЗАТЕЛЬНО вернуть обе временные записи в exempt_files/tausik/gates.json, иначе гейт filesize станет красным на восстановленном god-модуле. Промежуточная страховка на время работы: записи exempt снимаются ПОСЛЕДНИМ шагом, после зелёного прогона, а не первым.

## Journal

- 2026-07-28T08:10:32Z [implementation] — Разрез выполнен. handlers.py 1345 -> 174 строки. Девять доменных модулей (task 182, session 235, status 186, knowledge 250, hierarchy 67, stack 101, role 87, verification 168, cq 86) + handlers_render 19 под общий render_list. Границы взяты из СЕКЦИОННЫХ КОММЕНТАРИЕВ самого файла, конвенция <DOMAIN>_HANDLERS + _DISPATCH.update продолжает уже существующий прецедент handlers_spec/handlers_adapt. Ни одного *_extra/_misc/_utils. Побочно найдено и исправлено: _project_dir() в handlers.py стала мёртвой после выноса cq — удалена, а комментарий в server.py, ссылавшийся на неё, переписан на фактических потребителей cwd (handlers_skill, handlers_cq, handlers_stack). Новый тест test_mcp_dispatch_surface.py (13 кейсов) сверяет ключи _DISPATCH со СХЕМОЙ tools*.py, а не с зашитым числом, и отдельно ловит тихую коллизию имён при dict.update. Восемь тестовых файлов переведены на импорт из доменных модулей вместо приватных символов handlers. _DISPATCH: 117 записей, импорт развёрнутой копии проверен. gate filesize exit=0 БЕЗ именного исключения; временная запись handlers.py снята из tausik/gates.json, запись server.py переадресована новой задаче mcp-rag-server-module-split. bootstrap --ide all: модули развернулись во все профили (проверено .claude/ и .opencode/). ruff чист. ЗАМЕЧАНИЕ (не регресс, пре-существующее): harness/ вообще не входит в область mypy проекта (гоняется `mypy scripts`), поэтому 22 no-any-return в MCP-дереве не видит никто; на HEAD до разреза те же ошибки присутствуют.
- 2026-07-28T08:30:27Z [implementation] — Полный pytest: 6415 passed / 24 skipped / 2 failed (680 s). Разобраны оба падения. (1) test_gate_class_surface::test_named_exempt_files_are_exempt_and_documented[handlers.py] — МОЁ и по существу верное падение: тест ХАРДКОДИЛ перечень exempt_files, дублируя реестр tausik/gates.json, поэтому снятие исключения ломало тест, к которому оно отношения не имеет. Починено по конвенции #339 — параметры выводятся из gates.json, а не перечисляются в тесте; плюс добавлен новый кейс test_no_reason_documents_an_exemption_that_no_longer_exists (осиротевшая причина читается аудитором как живое исключение). 19 тестов зелёные. (2) test_mypy_clean::test_scripts_tree_is_mypy_clean — НЕ МОЁ, пре-существующий красный. Доказано чисто: git worktree на HEAD (cd0617f) + тот же venv дают ТЕ ЖЕ 2 ошибки import-untyped на PyYAML (renar_conformance.py, project_cli_renar.py). Пакеты venv не менялись с 03.05.2026, оба renar-файла в рабочем дереве не тронуты. Отчёт сессии #147 «mypy Success 291 файл / 0 failed» действительности не соответствовал. Закрывается отдельной задачей mypy-blind-to-harness-mcp-tree (AC3). После правок: bootstrap --ide all, ruff чист по scripts+tests+harness, doctor без drift.
- 2026-07-28T08:35:40Z [implementation] — AC1 ✓ handlers.py 1345 -> 174 строки по счётчику самого гейта; временная запись handlers.py удалена и из exempt_files, и из _exempt_files_reasons в tausik/gates.json. Постоянная запись tools.py не тронута. Запись codebase-rag/server.py оставлена и её текст переписан так, что называет нового владельца mcp-rag-server-module-split. AC2 ✓ scripts/gate_filesize.py exit=0 БЕЗ именного исключения для handlers.py. Де-exempt полный: _resolve_exempt_files не имеет хардкод-фолбэка (возвращает пустой frozenset при отсутствии ключа), проверено чтением кода — то есть исключение не воскресает из источника. AC3 ✓ Девять доменных модулей: task 182, session 235, status 186, knowledge 250, hierarchy 67, stack 101, role 87, verification 168, cq 86 + handlers_render 19. Каждое имя — одно слово предметной области, взятое из СЕКЦИОННЫХ КОММЕНТАРИЕВ самого файла (--- Tasks ---, --- Sessions ---, --- Knowledge (Memory) ---, --- Hierarchy (Epics & Stories) ---, --- Roles (CRUD) ---). Ни одного *_extra/_misc/_utils/_part2. Конвенция <DOMAIN>_HANDLERS + _DISPATCH.update продолжает существующий прецедент handlers_spec/handlers_adapt, а не заводит второй шаблон. AC4 ✓ Гейт class_surface PASS на task_done (92 класса в 74 файлах). Baseline в tausik/gates.json не тронут — SQLiteBackend 129 / ProjectService 118 без изменений, храповик не сдвинут. Разрез вынес ФУНКЦИИ, ни одного нового класса не создано. AC5 ✓ tests/test_mcp_dispatch_surface.py, 13 кейсов, сверка со СХЕМОЙ tools*.py, а не с зашитым числом: каждый объявленный инструмент резолвится; ни один хендлер не обслуживает необъявленный; ни один инструмент не заявлен двумя доменами (dict.update разрешил бы коллизию молча); каждая доменная таблица действительно слита; каждая запись вызываема с двумя аргументами. _DISPATCH = 117 записей. AC6 ✓ Живой прогон: импорт РАЗВЁРНУТОЙ копии .claude/mcp/project/handlers.py успешен, handle_tool вызываем. tausik doctor зелёный, Bootstrap drift none. bootstrap.py --ide all прогнан трижды; новые модули присутствуют и в .claude/mcp/project/, и в .opencode/mcp/project/ (проверено листингом). AC7 ✓ Тела хендлеров перенесены дословно. Полный pytest: 6415 passed / 24 skipped / 2 failed (680 s). Оба падения разобраны. (а) test_gate_class_surface[handlers.py] — падение по существу верное: тест ХАРДКОДИЛ перечень exempt_files, дублируя реестр. Починено по конвенции #339 выводом параметров из gates.json + новый кейс на осиротевшую причину; 19 тестов зелёные. (б) test_mypy_clean — ПРЕ-СУЩЕСТВУЮЩИЙ красный, не мой: git worktree на чистом HEAD cd0617f с тем же venv даёт ТЕ ЖЕ 2 ошибки import-untyped на PyYAML; пакеты venv не менялись с 03.05.2026; оба renar-файла в дереве не тронуты. Заведена задача mypy-blind-to-harness-mcp-tree. AC8 ✓ ruff «All checks passed» по scripts+tests+harness. Scoped pytest PASS над 16 из 356 файлов. CHANGELOG.md + CHANGELOG.ru.md — прозаические записи-зеркала. docs/{ru,en}/architecture.md: карта модулей MCP переписана под новую раскладку. Domain: разрез проверен НЕ только тестами — живой MCP-импорт развёрнутой копии, 117 резолвящихся инструментов и зелёный doctor означают, что агент, разговаривающий с фреймворком через MCP, получает ту же поверхность, что и до разреза. Побочно устранены две неправды в коде: мёртвая _project_dir() в handlers.py вместе со ссылавшимся на неё комментарием server.py, и утверждение «handlers.py 1281 строка, 77 хендлеров» в комментарии gate_filesize.py.
- 2026-07-28T08:35:58Z [done] — Negative: негативные сценарии AC отработаны явно, а не подразумевались. (1) Потеря инструмента при переносе — test_no_handler_routes_a_tool_the_schema_never_declares и test_every_declared_tool_has_a_handler сверяют обе стороны со схемой tools*.py; потерянный инструмент проявился бы только во время вызова как «Unknown tool», а не при импорте, поэтому проверка нужна именно двусторонняя. (2) Тихая коллизия имён — test_no_two_domain_modules_claim_the_same_tool: dict.update разрешил бы дубликат в пользу слитого последним, без единой ошибки где-либо. (3) Незаслитая доменная таблица — параметризованный test_every_domain_table_is_merged_into_dispatch: модуль, который никто не слил, невидим, его инструменты просто не резолвятся. (4) Файл сверх cap под mcp/ БЕЗ именного исключения по-прежнему ловится — существующий test_oversized_non_dispatch_file_under_mcp_is_caught зелёный, то есть снятие исключения не открыло дыру для новых файлов. (5) Осиротевшая причина исключения — новый test_no_reason_documents_an_exemption_that_no_longer_exists: причина, пережившая своё исключение, читается аудитором как живое исключение.
- 2026-07-28T08:36:05Z [done] — Root cause (documentation): перечень exempt_files был записан ДВАЖДЫ — в реестре tausik/gates.json и литералом в tests/test_gate_class_surface.py — поэтому снятие исключения роняло тест, который к этому исключению отношения не имел, и падение выглядело как регресс разреза. Prevention: перечень, дублирующий реестр, выводить из источника (конвенция #339); параметры теста читаются из gates.json, добавление исключения по-прежнему обязано принести причину, а снятие больше не требует правки теста.
