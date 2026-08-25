---
slug: mcp-update-claudemd-erases-the-memory-tail
title: "MCP-обработчик update_claudemd стирает хвост памяти, который обязан впрыскивать"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/claudemd_state.py"
  - "scripts/project_cli_extra.py"
  - "scripts/doc_drift_common.py"
  - "harness/claude/mcp/project/handlers_skill.py"
  - "tests/test_mcp_update_claudemd_parity.py"
  - "tests/test_doctor_multi_ide.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - AGENTS.md
scope_paths:
  - "harness/claude/mcp/project/*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-12T21:54:10Z"
---

## Goal

Вызов tausik_update_claudemd по MCP оставляет в CLAUDE.md тот же блок, что и CLI: Current State ПЛЮС хвост памяти (контексты, решения, конвенции, тупики, общие знания) — и обновляет файл-побратим AGENTS.md. Расхождение двух реализаций закрыто одной, а не выправлено копированием.

## Acceptance Criteria

AC1. tausik_update_claudemd по MCP пишет в CLAUDE.md блок, СОДЕРЖАЩИЙ '### Memory tail' с непустым перечнем, когда в базе есть память. Сегодня он пишет только Current State и удаляет хвост.
AC2. Расхождение закрыто ЕДИНОЙ реализацией, а не второй копией того же кода: обработчик MCP и команда CLI строят динамический блок одной функцией. Копия, выправленная вручную, разойдётся снова — так уже было (docstring flatten_for_injection называет этот случай прямым текстом).
AC3. Файл-побратим AGENTS.md обновляется и по пути MCP тоже — сегодня resolve_sibling_targets зовёт только CLI, поэтому по MCP AGENTS.md устаревает молча.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан СНАЧАЛА ПОКРАСНЕТЬ на текущем коде. Он вызывает обработчик MCP на CLAUDE.md с маркерами и памятью в базе и требует хвост в результате. Тест, написанный после правки и зелёный сразу, ничего не доказывает.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: пустая база памяти НЕ добавляет пустой заголовок '### Memory tail'. Поведение build_compact_memory_tail при пустой базе — вернуть [] — обязано сохраниться на пути MCP.
AC6. Ошибка чтения памяти НЕ роняет обновление CLAUDE.md: Current State записывается даже когда хвост построить не удалось (best-effort, как в CLI).

## Plan

## Rollback

git revert коммита; обработчик MCP возвращается к собственной копии — поведение ровно то, что было до правки

## Journal

