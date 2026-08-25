---
slug: v2-verify-receipt-as-argument
title: "[1.8] Квитанция verify передаётся аргументом в task done вместо поиска свежей строки в кэше"
status: done
epic: stateless-session
story: stateless-core
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: null
scope_exclude: "[\"scripts/crypto_ed25519.py\",\"scripts/crypto_keys.py\",\"scripts/crypto_sign.py\",\"scripts/security_pattern.py\",\".claude/**\",\".cursor/**\",\".kilo/**\",\".opencode/**\",\".qwen/**\"]"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/cli.md"
  - "docs/ru/receipts.md"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/tools_extra.py"
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "scripts/crypto_receipt.py"
  - "scripts/gate_post_scope.py"
  - "scripts/gate_verify_first.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_constants.py"
  - "scripts/verify_receipt_emit.py"
  - "scripts/verify_recent_lookup.py"
  - "scripts/verify_run_record.py"
  - "tests/test_ddl_fixture_parity.py"
  - "tests/test_gate_runs_failures.py"
  - "tests/test_migration_v43_model_mismatch.py"
  - "tests/test_security_sensitive.py"
  - "tests/test_service_verification.py"
  - "tests/test_tausik_service.py"
  - "tests/test_verify_cache.py"
  - "tests/test_verify_cache_empty_scope.py"
  - "tests/test_verify_first_contract.py"
  - "tests/test_verify_receipt_check.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_verify_scope_honesty.py"
  - "scripts/backend_migrations_v44.py"
  - "scripts/verify_handle.py"
  - "scripts/verify_handle_check.py"
  - "tests/test_init_schema_upgrade_order.py"
  - "tests/test_schema_index_parity.py"
  - "tests/test_verify_handle.py"
  - "tests/test_verify_handle_integration.py"
scope_paths:
  - "scripts/crypto_receipt.py"
  - "scripts/verify_*.py"
  - "scripts/gate_verify_first.py"
  - "scripts/gate_post_scope.py"
  - "scripts/service_verification.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/backend_migrations*.py"
  - "scripts/backend_schema*.py"
  - "scripts/backend_init.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/*"
  - "docs/ru/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T11:50:42Z"
---

## Goal

Направление задано решением #208. Первая конкретная цель stateless-курса.

КАК СЕЙЧАС. `verify --task` пишет строку в verification_runs и выпускает подписанную ed25519-квитанцию. `task done` квитанцию НЕ принимает: он вызывает has_fresh_verify_run(conn, slug, relevant_files) и ИЩЕТ строку по четырём условиям — совпадение files_hash, совпадение подписи набора гейтов, возраст меньше DEFAULT_CACHE_TTL_S (10 минут), плюс запрет для security-чувствительных путей. То есть зелёный результат живёт как серверное состояние с временем жизни, а связь между «проверил» и «закрываю» — это поиск в БД, а не предъявленный документ.

ЧТО ЛОМАЕТСЯ ИМЕННО ИЗ-ЗА ЭТОГО. Наблюдалось в сессии #152: два закрытия подряд вернули cache_status=git-mismatch (объявленная область оказалась подмножеством изменённого по git — верное поведение, но агент узнаёт об этом как о ПРОМАХЕ КЭША, а не как о содержательном отказе), и один verify дал status=miss с пустой областью. Плюс отдельный класс: MCP-процесс держит модули в памяти, поэтому «свежесть» считают два процесса с разным представлением о коде.

КУДА ИДЁМ. `verify` возвращает квитанцию агенту, агент передаёт её в `task done` обычным аргументом, `task done` ПРОВЕРЯЕТ ПОДПИСЬ И СОДЕРЖАНИЕ (какая область покрыта, какие гейты отработали, против какого состояния дерева), а не ищет строку. Свойства, которые это даёт: срок годности едет ВНУТРИ квитанции, а не в конфиге сервера; отказ формулируется по существу («квитанция покрывает область уже изменений»), а не как «не нашёл»; квитанция переносима между процессами и машинами — ради чего её и подписывают.

