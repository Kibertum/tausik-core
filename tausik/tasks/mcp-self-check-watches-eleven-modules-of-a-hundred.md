---
slug: mcp-self-check-watches-eleven-modules-of-a-hundred
title: "tausik_self_check следит за жёстким списком из 11 модулей и отвечает «in sync», когда устарел любой из остальных"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "harness/claude/mcp/project/self_check.py (watched-set derivation from sys.modules + lazy detection + eager-list rename), tests/test_mcp_self_check.py (reproduction + edge tests)"
scope_exclude: "_enumerate_sibling_mcps (sibling logic не трогать), collect() JSON-контракт (ключи стабильны), scripts/ модули не менять"
relevant_files:
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_mcp_self_check.py"
scope_paths:
  - "harness/claude/mcp/project/self_check.py"
  - "tests/test_mcp_self_check.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:16:22Z"
---

## Goal

Найдено эмпирически в сессии #135, а не чтением кода. Закрытие задачи verify-warn-names-a-flag-verify-does-not-have через MCP напечатало COMPLEXITY UNDERSTATED в СТАРОЙ формулировке — той, что была до правки, закрытой часом раньше в этой же сессии. Проверка на живом источнике: те же 12 путей дают understatement('medium', ...) -> None, предупреждения быть не должно. Файл .claude/scripts/complexity_understatement.py побайтово совпадает с scripts/. Устарел не файл, а ПРОЦЕСС: MCP поднялся в 14:37 и держит в памяти модуль, импортированный до правки.

При этом tausik_self_check в том же сеансе отвечал: drift_detected=false, «MCP modules in sync; no action needed».

МЕХАНИЗМ (.claude/mcp/project/self_check.py:39). _WATCHED_MODULES — жёстко перечисленный кортеж из одиннадцати имён: service_verification, verify_cache, security_pattern, gate_runner, gate_command_runner, service_gates, service_task, project_service, project_backend, handlers, handlers_skill. Сервер импортирует ДЕСЯТКИ модулей: service_task_done, complexity_understatement, task_done_scope, verify_cached_run, gate_test_resolver, ac_evidence_detectors, gate_ac_check и так далее. Любой из них может устареть, и проверка этого не увидит по построению.

ПОЧЕМУ ЭТО ДОРОГО. Ответ «in sync» читается агентом как «результатам MCP можно доверять» — так он и написан в /start SKILL.md, где drift_detected=false означает «не нужно откатываться на CLI». Сегодняшняя цена измерима: в журнал надзора записано ЛОЖНОЕ событие complexity_understated, то есть загрязнена ровно та метрика калибровки, которую сессия чинила часом раньше. Класс тот же, что закрывают задачи батча 1.8: проверка отвечает на более узкий вопрос, чем тот, который читает потребитель. Ср. память #289 (спрашивай набор объектов у ПРОИЗВОДИТЕЛЯ, а не перечисляй его) и #305 (знаменатель рядом с вердиктом).

НАПРАВЛЕНИЕ РЕШЕНИЯ, не приказ. Снимать mtime не по списку, а по sys.modules: все загруженные модули, чей __file__ лежит под развёрнутым scripts/ или mcp/. Тогда множество спрашивается у производителя. Отдельно обдумать модули, импортированные ЛЕНИВО уже ПОСЛЕ старта: их нет в стартовом снимке, поэтому дрейф по ним не виден никогда — вероятно, mtime позже времени старта сервера сам по себе является дрейфом. Проверить стоимость: обход sys.modules на каждый self_check и на старте.

ОБЯЗАТЕЛЬНО в проверке: воспроизвести сегодняшний случай — модуль ВНЕ старого списка правится после старта, self_check обязан сказать drift. И негативный сценарий: правка файла, который сервер не импортировал вовсе, дрейфом быть не должна.

## Acceptance Criteria

