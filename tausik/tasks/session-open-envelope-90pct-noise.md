---
slug: session-open-envelope-90pct-noise
title: "session_open превышает лимит tool-result: 90% конверта — дебажная телеметрия и дубль хендоффа"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "harness/claude/mcp/project/handlers.py (_handle_session_open), tests/test_mcp_self_check.py или новый tests/test_session_open_envelope.py"
scope_exclude: "harness/claude/mcp/project/self_check.py::collect() — сама диагностика не меняется (AC2); state_triggers.py; status_view.py"
relevant_files:
  - "harness/claude/mcp/project/handlers.py"
  - "tests/test_session_open_handler.py"
  - "harness/skills/start/SKILL.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T21:09:31Z"
---

## Goal

tausik_session_open возвращает 49.2 КБ и превышает потолок tool-result хостом, из-за чего /start Phase 1 (компаундный RPC, созданный ради дешевизны) деградирует в файловый дамп и обходится ДОРОЖЕ пяти вызовов, которые он заменил. Замер конверта сессии #147: self_check.current_mtimes 13637 + self_check.watched_modules 12385 = 26022 симв. чистой телеметрии, которую дашборд НИКОГДА не рендерит (SKILL.md читает только drift_detected и stale_modules); session.handoff 15480 симв. — \u-экранированный дубль верхнеуровневой секции handoff (4720 симв. без экранирования, инфляция 3.3x на кириллице). Полезный сигнал — ~5.1 КБ из 49.2 КБ. Цель: session_open отдаёт только то, что дашборд рендерит; tausik_self_check как отдельный инструмент сохраняет полную телеметрию (это его назначение); тест закрепляет и потолок размера, и отсутствие дубля.

## Acceptance Criteria