ГРАНИЦЫ И ЧЕГО НЕ ДЕЛАТЬ. verification_runs НЕ удаляется: это журнал прогонов и он остаётся источником для метрик и аудита. Меняется способ ПРЕДЪЯВЛЕНИЯ, а не факт записи. Запрет кэша для security-чувствительных областей сохраняется и должен быть выражен внутри проверки квитанции, а не потеряться при переносе. Совместимость: старые вызовы task done без квитанции обязаны либо продолжать работать через прежний поиск, либо отказывать ЯВНО с указанием, что предъявить, — молчаливое ужесточение недопустимо.

ЗАВИСИМОСТЬ. Осмысленно делать вместе с v2-mcp-request-time-db-routing: обе задачи убирают состояние, привязанное к процессу сервера.

## Acceptance Criteria

1. СХЕМА tausik-receipt/v3. Квитанция несёт: schema=tausik-receipt/v3, files (отсортированный список относительных путей объявленной области), gate_signature (та же sha256 по "name=<command>|sev=<severity>", что уходит в verification_runs.command), files_hash, expires_at. Квитанция v2 читается как ЧАСТИЧНАЯ (unknown по files/gate_signature), а не как полная: тест доказывает, что v2 НЕ проходит валидацию хендла и отказ НАЗЫВАЕТ недостающие поля.
2. ХЕНДЛ. verify возвращает агенту хендл вида <run_id>.<nonce>, nonce >= 128 бит из secrets. Хендл виден И в CLI-выводе verify, И в результате MCP-инструмента tausik_verify. Тест: два verify подряд дают разные nonce.
3. ТОЧЕЧНЫЙ LOOKUP ВМЕСТО ПОИСКА ПО СВЕЖЕСТИ. task done принимает --verify-handle. При переданном хендле has_fresh_verify_run НЕ вызывается: строка берётся по run_id, nonce сверяется constant-time. Тест: закрытие с хендлом проходит при возрасте прогона БОЛЬШЕ 600 с, пока expires_at квитанции не истёк.
4. ВАЛИДАЦИЯ FAIL-CLOSED, каждый пункт отдельным тестом на ОТКАЗ: хендла нет в БД; nonce не совпал; run.task_slug != закрываемая задача; files_hash пересчитан по живым файлам и не совпал; gate_signature квитанции != command строки; хендл уже погашен; expires_at в прошлом. Ни один из семи не проходит молча.
5. REDEEM-ONCE. Погашение атомарно (UPDATE ... WHERE redeemed_at IS NULL + проверка rowcount); повторное предъявление того же хендла отказывает (replay, SEP-2322). Тест на повтор.
6. SECURITY-ЧУВСТВИТЕЛЬНЫЕ ПУТИ. is_cache_allowed применяется к списку files ИЗ КВИТАНЦИИ, а не к аргументу вызова. Тест: квитанция, покрывающая security-путь, не даёт закрыть задачу по хендлу.
7. ДЕГРАДАЦИЯ ПЕРЕСТАЁТ БЫТЬ ТИХОЙ. verify_receipt_check не возвращает ok=True на произвольном исключении. Отсутствие ключа — ЯВНЫЙ режим, отличимый в выводе от «ключ есть, проверка прошла». Тест на оба режима.
8. СОВМЕСТИМОСТЬ БЕЗ ТИХОГО УЖЕСТОЧЕНИЯ. task done БЕЗ --verify-handle работает прежним поиском по свежести. Тест доказывает, что старый путь жив.
9. TTL — ДОКУМЕНТИРОВАННАЯ ПОЛИТИКА (SEP-2567): срок годности назван в описании инструмента tausik_verify и в docs/ru/receipts.md, а не только в константе. Тест читает описание инструмента и требует наличия срока.
10. Гейты зелёные; docs/ru/receipts.md и docs/ru/cli.md описывают хендл; CHANGELOG обновлён.

## Plan

## Rollback