1. Множество наблюдаемых модулей спрашивается у ПРОИЗВОДИТЕЛЯ, а не перечисляется руками: снимок mtime берётся по sys.modules — все загруженные модули, чей __file__ лежит под развёрнутым деревом сервера (scripts/ и mcp/). Жёсткий список _WATCHED_MODULES перестаёт быть определением множества (может остаться списком для ЖАДНОГО импорта критичных модулей на старте — это другая ответственность, и она должна быть названа в коде).
2. ВОСПРОИЗВЕДЁН СЕГОДНЯШНИЙ СЛУЧАЙ: тест правит модуль, которого НЕТ в старом списке одиннадцати (например complexity_understatement или service_task_done), и self_check обязан сообщить drift_detected=true и назвать этот модуль в stale_modules. Тот же тест на старой реализации обязан давать ОТКАЗ обнаружить дрейф — то есть доказывать, что дыра БЫЛА.
3. Модули, импортированные ЛЕНИВО после старта сервера, не создают слепого пятна: их нет в стартовом снимке, поэтому решено явно, как их трактовать, и решение закреплено тестом (mtime позже времени старта сервера — дрейф).
4. Замерена стоимость: приведено время работы self_check до и после на реальном наборе загруженных модулей. Если обход sys.modules дороже 100 мс — приведены цифры и объяснено, почему это приемлемо или что сделано взамен.
5. ГРАНИЧНЫЕ И ОШИБОЧНЫЕ ВХОДЫ, каждый — тест: правка файла, который сервер не импортировал, дрейфом НЕ МОЖЕТ считаться; модуль с ОТСУТСТВУЮЩИМ __file__ (встроенный, namespace-пакет) даёт пустой результат, а не исключение; УДАЛЁННЫЙ после старта файл модуля даёт OSError внутри, который проверка обязана проглотить явно, а не уронить сервер; модули стандартной библиотеки и site-packages в наблюдение попадать НЕ ДОЛЖНЫ, иначе первое же обновление pip объявит ложный дрейф; любая ошибка внутри проверки не должна ронять MCP-сервер — тест подменяет os.path.getmtime на бросающий и требует, чтобы вызов вернул отчёт, а не исключение.
6. Правка внесена в ИСТОЧНИК harness/claude/mcp/project/self_check.py и развёрнута во все профили (.claude, .cursor, .kilo, .opencode, .qwen) через bootstrap --ide all; гейт bootstrap_drift зелёный.

## Plan

## Rollback

git revert коммита; изменение локализовано в self_check.py — снапшот-логика; откат возвращает 11-модульный список. Ключи JSON-отчёта сохранены, потребители не ломаются.

## Journal

- 2026-07-26T22:16:20Z [implementation] — AC-1: ✓ Набор наблюдаемых модулей у ПРОИЗВОДИТЕЛЯ — _loaded_our_module_paths() фильтрует sys.modules по _server_roots (scripts+mcp профиля). tests/test_mcp_self_check.py::test_watch_set_comes_from_producer_not_hand_list. _EAGER_IMPORT_MODULES остался ТОЛЬКО для жадного импорта (названо в докстринге). AC-2: ✓ Воспроизведён случай #135 — tests/test_mcp_self_check.py::test_reproduces_todays_case_module_outside_old_eleven (complexity_understatement вне 11, правка после старта → drift, назван в stale_modules). Дыра доказана: test_old_list_would_have_missed_it (future-dated правка при пустом старом наборе → drift==[]). AC-3: ✓ Ленивые модули после старта — test_lazy_loaded_after_startup_is_drift (mtime>boot → reason lazy-loaded-after-edit) + негатив test_lazy_loaded_before_boot_is_not_drift. AC-4: ✓ Стоимость измерена: test_self_check_module_walk_cost_under_budget печатает 6.17 ms/call на 936 sys.modules (<100ms бюджет). AC-5: ✓ Граничные/ошибочные, каждый тест: stdlib/site-packages не наблюдаются (test_stdlib_and_site_packages_not_watched), не-импортированный файл не дрейф (test_file_not_imported_by_server_is_not_drift), нет __file__ → skip не crash (test_module_without_file_is_skipped_not_crash), удалённый файл OSError проглочен (test_deleted_file_getmtime_error_swallowed), любой Exception в getmtime не роняет collect() (test_any_getmtime_exception_does_not_crash_collect). AC-6: ✓ Правка в источнике harness/claude/mcp/project/self_check.py, развёрнута bootstrap --ide all во все профили (.claude подтверждён grep: _EAGER_IMPORT/lazy маркеры есть, _WATCHED_MODULES=0), gate bootstrap_drift зелёный. Verify run #1448 scoped pytest 20 passed. mypy: harness/claude/mcp/project/self_check.py Success (+ project-wide 280 files Success). CHANGELOG EN+RU обновлены. Domain: детектор теперь отвечает на тот же вопрос, что читает потребитель (/start доверяет drift_detected) — набор берётся у производителя, класс #289/#305.
