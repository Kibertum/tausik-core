---
slug: mcp-rag-server-module-split
title: "Разрезать codebase-rag/server.py (562 строки, 12% сверх cap) и снять его временный exempt"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "harness/claude/mcp/codebase-rag/server.py; новый или существующий harness/claude/mcp/codebase-rag/rag_<домен>.py; tausik/gates.json (снять 1 временную запись); tests/; CHANGELOG.md; CHANGELOG.ru.md"
scope_exclude: "harness/claude/mcp/project/** — весь пакет project не трогаем, это область mcp-handlers-god-module-split; scripts/gate_filesize.py hardcoded fallback; поведение индексации и ранжирования"
relevant_files:
  - "harness/claude/mcp/codebase-rag/server.py"
  - "harness/claude/mcp/codebase-rag/rag_tools.py"
  - "harness/claude/mcp/codebase-rag/rag_handlers.py"
  - "scripts/mcp_tool_counts.py"
  - "tausik/gates.json"
  - pyproject.toml
  - "tests/test_rag_tool_surface_parity.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "harness/claude/mcp/codebase-rag/"
  - "scripts/mcp_tool_counts.py"
  - "tausik/gates.json"
  - pyproject.toml
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-28T10:15:36Z"
---

## Goal

Отделена от mcp-handlers-god-module-split гейтом ёмкости сессии, и разделение оказалось правильным по существу: два файла связывал только общий коммит, который снял бланкетный exempt с harness/claude/mcp/ и выдал обоим ВРЕМЕННЫЕ именные исключения в tausik/gates.json. Домены у них разные, объём работы разный, и общая задача заставляла закрывать их одной распиской.

harness/claude/mcp/codebase-rag/server.py: 562 строки, 18 функций, 12% сверх cap 500 — то есть это НЕ god-модуль масштаба handlers.py (1345 строк, 77 хендлеров), а умеренный перебор. Соблазн подрезать до цифры здесь максимален и именно его надо избежать: родительский замер (filesize-mro-exempt-mcp) показал, что cap уже сдвинул распределение модулей в полосу 350-399, то есть влиял на то, ГДЕ проведены границы. Критерий тот же: границу можно назвать одним словом, а не «хвост, который не влез».

Рядом уже лежат rag_indexer.py (355), rag_detect.py (248), rag_web_cache.py (176), rag_store.py (169) — то есть доменное расслоение в этом пакете УЖЕ проведено и у него есть готовая конвенция имён rag_<домен>.py. Задача — понять, что осталось в server.py сверх собственно MCP-транспорта, и вынести это по существующей границе, а не завести новый шов.

Снять запись harness/claude/mcp/codebase-rag/server.py из exempt_files и _exempt_files_reasons; в записи для handlers.py текст про «retired by follow-up task mcp-handlers-god-module-split» остаётся, но перестаёт покрывать этот файл.

## Acceptance Criteria