git revert коммита задачи. Схема БД: добавляются ТОЛЬКО новые nullable-колонки в verification_runs (handle_nonce, redeemed_at, expires_at) — откат кода их просто перестаёт читать, DROP не нужен и данные не теряются. Поведение: путь без --verify-handle сохраняется рабочим (AC8), поэтому откат кода возвращает прежний поиск по свежести без миграции вниз. Схема квитанции: v2-квитанции остаются валидными (проверка ре-канонизирует сохранённые байты), новые v3 после отката читаются старым кодом как v2 с лишними полями подписи — подпись сходится, потому что канонизация идёт по сохранённому payload.

## Journal

- 2026-08-01T20:18:58Z [planning] — ИССЛЕДОВАНИЕ ПЕРЕД РЕШЕНИЕМ #218 (сессия #155, по требованию владельца). Источники и замеры. ПОПРАВКА ПО ИСТОЧНИКУ, называю прямо: статья владельца на Хабре (habr.com/ru/companies/tuturu/articles/1063414/) НЕ содержит материала про сессии и состояние. Три независимых прохода по тексту: слов «сессия», «состояние», «stateless», requestState в ней нет. Есть только раздел про АВТОРИЗАЦИЮ — и он подтверждает то, что мы завели в 2.0: «В стандарте MCP авторизация для удалённых HTTP-серверов описана через OAuth 2.1», «Локальные клиенты… могут хранить секрет на устройстве пользователя и передавать его в заголовке», «Спецификация MCP прямо запрещает помещать токен в строку запроса: он может попасть в логи». Опереть решение по квитанции на статью нельзя; опора — спецификация. ЧТО ГОВОРИТ СПЕЦИФИКАЦИЯ (это и есть основание #218): - SEP-2567 «Sessionless MCP via Explicit State Handles», статус Final. Мотив дословно: «After more than a year in the spec, sessions have not converged on a consistent meaning across clients». Канон: «servers that need to maintain state across tool calls do so by returning an identifier from a creation tool and accepting it as a parameter on subsequent calls». ВАЖНАЯ ОГОВОРКА СПЕЦА: «That third point is not a protocol change… "Explicit state handles" is a tool-design pattern». Про TTL: «Durability is documented in the tool description… A policy only in server documentation is not visible to the model». Про хендл как токен: «at least 128 bits of cryptographically secure entropy». Про TTL честно: «Servers already rely on TTL-based expiry today; the session boundary is not what performs cleanup. Explicit IDs with a documented durability policy is the same mechanism, made explicit». - SEP-2322 «Multi Round-Trip Requests», Final. Ключевое для нас: «If a request contains a requestState field, servers MUST always validate that state, as the client is an untrusted intermediary… SHOULD encrypt… MUST use some mechanism to cryptographically bind the data to the original user… Servers using plaintext state MUST treat the decoded values as untrusted input». Плюс риск replay назван прямо. - Релиз 2026-07-28: «We've officially retired the initialize/initialized exchange along with the Mcp-Session-Id header… mint an explicit handle from a tool and have the model pass it back as an argument. We found this works better than session state hidden in the transport». ЧТО У НАС СЕЙЧАС, ТОЧНО (это меняет формулировку задачи): Серверным состоянием с TTL является СТРОКА в verification_runs, а НЕ квитанция. Квитанция — печать ПОВЕРХ строки. Поиск: verify_recent_lookup.py:30, WHERE task_slug=? AND exit_code=0 AND files_hash=? AND command=? ORDER BY id DESC LIMIT 1, затем возраст <= 600 с (verify_constants.py:16). command = «trigger=verify|sig=<16hex>|files=<csv>», где sig — sha256 по отсортированным «name=<command>|sev=<severity>»; ИМЕННО ЭТИМ сегодня инвалидируется зелёный при смене команды гейта. files_hash — sha256 по (path, mtime_ns, size, sha256 первых 4 КиБ), verify_files_hash.py:26. Проверка квитанции (verify_receipt_check.py:25) БЛОКИРУЕТ на: битом JSON, невалидной подписи, receipt.task_slug != closing_slug или != row.task_slug, receipt.ran_at != row.ran_at. Три из четырёх — сверка СО СТРОКОЙ. Уберём строку — они перестанут значить что-либо. ЧЕТЫРЕ ЗАМЕРА, ОПРЕДЕЛИВШИЕ РЕШЕНИЕ: 1. КВИТАНЦИЯ НЕ САМОДОСТАТОЧНА. build_receipt (crypto_receipt.py:36, схема tausik-receipt/v2) кладёт gates как {name, passed, severity} — БЕЗ command. И списка файлов в ней нет: только scope («standard») и files_hash. Значит она не фиксирует НИ что запускалось, НИ над чем. Проверить то, что проверяет нынешний поиск, она физически не может. 2. АГЕНТ КВИТАНЦИИ НЕ ПОЛУЧАЕТ. CLI печатает только «Receipt: signed (run #N, key <fp>)» (project_cli_verify.py:87); MCP-инструмент tausik_verify её не возвращает. Это неявная, но СЕГОДНЯ ДЕЙСТВУЮЩАЯ защита: подделать зелёный можно было бы только записью в verification_runs, а прямой доступ к БД запрещён и в инструментарии отсутствует. 3. КЛЮЧ ДОСТУПЕН АГЕНТУ. docs/ru/receipts.md:205-228 дословно: «Приватный seed лежит в .tausik/keys/project.key ВНУТРИ рабочего дерева… Это НЕ attestation против агента. Агент… может прочитать seed и выпустить подпись, которую ключ примет». Вынос отложен задачей l26-signing-key-boundary. Следствие: сделать квитанцию предъявительской = снять единственное препятствие, не опиравшееся на секретность ключа. 4. ПЕРЕНОСИМОСТЬ НЕСОВМЕСТИМА С НЫНЕШНИМ files_hash: в него входит mtime_ns, а git checkout ставит mtime = now, поэтому на другой машине хеш не сойдётся НИКОГДА. Переносимость требует контентного хеша, то есть чтения файлов целиком вместо 4 КиБ — расход, который verify_files_hash.py:63 сознательно отверг. ЧТО ИЗ ЭТОГО СЛЕДУЕТ ДЛЯ РАБОТЫ (порядок внутри задачи): (1) tausik-receipt/v3: добавить в квитанцию СПИСОК ФАЙЛОВ и gate_signature. Без этого «квитанция аргументом» не проверяет ничего. Старые квитанции читать как unknown, НЕ как полные. (2) Хендл: verify возвращает run_id + nonce >= 128 бит; task done принимает --verify-handle обычным аргументом; сервер делает ТОЧЕЧНЫЙ lookup по хендлу, а не поиск по свежести. (3) Валидация на приёме, fail-CLOSED: хендл существует, принадлежит этой задаче, files_hash пересчитан по живым файлам и совпал, gate_signature совпала, хендл НЕ погашен ранее (redeem-once против replay, требование SEP-2322), не истёк. (4) TTL становится ДОКУМЕНТИРОВАННОЙ политикой в описании инструмента, видимой модели (SEP-2567), а не скрытым окном в 600 с. (5) Предикат is_cache_allowed для security-чувствительных путей применяется к списку файлов ИЗ квитанции — работает только после (1), иначе запрет тихо испарится. (6) verify_receipt_check сегодня ловит ЛЮБОЕ исключение и возвращает ok=True (verify_receipt_check.py:39-41). Когда квитанция станет единственным доказательством, такая деградация недопустима: нужен fail-closed плюс ЯВНЫЙ режим «без ключа квитанции не требуются, гейты гоняются inline». ЧЕГО ЗАДАЧА НЕ ДЕЛАЕТ, И ЭТО НАДО СКАЗАТЬ ВСЛУХ: переносимость квитанции между машинами в 1.8 НЕ достигается (нужен контентный хеш и вынос ключа). Цель формулируется точнее: убрать зависимость от TTL и от процесса, а не убрать БД. Полный stateless здесь недостижим и не нужен — пункты про «эта задача» и про replay ТРЕБУЮТ хранилища, но требуют идемпотентного точечного lookup, а не временнОго поиска. Это ровно то, что даёт SEP-2567.
- 2026-08-03T09:38:53Z [implementation] — Сессия #159. Сессия #158 закрыта досрочно: её ёмкость (144/200) не вмещала бюджет 120. В #158 задаче дописаны AC (10 пунктов), scope_paths, scope_exclude и rollback_plan. Начинаю шаг (1) — схема tausik-receipt/v3.
- 2026-08-03T09:59:08Z [implementation] — Шаги (1)-(3) написаны. Схема tausik-receipt/v3 (files, gate_signature, expires_at) + missing_v3_fields; verify_handle.py (минт, парс, атомарное погашение); verify_handle_check.py (fail-closed валидация, 13 отказов); миграция v44 (три nullable-колонки + индекс), SCHEMA_VERSION 43->44, SCHEMA_SQL и backend_schema_indexes синхронизированы. Хендл протянут: verify -> details -> run_verify_for_task -> CLI print + MCP _handle_lines; task done --verify-handle -> cli -> service_task -> service_task_done -> service_gates -> gate_post_scope (единая форма вызова) -> gate_verify_first._enforce_handle. Дальше: тесты.
- 2026-08-03T10:24:17Z [implementation] — НАЙДЕНО И ИСПРАВЛЕНО В ХОДЕ РАБОТЫ, три дефекта. (1) МОЙ СОБСТВЕННЫЙ: 'run.get("exit_code") or 1' — ноль ложен, поэтому КАЖДЫЙ зелёный прогон читался как красный. Поймали новые тесты, а не глазами. (2) ДЕФЕКТ ПУТИ ОБНОВЛЕНИЯ, найден живым запуском CLI, не тестами. Индекс idx_verify_handle был положен в INDEXES_SQL — очевидное место. init_schema применяет INDEXES_SQL ДО миграций, поэтому на СУЩЕСТВУЮЩЕЙ базе колонки ещё нет: 'no such column: handle_nonce' на КАЖДОЙ обновляемой установке, при этом на свежих базах всё зелено. Правило записано в докстринге самого backend_schema_indexes — и всё равно было нарушено, потому что путь, который оно защищает, не исполнялся ни одним тестом. Индекс перенесён в миграцию v44; заведён tests/test_init_schema_upgrade_order.py, который поднимает базу на версию НАЗАД и зовёт настоящий init_schema. Проверено обратно: с возвращённым багом тест краснеет тремя случаями, без бага — зелёный. (3) СЛОЙ: verify_run_record (запись) импортировал приватный парсер из verify_handle_check (политика) — направление неверное. Парсер подписи гейтов переехал в verify_recent_lookup, к своему близнецу _extract_files_from_cache_command: обе половины ОДНОЙ строки команды читаются теперь в одном месте.
- 2026-08-03T10:53:30Z [implementation] — РЕВЬЮ ДВУМЯ ЛИНЗАМИ (конвенция #364): «утверждения против кода» и «обход + путь обновления». Шесть находок, все закрыты. КРИТИЧНОЕ — redeem() делал голый conn.commit(). MCP держит ОДНО соединение на все потоки без мьютекса (project_backend, check_same_thread=False), поэтому commit фиксировал бы ЧУЖОЙ недописанный task_done: задача осталась бы status=done, а её каскад, заметки и аудит откатились бы. Введён _write(): conn.in_transaction снимается ДО записи, commit только если транзакцию открыли мы; иначе запись едет с транзакцией владельца, что и есть верная семантика. Два теста, один проверяет именно неоткат чужой записи. ВЫСОКОЕ — ветка хендла стоит ПЕРЕД блоком «область не объявлена» (сознательно: область берётся из квитанции). Побочный эффект: закрытие БЕЗ объявленных файлов доходило до хендла, git-сверка на стороне task done меряла пустое множество, возвращала unknown и не замечала ухода дерева. Сверка переделана в _check_git_scope против списка ИЗ КВИТАНЦИИ, делегируя security_block_reason, чтобы правило не раздвоилось. Блокирует ровно security-расхождение; обычное проговаривается в вердикте (решение #138). СРЕДНЕЕ — load_public с encoding=ascii ронял UnicodeDecodeError на битом ключе; наверху никто не ловит, CLI показал бы traceback вместо отказа. Ловится вместе с KeyError_/OSError/ValueError: непрочитаемый ключ и отсутствующий — один факт. СРЕДНЕЕ — auto_verify гоняет verify-гейты ВНУТРИ task done и писал их с trigger=verify, то есть выпускал настоящий часовой предъявимый хендл побочным эффектом закрытия. Если закрытие потом блокировалось, хендл оставался валидным для незакрытой задачи. Добавлен allow_handle=False, протянут run_gates_with_cache -> _record_verification -> record_run. Инвариант «закрытие не может само себя удостоверить» теперь выражен отдельно от метки триггера, которая нужна кэшу. ВЫСОКОЕ (доки) — таблица отказов в receipts.md выдавала себя за исчерпывающую и не называла три реальных: беcключевой проект, подменённый task_slug, подменённый ran_at. Плюс дописаны files_hash-против-строки и git-расхождение. НИЗКОЕ — nonce в верхнем регистре отвергался как неверный (сравнение побайтовое, token_hex даёт нижний). Нормализуется в parse_handle. Комментарий про «оракул» переписан: run_id не секрет, различимость этих двух отказов ничего не утекает; constant-time нужен для 128-битного значения. ОТКЛОНЕНО ОДНО. Ревьюер счёл дырой то, что widened-scope не ловится: агент объявляет docs/x.md, правит auth.py, закрывает. Проверено по коду — на пути task done ДО post-scope гейтов работает run_gates_with_cache(trigger=task-done), который считает describe_declared_scope и падает со scope-security-mismatch. Половина про security закрыта выше по потоку; половина про несекьюрное расхождение не блокирует ПО РЕШЕНИЮ #138. Тем не менее дыра для пустой области была настоящей и закрыта отдельно (см. ВЫСОКОЕ).
- 2026-08-03T11:07:36Z [implementation] — ДРЕЙФ ФИКСТУР ЗАКРЫТ ПОЛНОСТЬЮ, и он оказался шире заявленного. Гейт test_ddl_fixture_parity параметризован ПО ТАБЛИЦЕ, поэтому все нарушители схлопываются в один красный случай — по тексту ошибки я насчитал пять файлов, на деле их девять, а рукописных копий схемы verification_runs одиннадцать (в test_verify_first_contract их три внутри одного файла). Починка пяти оставила бы гейт красным. Все одиннадцать заменены на conftest.VERIFICATION_RUNS_DDL; grep по tests/*.py больше не находит ни одной рукописной CREATE TABLE verification_runs. Минус 355 строк дублирования. ПОБОЧНОЕ, стоит записи: execute -> executescript было необходимостью, а не вкусом. canonical_ddl возвращает блок, уже оканчивающийся на ');', поэтому '+ ";"' даёт пустой хвостовой оператор, который Connection.execute отвергает как многооператорный, а executescript принимает. ПИН КОЛОНОК обновлён 13 -> 16, и проза вокруг него потребовала большего, чем замена цифры: она обосновывала выбор PRAGMA вместо регулярки конкретным промахом «18 против 13 настоящих». Наивный подсчёт по запятым теперь даёт 31 против 16 — три новые колонки несут комментарии с запятыми. Числа пересчитаны, история 18/13 оставлена рядом: растущий разрыв сильнее исходного аргумента, поэтому объяснение читается как доказательство, а не как устаревший анекдот. ДВА ПАДЕНИЯ ИЗ ПОЛНОГО ПРОГОНА оказались сопутствующими: модуль с несвежей фикстурой падал до своих тестов, а не они сами. Правок в них не потребовалось.
- 2026-08-03T11:44:06Z [implementation] — AC-ПРОВЕРКА, каждый пункт с доказательством. AC1 схема v3 — crypto_receipt.RECEIPT_SCHEMA='tausik-receipt/v3', поля files/gate_signature/expires_at; missing_v3_fields судит ПО ЗНАЧЕНИЮ, не по ключу (build_receipt пишет None, а не опускает). Тесты TestLegacyReceiptIsPartial: v2 не проходит, отказ называет все три поля поимённо. ✓ AC2 хендл — secrets.token_hex(16)=128 бит; печатается CLI (project_cli_verify._emit_handle) И MCP (handlers_verification._handle_lines; раньше MCP не отдавал даже run_id). Тест на разные nonce у двух прогонов. ЖИВОЕ ДОКАЗАТЕЛЬСТВО: прогон #1656 напечатал 1656.23320eb32f74288155511d53041b854a. ✓ AC3 точечный lookup — task done --verify-handle не зовёт has_fresh_verify_run; тест test_handle_closes_a_run_older_than_the_cache_ttl закрывает прогон возрастом 12×TTL. ✓ AC4 fail-closed — 13 отказов, у каждого свой тест: форма, нет прогона, nonce, красный прогон, чужая задача, noncacheable, погашен, срок, нечитаемый срок, нет чека, битый JSON, плохая подпись, v2-чек, security-файлы, files_hash живой, files_hash строки, подпись гейтов строки, подпись гейтов живая, git-расхождение по security. ✓ AC5 redeem-once — UPDATE ... WHERE handle_redeemed_at IS NULL + rowcount; тесты на повтор, на прямой redeem дважды, на чужой nonce, и на то, что ОТКАЗАВШЕЕ закрытие хендл НЕ тратит. ✓ AC6 security по квитанции — is_cache_allowed(files ИЗ КВИТАНЦИИ) в _check_coverage; тест с квитанцией на auth/login.py. ✓ AC7 деградация названа — verify_receipt_check больше не единственный путь; в handle-пути беcключевой проект даёт ЯВНЫЙ отказ со словами «keyless project, not a failed check», отличимый от VALID. Два теста. ✓ AC8 совместимость — test_closing_without_a_handle_still_uses_the_freshness_lookup зелёный; плюс test_no_handle_and_no_verify_run_still_blocks доказывает, что старый путь не только жив, но и по-прежнему СТРОГ. ✓ AC9 TTL опубликован — DEFAULT_HANDLE_TTL_S=3600 назван в описании инструмента tausik_verify, в выводе CLI и в подписанном expires_at; тест читает описание инструмента и требует «1 hour» и «SINGLE-USE». ✓ AC10 гейты, доки, CHANGELOG — полный прогон 6779 passed / 0 failed; docs/ru/receipts.md (схема v3, раздел про хендл, таблица из 13 отказов), docs/ru/cli.md (--verify-handle), CHANGELOG.md и CHANGELOG.ru.md. ✓ ЛОКАЛЬНАЯ НАСТРОЙКА, называю явно: verify_pipeline_timeout_seconds=900 в .tausik/config.json. 60-секундный конверт мал для области в 45 файлов (28 сопоставленных тестовых файлов, 86 с). Файл в .gitignore, значит настройка НЕ уезжает в репозиторий и на других она не влияет.
- 2026-08-03T11:44:25Z [implementation] — AC-1: ✓ tests/test_verify_handle.py::TestLegacyReceiptIsPartial::test_refusal_names_every_missing_field AC-2: ✓ tests/test_verify_handle_integration.py::TestMintedHandleClosesTheTask::test_verify_returns_a_handle_and_task_done_accepts_it AC-3: ✓ tests/test_verify_handle.py::TestAgeIsNotFreshness::test_handle_closes_a_run_older_than_the_cache_ttl AC-4: ✓ tests/test_verify_handle.py::TestRefusals::test_files_changed_since_verify AC-5: ✓ tests/test_verify_handle.py::TestRedeemOnce::test_redeem_is_atomic_on_the_predicate AC-6: ✓ tests/test_verify_handle.py::TestSecuritySensitiveScope::test_security_paths_are_read_from_the_receipt AC-7: ✓ tests/test_verify_handle.py::TestKeylessProjectIsANamedMode::test_keyless_refusal_says_so_explicitly AC-8: ✓ tests/test_verify_handle_integration.py::TestBackwardCompatibility::test_closing_without_a_handle_still_uses_the_freshness_lookup AC-9: ✓ tests/test_verify_handle_integration.py::TestDurabilityPolicyIsPublished::test_tool_description_states_the_handle_lifetime AC-10: ✓ verification_run #1656 (green, 28 сопоставленных тестовых файлов) + tests/test_schema_index_parity.py::TestPostMigrationIndexesReachBothPaths::test_the_handle_index_specifically
