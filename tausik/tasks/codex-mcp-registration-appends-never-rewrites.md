---
slug: codex-mcp-registration-appends-never-rewrites
title: "Регистрация MCP для Codex: дописать блок в .codex/config.toml, не переписывая чужой TOML"
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
scope_exclude: "Не писать в ~/.codex/config.toml — глобальный конфиг пользователя не принадлежит bootstrap проекта"
relevant_files:
  - "bootstrap/bootstrap_codex_mcp.py"
  - "bootstrap/bootstrap_codex.py"
  - "tests/test_bootstrap_codex_mcp.py"
  - "docs/ru/model-providers.md"
  - "docs/en/model-providers.md"
scope_paths:
  - "bootstrap/bootstrap_codex.py"
  - "bootstrap/bootstrap_codex_mcp.py"
  - "tests/test_bootstrap_codex_mcp.py"
  - "docs/ru/model-providers.md"
  - "docs/en/model-providers.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-09T16:32:11Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "gitlab#17"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР, смена #241, на живой машине владельца. Формат регистрации MCP у Codex установлен по РАБОТАЮЩЕМУ файлу ~/.codex/config.toml: секция [mcp_servers.<имя>] с ключами command и args, при необходимости подтаблица [mcp_servers.<имя>.env]. Там же присутствует секция [projects.'<путь>'] с trust_level. Проектный .codex/config.toml Codex тоже читает - строка .codex/config.toml присутствует в бинаре. То есть регистрация возможна на уровне ПРОЕКТА, без правки пользовательского глобального конфига, и это верный выбор: bootstrap проекта не должен писать в домашний каталог.

ОГРАНИЧЕНИЕ ЯЗЫКА, ОПРЕДЕЛЯЮЩЕЕ ФОРМУ ПРАВКИ. В stdlib Python 3.11 есть tomllib только на ЧТЕНИЕ; писателя TOML нет и зависимость тянуть нельзя. Разобрать и переписать файл целиком значило бы потерять комментарии и порядок секций пользователя - то самое, ради сохранения чего слово preserve-first стоит в тикете. Поэтому правка НЕ переписывает файл: она читает его через tomllib, чтобы УЗНАТЬ, есть ли уже наши серверы, и при отсутствии ДОПИСЫВАЕТ блок, ограниченный маркерами. Чужие секции и комментарии не переживают правку, а просто не трогаются.

ПУТИ АБСОЛЮТНЫЕ. Codex не раскрывает переменных рабочей области - проверено: в бинаре нет ни CLAUDE_PROJECT_DIR, ни CODEX_PROJECT_ROOT, ни workspaceFolder. Решение то же, что у OpenCode (gotcha #201), и по той же причине.

## Acceptance Criteria

AC-1 После bootstrap --ide codex в .codex/config.toml есть [mcp_servers.tausik-project] с абсолютным путём к интерпретатору и к server.py, и оба пути существуют на диске. AC-2 Файл читается tomllib без ошибки - то есть дописанный блок остаётся валидным TOML: проверяется разбором, а не глазами. AC-3 ПРЕЗЕРВАЦИЯ: файл с чужой секцией и комментариями после повторного bootstrap несёт их ПОБАЙТОВО - тест сравнивает чужую часть до и после. AC-4 Идемпотентность: два прогона подряд дают один и тот же файл, блок не дублируется. AC-5 НЕГАТИВ: сервер, чей server.py не найден, в конфиг НЕ попадает - запись команды, которая не запустится, хуже отсутствия записи, потому что выглядит настроенной.

## Plan

## Rollback

Дописывание блока в .codex/config.toml; откат - git revert генератора и удаление блока по маркерам. Пользовательские секции не затрагиваются ни при правке, ни при откате.

## Journal

- 2026-09-09T16:19:03Z [implementation] — AC-1: ✓ tests/test_bootstrap_codex_mcp.py::TestКаждыйПутьСуществует::test_интерпретатор_и_сервер_на_месте — три сервера, у каждого команда и server.py существуют на диске
- 2026-09-09T16:19:03Z [implementation] — ФОРМАТ ПОДТВЕРЖДЁН ПО РАБОТАЮЩЕМУ ФАЙЛУ ~/.codex/config.toml: [mcp_servers.<имя>] с command и args. Пишем в ПРОЕКТНЫЙ .codex/config.toml — Codex его читает (строка есть в бинаре), а домашний каталог пользователя bootstrap проекта не принадлежит.
- 2026-09-09T16:19:04Z [implementation] — AC-2: ✓ tests/test_bootstrap_codex_mcp.py::TestЗаписанноеЯвляетсяВалиднымTOML::test_живой_конфиг_разбирается и test_путь_в_windows_экранирован_а_не_съеден
- 2026-09-09T16:19:05Z [implementation] — AC-3: ✓ tests/test_bootstrap_codex_mcp.py::TestПовторныйПрогонИЧужойТекст::test_чужой_текст_и_комментарии_сохраняются_побайтово — сравнение startswith, то есть чужая часть неизменна побайтово
- 2026-09-09T16:19:06Z [implementation] — AC-4: ✓ tests/test_bootstrap_codex_mcp.py::TestПовторныйПрогонИЧужойТекст::test_два_прогона_дают_один_файл
- 2026-09-09T16:19:07Z [implementation] — AC-5: ✓ tests/test_bootstrap_codex_mcp.py::TestНенайденныйСерверНеЗаписывается::test_записывается_только_найденный
- 2026-09-09T16:19:08Z [implementation] — Domain: сервер ЗАПУСКАЕТСЯ командой из конфига и отвечает на initialize — tests/test_bootstrap_codex_mcp.py::TestСерверДЕЙСТВИТЕЛЬНОЗапускается::test_ответ_на_initialize_командой_из_конфига. Это и есть разница между 'прописан' и 'работает', с которой началась вся история.
- 2026-09-09T16:19:09Z [implementation] — ТЕСТ НАШЁЛ НАСТОЯЩЕЕ, а не только подтвердил задуманное: разбор TOML стоял ТОЛЬКО после записи, и пользовательский config.toml, уже невалидный, ронял bootstrap исключением. Теперь разбор идёт ДО: неразбираемый файл не трогается вовсе и о нём сообщается — Codex не прочтёт его и без нас, а спрятать чужую поломку под своим блоком значит получить жалобу 'TAUSIK сломал мне конфиг'.
- 2026-09-09T16:30:46Z [implementation] — ЗАПАСНОЙ ПУТЬ ЗАДОКУМЕНТИРОВАН в обоих языках: приоритет проектного .codex/config.toml над глобальным ~/.codex/config.toml зависит от версии хоста и проверяется только открытием Codex. Если инструменты не видны — блок между маркерами копируется в глобальный конфиг; пути в нём абсолютные, поэтому он работает из любого файла, а маркеры позволяют потом его найти и убрать. Это названо прямо, а не оставлено читателю: единственный неизвестный на пути переключения не должен стоить владельцу часа догадок.