- 2026-08-12T21:16:43Z [implementation] — КАК НАЙДЕН. Не поиском — дефект приехал сам, в штатном /start. Вызов tausik_update_claudemd дал в git diff CLAUDE.md -34/+3: исчезли '### Memory tail' целиком и блок общих знаний. Команда при этом отчиталась 'CLAUDE.md updated'. Тихий отказ ровно того класса, к которому у проекта нулевая терпимость, и на самой заметной двери — CLAUDE.md читает КАЖДЫЙ свежий агент. КОРЕНЬ. harness/claude/mcp/project/handlers_skill.py::handle_update_claudemd был второй независимой копией scripts/project_cli_extra.py::cmd_update_claudemd. В копии не было двух вещей: впрыска build_compact_memory_tail (строки 311-316 оригинала) и обхода resolve_sibling_targets, обновляющего AGENTS.md. ПОЧЕМУ ЭТО БИЛО ВСЕГДА, А НЕ ИНОГДА. /start Phase 2 предписывает именно MCP-вызов, MCP-first — жёсткое правило проекта, а текст скилла прямо обещает: 'injects compact memory tail ... so memory persists across sessions'. Значит хвост стирался КАЖДЫМ стартом сессии и возвращался только если кто-то запускал CLI. Блок памяти не жил между сессиями — он мигал. ГОРЬКАЯ ДЕТАЛЬ. В докстроке flatten_for_injection уже написано: два потребителя сведены к одной функции, 'so the two cannot drift apart again — which is precisely what had already happened by the time this was written'. Предупреждение было верным и недостаточным: расхождение случилось этажом выше, где обработчик MCP просто не звал эту функцию. ПОЧЕМУ ПРЕЖНИЕ ТЕСТЫ МОЛЧАЛИ. tests/test_claudemd_drift.py покрывает build_compact_memory_tail пятью тестами — напрямую, через стаб бэкенда. Ни один не спрашивал, КТО её вызывает. Покрытие функции было полным, покрытие пути — нулевым. ПРАВКА. Не исправленная копия, а единая: scripts/claudemd_state.py::build_dynamic_state строит блок, обе стороны зовут его. Заодно ушли два меньших расхождения — ветка теперь спрашивается у git вместо чтения .git/HEAD (в worktree там ФАЙЛ, и путь MCP всегда писал 'unknown'), и CLAUDE.md ищется по абсолютным кандидатам, а не относительно cwd MCP-сервера. Мёртвая после сведения _get_version удалена, комментарий в doc_drift_common.py, который её называл, поправлен — иначе ссылка на несуществующую функцию стала бы новой тихой ложью. ПРОВЕРКА. tests/test_mcp_update_claudemd_parity.py, 6 тестов. Первый прогон КРАСНЫЙ на неисправленном обработчике (assert '### Memory tail' in block -> в блоке только Current State) — зафиксировано до правки. После правки 6 passed. Ключевой тест пришпиливает ПАРИТЕТ построчно: каждая строка блока CLI обязана быть в блоке MCP. Тест на наличие подстроки пропустил бы третью потерю так же, как прежние пропустили эту. Развёрнуто в .claude/ полным bootstrap (300 scripts, 3 MCP). Работающий MCP-сервер сессии остался на старом коде — проверка шла через CLI, паритет доказан тестами.
- 2026-08-12T21:53:48Z [implementation] — Полный прогон набора ЗЕЛЁНЫЙ: 7008 passed, 24 skipped, 140 deselected, 0 failed, 0 errors (1030.76s). Это сильнее области квитанции: квитанция покрывает 12 тестовых файлов из 400, полный прогон покрывает все. Оба прогона на одном дереве. AC1 (хвост памяти по MCP): выполнен. test_mcp_update_claudemd_injects_memory_tail. Сверх теста — проверка РАЗВЁРНУТОЙ копии из .claude/, а не только исходников: обработчик вызван на временном проекте, хвост и решение оказались и в CLAUDE.md, и в AGENTS.md. AC2 (единая реализация): выполнен. scripts/claudemd_state.py::build_dynamic_state зовут обе стороны. Тест паритета сверяет ПОСТРОЧНО: каждая строка блока CLI обязана быть в блоке MCP. Сверх плана консолидирован и ПОИСК файла (resolve_claudemd) — из-за этого исключение для литерала .claude переехало из project_cli_extra.py, где литерала больше нет; гейт устаревших исключений test_allowlist_has_no_stale_entries это подтвердил, он бы покраснел на оставленной записи. AC3 (AGENTS.md по пути MCP): выполнен. test_mcp_refreshes_the_agents_md_sibling плюс проверка развёрнутой копии. AC4 (тест сначала красный): ВЫПОЛНЕН И ЗАФИКСИРОВАН. Первый прогон до правки: assert '### Memory tail' in block провалился, в блоке был только Current State. Красный получен ДО написания правки, а не после. AC5 (пустая база не даёт пустого заголовка): выполнен. test_empty_memory_adds_no_empty_tail_heading. AC6 (сломанная память не роняет запись): выполнен. test_memory_failure_still_writes_current_state. ДВА ДЕФЕКТА СОБСТВЕННОЙ ПРАВКИ, НАЙДЕННЫЕ ПЕРВЫМ ПОЛНЫМ ПРОГОНОМ И ЗАКРЫТЫЕ: (1) Новый модуль внёс литерал '.claude' в scripts/ — гейт test_no_unexempted_claude_literal_in_scripts покраснел. Правильно покраснел: литерал приехал вместе с перенесённым кодом. Исключение перенесено с причиной, а не выключено. (2) Моя фикстура не закрывала бэкенд SQLite. На Windows незакрытый дескриптор не даёт pytest убрать временный каталог, и ошибка приехала под ЧУЖИМ именем — ERROR в test_memory_cleanup_cli, который в одиночку проходил. Фикстура переведена на yield с be.close(), как принято в остальном наборе. Второй полный прогон после обеих правок — зелёный.
- 2026-08-12T21:54:02Z [implementation] — AC verified: 1. ✓ хвост памяти впрыскивается по MCP — test_mcp_update_claudemd_injects_memory_tail, плюс проверка развёрнутой копии из .claude/ на временном проекте. 2. ✓ единая реализация claudemd_state.build_dynamic_state, тест паритета сверяет построчно; сверх плана сведён и поиск файла — исключение для литерала .claude переехало, гейт устаревших исключений подтвердил. 3. ✓ AGENTS.md обновляется по пути MCP — test_mcp_refreshes_the_agents_md_sibling. 4. ✓ тест получен КРАСНЫМ до правки: assert '### Memory tail' in block провалился, в блоке был только Current State. 5. ✓ пустая база не даёт пустого заголовка — test_empty_memory_adds_no_empty_tail_heading. 6. ✓ сломанная память не отменяет запись Current State — test_memory_failure_still_writes_current_state. Полный прогон: 7008 passed, 0 failed, 0 errors.
- 2026-08-12T21:54:37Z [done] — AC-1: ✓ tests/test_mcp_update_claudemd_parity.py::test_mcp_update_claudemd_injects_memory_tail AC-2: ✓ tests/test_mcp_update_claudemd_parity.py::test_mcp_and_cli_build_the_same_dynamic_block AC-3: ✓ tests/test_mcp_update_claudemd_parity.py::test_mcp_refreshes_the_agents_md_sibling AC-4: ✓ tests/test_mcp_update_claudemd_parity.py::test_mcp_update_claudemd_injects_memory_tail (прогон ДО правки — красный, зафиксирован) AC-5: ✓ tests/test_mcp_update_claudemd_parity.py::test_empty_memory_adds_no_empty_tail_heading AC-6: ✓ tests/test_mcp_update_claudemd_parity.py::test_memory_failure_still_writes_current_state Domain: результат осмыслен ВНЕ тестов и проверен вне их. Обработчик из РАЗВЁРНУТОЙ копии .claude/mcp/project (а не из scripts/) вызван на настоящем временном проекте с CLAUDE.md и AGENTS.md: оба файла получили '### Memory tail' и записанное решение. Сверх того на этом самом репозитории: до правки штатный /start дал в git diff CLAUDE.md -34/+3 с исчезнувшим хвостом, после правки CLI-обновление вернуло хвост и обновило AGENTS.md. То есть проверяется наблюдаемое поведение двери, которую читает каждый свежий агент, а не только предикат в тесте. Калибровка: call_actual=102 против call_budget=45, перерасход 2,3x. Причина названа честно, а не списана на сложность: бюджет ставился на 'починить обработчик', а работа оказалась другой — сведение двух реализаций, перенос исключения для литерала с проверкой гейта устаревших исключений, и ДВА собственных дефекта правки, найденных первым полным прогоном (литерал .claude в новом модуле и утечка дескриптора SQLite в фикстуре, приехавшая ERROR'ом под чужим именем). Плюс два полных прогона по ~18 минут каждый. Урок для тира: задача вида 'обработчик MCP разошёлся с CLI' — это не light, это moderate, потому что сведение тянет за собой чужие гейты.
