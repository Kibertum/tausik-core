---
slug: release-v1-7-0-opencode
title: "Релиз v1.7.0: поддержка OpenCode + честность доки + тишина MCP"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/tausik_version.py, CHANGELOG.md, CHANGELOG.ru.md, зеркала через bootstrap"
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/tausik_version.py"
  - pyproject.toml
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-16T20:50:31Z"
---

## Goal

Выпустить накопленное: поддержка OpenCode (новая IDE = minor bump 1.6.1 → 1.7.0), правдивая таблица платформ с гардом, ответ MCP-серверов на prompts/list вместо -32601. Делать ПОСЛЕ opencode-ide-support.

## Acceptance Criteria

1. scripts/tausik_version.py: 1.6.1 → 1.7.0 (новая IDE = feature = minor). 2. ОБЯЗАТЕЛЬНО СРАЗУ ПОСЛЕ БАМПА: python bootstrap/bootstrap.py --ide all --no-detect. Урок сессии #106: без этого зеркала (.claude/, .cursor/, .qwen/, .kilo/, .opencode/) остаются со СТАРОЙ версией, и аудит ловит дрейф. Этот же прогон разложит новые MCP-серверы (list_prompts) и конфиг OpenCode. 3. CHANGELOG.md + CHANGELOG.ru.md: записи про OpenCode (генератор конфига, QG-0-плагин, doctor-проверки), гард доки, MCP prompts/list. 4. НЕГАТИВНЫЕ СЦЕНАРИИ (обязательны, каждый — команда с выводом): (а) ОШИБКА, если после бампа и bootstrap grep по зеркалам всё ещё находит строку 1.6.1 — это означает воспроизведённый дрейф версии, релиз в таком виде не выпускается; (б) ОШИБКА, если tausik doctor не чист; (в) ОШИБКА, если полный pytest красный; (г) ОШИБКА, если версия в CHANGELOG не совпадает с tausik_version.py — рассинхрон доки и кода есть тот же класс лжи, что мы чинили весь релиз. 5. Перезапустить IDE, чтобы MCP-сервер поднялся на 1.7.0 и подтвердить, что -32601 в логе больше нет — это ЕДИНСТВЕННАЯ фактическая проверка тишины в логе (в тестах она недостижима: harness/-исходник не запускается напрямую). Если перезапуск в этой сессии невозможен — честно записать это как непроверенное, НЕ выдавая за проверенное. 6. Gates зелёные + push по правилам (tausik push-ok, спросить пользователя перед push).

## Plan

## Rollback

Откат тега + revert коммита бампа; зеркала восстанавливаются повторным bootstrap с прежней версией.

## Journal

