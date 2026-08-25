---
slug: ruff-gate-rests-on-the-linters-default-not-the-projects-choice
title: "Гейт ruff держится на УМОЛЧАНИИ линтера, а не на выборе проекта — и умолчание сменилось"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: backend
stack: null
tier: light
call_budget: 18
defect_of: null
scope: null
scope_exclude: "tests/**, docs/**, .gitlab-ci.yml, .github/** — пин версии в CI НЕ делаем"
relevant_files:
  - pyproject.toml
  - "scripts/verify_handle.py"
scope_paths:
  - pyproject.toml
  - "scripts/verify_handle.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-04T07:38:00Z"
---

## Goal

Вердикт lint определяется КОНФИГОМ репозитория, а не версией ruff, установленной в момент прогона; и единственная настоящая находка (неиспользуемый import hmac) устранена.

## Acceptance Criteria

1. pyproject.toml называет набор правил ЯВНО (select = E4, E7, E9, F, BLE001) вместо extend-select, опиравшегося на умолчание ruff; проверяется чтением файла.
2. `ruff check scripts/ tests/ bootstrap/` даёт 0 находок и на ruff 0.15.12 (локальная), и на ruff 0.16.1 (та, что ставит CI) — измерено обоими бинарями, а не выведено из конфига.
3. Неиспользуемый `import hmac` удалён из scripts/verify_handle.py; hmac не переэкспортируется — ни один модуль его оттуда не импортирует.
4. НЕГАТИВНЫЙ сценарий: до правки ruff 0.16.1 даёт 1539 находок, из них 1537 — правила, которых проект НЕ выбирал (EXE001, I001, SIM115, PLW1510, RUF100) плюс 137 E501; после правки эти правила не срабатывают вовсе. Расхождение между версиями линтера БОЛЬШЕ НЕ МЕНЯЕТ вердикт.
5. НЕГАТИВНЫЙ сценарий: если после правки хоть одна версия ruff даёт ненулевой выход, коммит НЕ делается и тег НЕ ставится.

## Plan

## Rollback

git revert коммита: вернуть extend-select и импорт hmac

## Journal

- 2026-08-04T07:35:39Z [implementation] — Корень найден измерением, а не чтением конфига. CI ставит ruff БЕЗ пина (`pip install --quiet pytest PyYAML ruff`), 2026-08-04 вышла 0.16.1 и сменила НАБОР ПРАВИЛ ПО УМОЛЧАНИЮ. Пайплайн #4225 на main упал с 1572 находками при неизменном репозитории. Измерено тремя прогонами на одном и том же дереве: - ruff 0.15.12 (локальная, конфиг ДО правки): 1 находка — F401 `hmac` в scripts/verify_handle.py - ruff 0.16.1 (конфиг ДО правки): 1539 находок; коды, которых проект не выбирал: EXE001, I001, SIM115, PLW1510, RUF100 - ruff 0.16.1 с --select E,F,BLE001: 138 находок, из них 137 — E501, который в умолчании ruff никогда не был (умолчание — E4,E7,E9,F, а не всё E) Отсюда правка: набор правил назван ЯВНО select = [E4, E7, E9, F, BLE001]. Это ровно то, что гейт enforce'ил все эти месяцы, просто теперь это сказано в конфиге, а не унаследовано от вкуса вендора. Пин версии в CI отвергнут как лечение симптома: он оставил бы вердикт зависящим от того, что установилось, и следующая смена умолчания снова прилетела бы в релизный день. Разница 1572 (CI) против 1539 (локально) объясняется EXE001 — shebang при неисполняемом бите, на Windows не срабатывает. `import hmac` — настоящая находка, не шум: nonce сравнивается в SQL (WHERE handle_nonce = ?), в Python сравнения нет, hmac никем из verify_handle не импортируется. Удалён. После правки: 0 находок на ОБЕИХ версиях, проверено запуском обеих.
- 2026-08-04T07:36:59Z [implementation] — Чек-лист доказательств. AC-1 (набор правил назван явно): ✓ tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject ✓ MANUAL: pyproject.toml строка select = ["E4", "E7", "E9", "F", "BLE001"] — extend-select удалён AC-2 (ноль находок на обеих версиях ruff): ✓ MANUAL: .tausik/venv ruff 0.15.12 — `ruff check scripts/ tests/ bootstrap/` -> All checks passed! EXIT=0 ✓ MANUAL: ruff 0.16.1 в отдельном venv (та версия, что ставит CI) -> All checks passed! EXIT=0 AC-3 (неиспользуемый импорт удалён): ✓ tests/test_verify_handle.py ✓ tests/test_verify_handle_integration.py ✓ MANUAL: grep hmac по scripts/ и tests/ — ни одного вхождения из verify_handle; nonce сравнивается в SQL AC-4 (негативный: расхождение версий больше не меняет вердикт): ✓ MANUAL: ДО правки 0.16.1 давала 1539 находок (EXE001, I001, SIM115, PLW1510, RUF100 + 137 E501), 0.15.12 — одну; ПОСЛЕ правки обе дают ноль. Правила, которых проект не выбирал, не срабатывают вовсе. AC-5 (негативный: красный линт останавливает коммит и тег): ✓ MANUAL: именно это и произошло — пайплайн #4225 упал, тег НЕ поставлен, работа ушла в эту задачу. Критерий исполнен ходом событий, а не рассуждением о нём. Дополнительно прогнаны тесты, читающие конфиг ruff: test_ble001_enforced, test_no_silent_subprocess, test_aidd_validate, test_v13_hardening — 58 passed.