AC1. session_open БОЛЬШЕ НЕ отдаёт self_check.watched_modules и self_check.current_mtimes: секция self_check в конверте сведена к полям, которые дашборд реально рендерит (server, pid, watched_modules_count, drift_detected, stale_modules, sibling_mcp_count, sibling_mcp_pids, sibling_introspection_error, sibling_warning, remediation). Проверка: тест на реальном возврате _handle_session_open — ключи watched_modules/current_mtimes отсутствуют, drift_detected и stale_modules присутствуют.
AC2. Отдельный инструмент tausik_self_check СОХРАНЯЕТ полную телеметрию (watched_modules + current_mtimes) — это его назначение как диагностики. Проверка: тест на _handle_self_check показывает оба ключа. Сужение применено ТОЛЬКО к конверту session_open.
AC3. session.handoff не дублирует верхнеуровневую секцию handoff: тяжёлые блобы вырезаны из session-снапшота (handoff, tasks_done), т.к. handoff уже отдаётся распарсенным отдельной секцией. Проверка: тест — session-секция не содержит ключ handoff, верхнеуровневый handoff при этом непустой и содержит те же данные.
AC4. Потолок размера закреплён тестом-регрессией: json.dumps(конверт) на реалистичном фикстуре (>=100 watched-модулей, хендофф с кириллицей >=4 КБ) укладывается в бюджет (<=8000 симв.), и тест ПАДАЕТ, если вернуть любой из вырезанных блобов. Это защита от повторной регрессии, а не косметика.
AC5. Никакой другой потребитель не сломан: grep по watched_modules/current_mtimes/session[...]handoff показывает, что ни один рендерер (status_view, SKILL.md, хуки, CLI) не читает вырезанные поля из конверта session_open. Если читает — либо не режем, либо чиним потребителя в этой же задаче.
AC6. Гейты зелёные: ruff, mypy, pytest (полный прогон), filesize, doc-drift. bootstrap.py --ide all прогнан после правки source (конвенция #321).
AC7 (SECURITY, поверхность угрозы = утечка данных хоста в контекст модели/транскрипт). Вырезаемые поля — не просто объём: watched_modules + current_mtimes публикуют 108 АБСОЛЮТНЫХ путей файловой системы разработчика ([вычеркнуто: local-path]<заказчик>\... — имя заказчика в пути) плюс mtime-отпечаток рабочей машины, а sibling_mcp_pids/pid — PID'ы живых процессов. /start вызывается КАЖДУЮ сессию, т.е. это регулярная выгрузка в транскрипт LLM-провайдера. Требование: (а) после правки конверт session_open не содержит НИ ОДНОГО абсолютного пути — тест проверяет отсутствие разделителей путей/префикса cwd в сериализованном конверте, кроме явно допущенных stale_modules (они и есть actionable-сигнал и появляются только при drift); (б) stale_modules при drift отдаются как basename, а не абсолютный путь — для ремедиации «перезапусти IDE» полного пути не требуется; (в) в задаче зафиксировано решением, что полная телеметрия остаётся доступной по ЯВНОМУ вызову tausik_self_check (opt-in диагностика), а не в автоматическом /start (implicit), — принцип минимизации по умолчанию.

## Plan

## Rollback

git revert коммита. Изменение чисто аддитивно-вычитающее в одной функции-сборщике конверта (_handle_session_open): вернуть передачу self_check_data/session_data целиком. Данные не мигрируют, схема БД не трогается, откат безрискован.

## Journal

- 2026-07-27T20:53:59Z [implementation] — [implementation] Замер до правки (конверт сессии #147, 49 165 симв.): self_check.current_mtimes 13637 + self_check.watched_modules 12385 = 26022 симв. телеметрии, которую дашборд не читает; session.handoff 15480 симв. — \u-экранированный дубль верхнеуровневого handoff (4720 без экранирования, инфляция 3.3x на кириллице); полезный сигнал status 273 + handoff 4720 + tasks 29 + self_check-сигнал ~110 + sync 4 ≈ 5.1 КБ. Т.е. 90% — шум. AC5 проверен ДО правки: grep watched_modules|current_mtimes по репо (без .claude) даёт только self_check.py (производитель) и tests/test_mcp_self_check.py:63 — а это тест ОТДЕЛЬНОГО инструмента tausik_self_check, который по AC2 остаётся полным. Ни один потребитель конверта session_open вырезаемые поля не читает. Реализация: _handle_session_open проецирует обе полноточные секции через ALLOWLIST (_SESSION_ENVELOPE_KEYS, _SELF_CHECK_ENVELOPE_KEYS, _STALE_MODULE_KEYS) — не denylist, чтобы новое тяжёлое поле у производителя не раздуло конверт молча. Error-секции проходят насквозь (иначе аллоулист стёр бы диагностику, ради которой существует деградированный дашборд). stale_modules чистится от абсолютного path, basename в module достаточно для ремедиации «перезапусти IDE».
- 2026-07-27T21:09:28Z [implementation] — AC1 ✓ Секция self_check в конверте сведена аллоулистом _SELF_CHECK_ENVELOPE_KEYS: watched_modules и current_mtimes отсутствуют, drift_detected/stale_modules/watched_modules_count на месте. tests/test_session_open_handler.py::TestEnvelopeProjection::test_self_check_section_drops_module_telemetry. AC2 ✓ tausik_self_check (отдельный инструмент) сохраняет ОБА ключа — сужение применено только к конверту session_open. test_self_check_tool_keeps_full_telemetry. AC3 ✓ session-секция не содержит handoff и tasks_done; верхнеуровневый handoff непуст и несёт те же данные (проверено по кириллической подстроке). test_session_section_drops_handoff_duplicate + test_session_section_is_allowlisted. AC4 ✓ Потолок 8000 симв. на реалистичном фикстуре (120 наблюдаемых модулей + кириллический хендофф) — test_envelope_stays_under_budget. Страховка НЕ вхолостую: test_budget_guard_has_teeth отдельно доказывает, что каждый вырезанный блоб в одиночку превышает бюджет (watched_modules, current_mtimes, \u-экранированный дубль хендоффа). Замер эффекта на одной и той же нагрузке: 36989 -> 3017 симв., -91.8%. AC5 ✓ Проверено ДО правки: grep watched_modules|current_mtimes по репо (без .claude) даёт только self_check.py (производитель) и tests/test_mcp_self_check.py:63 — тест ОТДЕЛЬНОГО инструмента, сохранённого по AC2. Ни один потребитель конверта вырезанные поля не читает; ломать нечего. Дополнительно: error-секции проходят проекцию насквозь (test_error_sections_pass_through_unprojected), иначе аллоулист стёр бы диагностику деградированного дашборда. AC6 ✓ ruff All checks passed (весь репозиторий); mypy Success 291 файл; pytest ПОЛНЫЙ прогон 6396 passed / 24 skipped / 0 failed / 0 errors (655s) + после doc-правок прогон 92 doc-drift/bootstrap-drift/session-open/self-check тестов зелёный; filesize без превышений; bootstrap.py --ide all прогнан дважды (после правки кода и после правки SKILL.md) — конвенция #321. CHANGELOG.md + CHANGELOG.ru.md, docs/{en,ru}/mcp.md, harness/skills/start/SKILL.md обновлены. AC7 ✓ SECURITY. (а) test_envelope_leaks_no_absolute_host_paths: в сериализованном конверте нет ни os.getcwd(), ни префикса [вычеркнуто: local-path]. (б) stale_modules при drift несут module (basename) + reason + delta_seconds, ключ path вырезан, при этом drift_detected=true доходит до /start — сигнал не заглушён (test_stale_modules_named_by_basename_not_path). (в) Полная телеметрия остаётся по ЯВНОМУ tausik_self_check (opt-in), а не в автоматическом /start — принцип минимизации по умолчанию зафиксирован в докстринге проекции, CHANGELOG EN+RU и SKILL.md. Verify: run #1540 (scoped pytest 17 файлов, PASS, подпись 103a83a212851018). Первый прогон #1539 БРАКОВАН и пересдан: без объявленного relevant_files pytest был SKIP, т.е. расписка не удостоверяла ничего.
- 2026-07-27T21:10:00Z [done] — Domain: результат осмыслен ВНЕ тестов — конверт снят с реальной сессии #147 (49165 симв., отказ хоста с превышением потолка tool-result и деградацией в файловый дамп), а не сконструирован под тест. После правки на той же нагрузке 36989 -> 3017 симв. (-91.8%), и все шесть сигналов, которые /start Phase 3 реально рендерит (session id/started_at, status, handoff, tasks, drift_detected+stale_modules, sync_suggested), остались на месте — проверено по спецификации рендера в SKILL.md, а не по набору ключей. То есть дашборд физически строится из того же множества фактов при 1/12 объёма. Negative: негативные сценарии AC исполнены отдельными тестами, а не подразумеваются. (1) test_budget_guard_has_teeth — потолок 8000 симв. ПАДАЕТ, если вернуть любой из трёх вырезанных блобов: каждый в одиночку превышает бюджет; без этого теста ассерт размера мог бы проходить вхолостую. (2) test_error_sections_pass_through_unprojected — секция со сбоем {error: ...} проходит проекцию НЕТРОНУТОЙ; наивный аллоулист стёр бы её и убил деградированный дашборд, ради которого watchdog и вводился. (3) test_stale_modules_named_by_basename_not_path на drift_detected=true — при РЕАЛЬНОМ дрейфе сигнал доходит до /start (не заглушён сужением), path вырезан, module остаётся. (4) Процессный негатив: verify #1539 забракован самим автором — без relevant_files pytest был SKIP, расписка не удостоверяла ничего; пересдан как #1540 со scoped pytest PASS.