- 2026-07-14T14:19:39Z [implementation] — РЕЛИЗ ГОТОВ, НО НЕ ЗАКОММИЧЕН — пользователь решил пока не коммитить (спрошено явно, ответ «Пока ничего не коммитить»). Задача остаётся active до его команды. СДЕЛАНО: (1) scripts/tausik_version.py 1.6.1 → 1.7.0. ВТОРОЙ САЙТ ВЕРСИИ, который я чуть не пропустил: pyproject.toml тоже держал 1.6.1 — поймал гард tests/test_check_docs_hook (проверка «__version__ vs pyproject»), не я. (2) CHANGELOG.md + CHANGELOG.ru.md: записи 1.7.0 (OpenCode, QG-0-плагин, doctor-проверки, гард таблицы платформ, prompts/list, traversal в rules_path, фейковый npm-пакет). (3) bootstrap --ide all --no-detect прогнан ДВАЖДЫ: первый раз до gen_doc_constants, из-за чего зеркала унесли старые константы с 1.6.1 — ровно тот дрейф, что запрещает негативный сценарий (а). Порядок правильный: бамп → gen_doc_constants --write → bootstrap --ide all. НЕГАТИВНЫЕ СЦЕНАРИИ ПРОВЕРЕНЫ: (а) grep 1.6.1 по всему дереву вне CHANGELOG/research — пусто; все пять зеркал (.claude/.cursor/.qwen/.kilo/.opencode) на 1.7.0. (б) doctor — All clean. (в) полный pytest — 4533 passed, 20 skipped, 0 failed. (г) CHANGELOG и tausik_version.py совпадают (проверено скриптом). ОСТАЁТСЯ: AC5 (перезапуск IDE + подтверждение, что -32601 ушёл из лога) — НЕ ПРОВЕРЕНО, в этой сессии перезапуск невозможен; фиксирую честно как непроверенное, не выдавая за проверенное. AC6 — push после команды пользователя (push-ok выдавал тикет, TTL 60с, при коммите выдать заново). ЗАМЕЧАНИЕ: `tausik claudemd` печатает warning «DYNAMIC:START marker not found in AGENTS.md — skipped». Это НЕ баг: AGENTS.md в нашем репозитории написан руками (tracked, публичный онбординг), маркеров динамического блока в нём нет, и TAUSIK честно сообщает, что не стал его трогать. В сгенерированных проектах AGENTS.md содержит маркеры. Глушить нечего. ЛОВУШКА ДЛЯ СЛЕДУЮЩЕГО: MCP-сервер держит модуль версии в памяти с момента старта, поэтому tausik_update_claudemd через MCP писал 1.6.1 уже ПОСЛЕ бампа. Обновлять CLAUDE.md после бампа версии — только через CLI (`.tausik/tausik claudemd`), свежий процесс читает с диска.
- 2026-07-16T20:50:30Z [implementation] — AC verified. РЕЛИЗ ВЫЛОЖЕН. Обе полосы зелёные на ТИХОМ дереве (FULL 4716 / FAST 4583), doctor All clean, integrity 20/20. 1. ✓ scripts/tausik_version.py 1.6.1 → 1.7.0 И pyproject.toml (второй сайт версии). 2. ✓ bootstrap --ide all --no-detect прогнан; зеркала (.claude/.cursor/.qwen/.kilo/.opencode) на 1.7.0. 3. ✓ CHANGELOG.md + CHANGELOG.ru.md: секция [1.7.0] — 2026-07-16, EN/RU симметричны (4 секции, 15 пунктов), caveman свёрнут из [Unreleased], блок «What is verified, and what is not». 4. ✓ НЕГАТИВНЫЕ: (а) grep 1.6.1 по дереву вне CHANGELOG — пусто; (б) doctor чист; (в) полный pytest зелёный; (г) CHANGELOG == tausik_version.py. 5. ✗→✓ ЧЕСТНО: AC5 (перезапуск IDE + подтверждение ухода -32601 из лога) НЕ выполнен — по решению пользователя живая валидация OpenCode передана тестировщикам. Это НЕ выдано за проверенное: записано отдельным блоком в CHANGELOG обеих версий и в release notes на GitHub. 6. ✓ PUSH ПО ПРАВИЛАМ ПАМЯТИ (пользователь дал команду «коммит пуш всего + релиз в гитхаб»): - Память прочитана ПЕРЕД действием, как велено. Найдено расхождение: задача v156-github-release (20.06) использовала force-push orphan, а решение #124 (06.07) новее и предписывает fast-forward child от существующего scrubbed-root. Выбрано #124 как актуальное — не стал повторять устаревшую процедуру. - Leak-аудит ПЕРЕД push (блокер AC6 прошлых релизов): 0 совпадений по [вычеркнуто: internal-host]/glpat-/oauth2:/ghp_/sk-*/PRIVATE KEY; docs/audit отсутствует; docs/research/_internal gitignored; .pem/.key/.env не трекаются. - Стейджинг по allowlist путей, НЕ `git add -A` (решение #125): ровно 78 файлов, мусора (pyc/venv/db) ноль, ничего не забыто. - GitLab (origin, полная история): commit f34d9d6, push cdde825..f34d9d6, тег v1.7.0 → f34d9d67. Тикет push-ok минтился ОТДЕЛЬНЫМ вызовом перед каждым push (dead-end #191 запрещает цепочку в одном bash-вызове). - Completeness-check зеркала ПЕРЕД публикацией: mirror 828 файлов, HEAD 823. «Потеряно» 19 = ровно harness/cursor/mcp (намеренное удаление этого релиза). Добавлено 14 = мои модули opencode/caveman + плагин + тесты. 828−19+14=823 ✓ — тихих потерь нет, лишнего не публикуется. - GitHub (публичное зеркало): child-коммит 61005bc собран plumbing'ом (tree = HEAD tree, parent = github/main e036321) → fast-forward, force НЕ нужен (firewall его и блокирует). Push `61005bc:refs/heads/main 61005bc:refs/tags/v1.7.0` — принят, e036321..61005bc. - Дуальная схема тегов (решение #125) соблюдена: gitlab v1.7.0=f34d9d67, github v1.7.0=61005bc, ДЕРЕВЬЯ ИДЕНТИЧНЫ (2a3dac87) — downstream может чекаутить тег на обоих ремоутах. - gh release create v1.7.0 → https://github.com/Kibertum/tausik-core/releases/tag/v1.7.0 (Latest, не draft/prerelease), notes = секция CHANGELOG [1.7.0]. - ORPHAN-АУДИТ СВЕЖИМ КЛОНОМ (правило памяти #175): clone --branch v1.7.0 публичного репо → version 1.7.0 ✓, opencode в SCAFFOLD_IDES ✓, QG-0-плагин на месте ✓, cursor-зеркало отсутствует ✓, resolve_output_mode(full_cfg) ✓, opencode получает output_mode ✓; утечки: [вычеркнуто: internal-host] 0, glpat- 0, ghp_ 0, docs/audit нет, _internal нет. Зеркало = 7 коммитов от parentless scrubbed-root f380a2e, dev-история не экспонирована. Domain: публичный тег отдаёт свежему клону ровно тот код, который заявлен в release notes — проверено клоном, а не доверием к коду возврата gh.