AC1. harness/claude/mcp/codebase-rag/server.py под cap 500 по счётчику самого гейта (gate_filesize.count_lines), и его запись удалена из exempt_files И из _exempt_files_reasons в tausik/gates.json. Записи tools.py (постоянная) и handlers.py (временная, чужая) не тронуты.
AC2. Гейт filesize зелёный без именного исключения для этого файла.
AC3. Вынесенное живёт в модуле, названном по конвенции соседей rag_<домен>.py, и домен называется одним словом. НЕ допускается server_extra.py / server_part2.py / utils.py. Если подходящий сосед уже существует (rag_indexer / rag_detect / rag_store / rag_web_cache) — переносить туда, а не заводить новый шов.
AC4. Поверхность MCP не изменилась: множество имён инструментов, которые отдаёт сервер, до и после разреза совпадает поимённо (сверка списка TOOLS и таблицы диспетча).
AC5. Живой прогон: codebase-rag сервер стартует (probe/--help без ImportError), поиск search_code возвращает результаты на реальном индексе.
AC6. НЕГАТИВ: перенос механический — тела функций не переписываются; поведение индексации и поиска не меняется.
AC7. Гейты зелёные (ruff/mypy/scoped pytest), CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью, bootstrap.py --ide all прогнан (конвенция #321).

## Plan

## Rollback

git revert коммита. Перенос механический — восстанавливается единый server.py. При откате ОБЯЗАТЕЛЬНО вернуть запись harness/claude/mcp/codebase-rag/server.py в exempt_files и её текст в _exempt_files_reasons, иначе гейт filesize станет красным на восстановленном файле. Exempt снимается ПОСЛЕДНИМ шагом, после зелёного прогона.

## Journal

- 2026-07-28T09:57:01Z [implementation] — ПЛАН РАЗРЕЗА, границы выбраны по домену и сверены с уже принятой конвенцией, а не подобраны под цифру. Замер входа: server.py 562 строки по счётчику самого гейта (gate_filesize.count_lines), 18 функций, из них main() занимает 336 строк (196-532) — то есть вес не размазан, а сидит в одной функции. Соседи по пакету: rag_indexer 412, rag_detect 281, rag_web_cache 199, rag_store 197. Найденные границы: (1) строки 227-358 — тело @server.list_tools(), семь литералов Tool(...) со схемами, домен одним словом «tools»; (2) строки 372-498 — _sync_call_tool, диспетч по тем же семи именам, домен одним словом «handlers», плюс принадлежащие ему помощники _get_rag_store/_get_web_cache/_get_backend (50-71), _format_code_results (74), _format_knowledge_results (96), _find_related_tasks (122), _extract_relevant_files (142), _staleness_report (161), _archive_old_tasks (532). В server.py остаётся ТРАНСПОРТ: константы таймаута + _tool_timeout_sec, _setup_paths, argparse, охраняемый импорт mcp, Server(), регистрация list_tools/list_prompts/list_resources, обёртка call_tool с asyncio.wait_for и _run/asyncio.run. Целевые имена по конвенции соседей rag_<домен>.py: rag_tools.py и rag_handlers.py. ПРЕЦЕДЕНТ, а не новый шов: соседний пакет harness/claude/mcp/project разложен ровно так же — tools.py/tools_extra.py/tools_spec.py/tools_adapt.py плюс десять handlers_*.py; там же tools.py (988 строк) несёт ПОСТОЯННОЕ исключение с обоснованием «декларативная таблица схем — не логика», а наши вынесенные схемы ~135 строк и в исключении не нуждаются вовсе. Оценка после разреза: rag_tools ~135, rag_handlers ~290, server ~160 — все под cap 500 без подрезки. ВАЖНО ПО AC6: перенос механический, тела не переписываются; единственное неизбежное изменение сигнатуры — _sync_call_tool сейчас ЗАМЫКАНИЕ над project_dir внутри main(), после выноса project_dir передаётся параметром. Импорт Tool остаётся отложенным: rag_tools импортируется внутри main() ПОСЛЕ охраняемого блока try: from mcp... except ImportError, иначе сломается внятное сообщение «mcp package not installed» и сервер начнёт падать трейсбеком вместо подсказки. БАЗОВАЯ ЛИНИЯ AC4 снята ДО правки (AST по файлу): множество имён в схемах и множество имён в диспетче совпадают поимённо и равны семи — archive_done, cache_web_result, rag_status, reindex, search_code, search_knowledge, search_web_cache. Сырой список диспетча содержит reindex дважды, второе вхождение принадлежит _tool_timeout_sec (порог для долгой переиндексации), а не второму диспетчу — сравнивать надо множества. Эту сверку намерен оставить ТЕСТОМ, а не разовым скриптом, чтобы паритет схем и диспетча держался и дальше.
- 2026-07-28T10:01:03Z [implementation] — НАЙДЕНА СКРЫТАЯ ЗАВИСИМОСТЬ ОТ ФИЗИЧЕСКОГО РАСПОЛОЖЕНИЯ, до правки, а не после падения. scripts/mcp_tool_counts.py::count_rag_tool_defs считает инструменты RAG регуляркой r'^\s+Tool\(' ПО ФАЙЛУ harness/claude/mcp/codebase-rag/server.py. После выноса схем в rag_tools.py эта функция вернёт 0, а через неё завязаны count_mcp_tool_totals -> mcp_counts_flat -> constants.json и тесты tests/test_mcp_doc_tool_counts.py (docs/en/mcp.md и docs/ru/mcp.md утверждают число инструментов). Падение будет ГРОМКИМ (тест сверяет число в доке с числом в коде, 7 против 0), но это ровно тот класс, что конвенция #320: счётчик в доке ловится сканером только если файл в списке сканирования. Заметим асимметрию: project и brain считаются честно через len(TOOLS) импортом модуля, а RAG — регуляркой по исходнику, потому что импорт rag-схем тянет пакет mcp. Решение: НЕ переставлять указатель на rag_tools.py (это воспроизведёт ту же хрупкость на новом месте — следующий переезд снова обнулит счёт), а сканировать ВЕСЬ каталог пакета codebase-rag. Тогда счётчик переживает любую последующую перекладку схем внутри пакета, что и является предметом этой задачи. Область задачи расширена: scripts/mcp_tool_counts.py добавлен в scope_paths.
- 2026-07-28T10:15:28Z [implementation] — AC-1: ✓ server.py 562 -> 134 строки по счётчику самого гейта (gate_filesize.count_lines); записи harness/claude/mcp/codebase-rag/server.py удалены И из exempt_files, И из _exempt_files_reasons в tausik/gates.json; запись tools.py (постоянная) не тронута, запись handlers.py к этому моменту уже отсутствовала (снята предыдущей задачей), так что чужие записи не пострадали. AC-2: ✓ прогон scripts/gate_filesize.py -> exit 0 без именного исключения для этого файла. AC-3: ✓ rag_tools.py (149) и rag_handlers.py (320) — имена по конвенции соседей rag_<домен>.py, домены называются одним словом («tools» = схемы на проводе, «handlers» = что инструменты делают). Ни server_extra.py, ни server_part2.py, ни utils.py не заведены. Новый шов НЕ создан: разрез повторяет соседний пакет harness/claude/mcp/project (tools*.py + handlers_*.py). Переносить в существующих соседей (rag_indexer/rag_detect/rag_store/rag_web_cache) было НЕЛЬЗЯ — это индексация, детект и хранилища, а перенесённое суть схемы MCP и диспетч, другой домен. AC-4: ✓ поверхность MCP не изменилась поимённо. Базовая линия снята ДО правки: 7 имён. После: schema и dispatch совпадают множествами, те же 7 (archive_done, cache_web_result, rag_status, reindex, search_code, search_knowledge, search_web_cache). Закреплено тестом tests/test_rag_tool_surface_parity.py (4 проверки, включая защиту от вырожденного прохода на двух пустых множествах). AC-5: ✓ живой прогон в ДВУХ режимах. Скрипт как точка входа: `python harness/claude/mcp/codebase-rag/server.py` -> argparse требует --project (значит main() отработал). Полная загрузка: `python .../server.py --project . </dev/null` -> exit 0, stderr ПУСТОЙ. Реальный поиск на живом индексе: call_tool_sync('search_code', {'query':'claudemd drift report','limit':3}) вернул 1953 символа, 3 чанка из tests/test_claudemd_drift.py. AC-6: ✓ перенос механический, ДОКАЗАНО сравнением AST с копией файла до разреза: 11 функций (_get_rag_store, _get_web_cache, _get_backend, _format_code_results, _format_knowledge_results, _find_related_tasks, _extract_relevant_files, _staleness_report, _archive_old_tasks, _tool_timeout_sec, _setup_paths) имеют ПОБАЙТОВО идентичные тела; _sync_call_tool -> call_tool_sync тело идентично; список схем list_tools -> tool_definitions идентичен после отбрасывания добавленной строки документации (6666 символов дампа AST совпали). Единственное намеренное изменение сигнатуры — project_dir из замыкания стал параметром, как и планировалось. AC-7: ✓ ruff clean, ruff format применён, mypy Success (313 файлов объявленной области), срез 837 тестов (rag/mcp/doc/mypy/bootstrap) зелёный, bootstrap.py --ide all прогнан и развёрнутые копии содержат оба новых модуля, doctor «OK All clean», verify run #1559 подписан с [PASS] pytest, CHANGELOG.md + CHANGELOG.ru.md обновлены прозой на обоих языках. Domain: результат осмыслен вне тестов — сервер реально поднимается и реально ищет по живому индексу (см. AC-5), а не только парсится. ДВЕ ПОЛОМКИ, которые разрез внёс и которые тесты бы не поймали, найдены и закрыты: (1) счётчик scripts/mcp_tool_counts.py::count_rag_tool_defs искал Tool( регуляркой ПО ИМЕНИ server.py и после переезда схем вернул бы 0, ломая числа в docs/{en,ru}/mcp.md — переписан на сканирование всего каталога пакета, так что переживёт любую следующую перекладку; (2) завершающий `if __name__ == "__main__": main()` уехал вместе с последней функцией, и server.py остался БЕЗ точки входа — .mcp.json запускает его как скрипт, то есть он стартовал бы, всё определил и вышел с кодом 0, никого не обслужив, а мой первый вариант проверки AC5 этого не увидел, потому что импортировал модуль вместо запуска скрипта. Обе поломки теперь закреплены тестами (сканирование каталога + test_server_keeps_its_entrypoint).
