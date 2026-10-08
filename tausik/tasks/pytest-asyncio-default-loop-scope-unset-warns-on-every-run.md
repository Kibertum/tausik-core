---
slug: pytest-asyncio-default-loop-scope-unset-warns-on-every-run
title: "pytest-asyncio предупреждает на КАЖДОМ прогоне: asyncio_default_fixture_loop_scope не задан"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "pyproject.toml (две строки текста: комментарий к addopts и описание маркера slow), scripts/gate_command_runner.py (комментарий у _FULL_LANE_REMEDY), tests/test_gate_outcome.py (комментарий в тесте про отказ), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files:
  - pyproject.toml
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_outcome.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-30T18:35:24Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР (сессия #183): всякий запуск pytest печатает PytestDeprecationWarning от pytest_asyncio/plugin.py:247 — «The configuration option "asyncio_default_fixture_loop_scope" is unset». Установлен pytest-asyncio 1.3.0, асинхронные тесты в дереве ЕСТЬ (tests/test_gate_test_citation.py), то есть плагин используется по назначению и предупреждение не паразитное.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: плагин прямо обещает смену умолчания в будущей версии («will default the loop scope for asynchronous fixtures to function scope»). Незаданное значение означает, что поведение async-фикстур изменится при обновлении зависимости молча, и обнаружится это падением теста, а не апгрейдом.

ИСПРАВЛЕНИЕ ИЗВЕСТНО И ОДНОСТРОЧНО: в pyproject.toml, секция [tool.pytest.ini_options], добавить
  asyncio_default_fixture_loop_scope = "function"
(значение "function" — то, которое плагин объявляет будущим умолчанием, то есть выбор без изменения смысла в будущем).

ПОЧЕМУ ЗАВЕДЕНО ЗАДАЧЕЙ, А НЕ ПОЧИНЕНО НА МЕСТЕ: pyproject.toml огорожен владельцем до решения по развилке задачи hang-guard-promises-eleven-times-headroom-and-has-one, и правка ложится в ТОТ ЖЕ блок [tool.pytest.ini_options], где живёт faulthandler_timeout. Ключ другой и семантически с развилкой не пересекается, но трогать огороженный владельцем файл ради предупреждения — не тот размен. Делать ВМЕСТЕ с решением по hang-guard, одним заходом в файл.

ПОПУТНО В ТОМ ЖЕ ФАЙЛЕ, проверено в #183: комментарий в [tool.pytest.ini_options] отсылает к «tausik verify --full (env: TAUSIK_VERIFY_FULL=1)». Флага --full у команды НЕТ (verify --help показывает только --task, --scope, --relevant-files, --no-tests-expected). Работает переменная окружения. Исправить в тот же заход.

## Acceptance Criteria

1. НИ ОДНА строка дерева не обещает несуществующий флаг `tausik verify --full`. В pyproject.toml (комментарий к addopts и описание маркера slow) остаётся только TAUSIK_VERIFY_FULL=1. Квитанция: grep по исходникам даёт ноль совпадений вне сгенерированного состояния tausik/ и истории CHANGELOG.
2. Комментарии, которые ссылались на это обещание как на «отдельный открытый дефект» (scripts/gate_command_runner.py, tests/test_gate_outcome.py), приведены в соответствие — обещания больше нет, значит и ссылки на него лгать не должны.
3. УТВЕРЖДЕНИЕ ЗАДАЧИ ПРОВЕРЕНО, А НЕ ПРИНЯТО НА ВЕРУ: «всякий запуск печатает PytestDeprecationWarning» — под pytest 9.0.2 предупреждение НЕ печатается ни разу (оно поднимается в pytest_configure, до установки перехватчика, и видно только через python -W error::DeprecationWarning). В дереве ноль async-тестов; pytest-asyncio не объявлен ни в одном пути установки — это окружение разработчика, а не зависимость проекта.
4. НЕГАТИВНЫЙ СЦЕНАРИЙ, РЕШАЮЩИЙ ИСХОД: ключ asyncio_default_fixture_loop_scope НЕ добавляется, потому что в окружении БЕЗ плагина (все ячейки CI, любой участник по CONTRIBUTING.md) он даёт ошибку конфигурации PytestConfigWarning: Unknown config option. Замер сделан: pytest -o asyncio_default_fixture_loop_scope=function -p no:asyncio печатает это предупреждение. Обмен «невидимое предупреждение на одной машине» -> «видимое предупреждение везде» отвергнут; отказ записан в задаче, в CHANGELOG и в память проекта.
5. Тест test_it_names_the_environment_variable_and_not_the_missing_flag остаётся зелёным: продукт по-прежнему называет переменную окружения, а не флаг.

## Plan

## Rollback

Правка текстовая, поведение продукта не меняется. Откат: git revert возвращает ложное обещание флага --full в pyproject; на исполнение это не влияет никак, потому что флага нет ни до, ни после.

## Journal

- 2026-08-30T18:18:19Z [implementation] — [#191] ГЛАВНАЯ ПОСЫЛКА ЗАДАЧИ ОПРОВЕРГНУТА ЗАМЕРОМ, КЛЮЧ НЕ ДОБАВЛЕН. Три проверки, каждая с квитанцией. (1) «Всякий запуск печатает PytestDeprecationWarning» — на pytest 9.0.2 предупреждение не печатается НИ РАЗУ: ни обычным прогоном, ни с -rw, ни с -W always; шапка при этом честно показывает asyncio_default_fixture_loop_scope=None. Оно поднимается (проверено python -W error::DeprecationWarning -> INTERNALERROR с трассировкой до pytest_asyncio/plugin.py:247 warnings.warn), но глохнет: configure идёт раньше перехватчика warnings. Замер #183 устарел вместе с версией pytest, память #436. (2) «Асинхронные тесты в дереве ЕСТЬ (tests/test_gate_test_citation.py)» — НЕТ: в этом файле строка-литерал "async def test_delta():\n", которую тест ЗАПИСЫВАЕТ во временный файл. По всему tests/ ноль совпадений `async def test`; корутины есть только как хелперы (list_prompts и подобные), их гоняет asyncio.run. Будущая смена умолчания у async-фикстур физически не может нас коснуться. (3) pytest-asyncio не объявлен НИ В ОДНОМ пути установки: CI ставит pytest ruff mypy bandit + requirements.txt (mcp), CONTRIBUTING — pytest ruff pyyaml. Он стоит в глобальном site-packages разработчика рядом с playwright и ansible, то есть это окружение одной машины. РЕШАЮЩИЙ ЗАМЕР: pytest -o asyncio_default_fixture_loop_scope=function -p no:asyncio печатает PytestConfigWarning: Unknown config option — то есть добавление ключа обменяло бы НЕВИДИМОЕ предупреждение на одной машине на ВИДИМОЕ во всех ячейках CI и у каждого участника по CONTRIBUTING.md. Обмен отвергнут, конфиг не тронут. Вариант «-p no:asyncio в addopts» тоже отвергнут: он гасит плагин, но в день, когда в дерево придёт первый async-тест, тот молча не выполнится — это дыра дороже предупреждения. СДЕЛАНО ПО ВТОРОЙ, НАСТОЯЩЕЙ ЧАСТИ: обещание `tausik verify --full` снято из pyproject (комментарий к addopts и описание маркера slow) и из двух комментариев, называвших его «отдельным открытым дефектом» (scripts/gate_command_runner.py, tests/test_gate_outcome.py). Флага нет: verify --help даёт только --task, --scope, --relevant-files, --no-tests-expected.
- 2026-08-30T18:35:21Z [implementation] — AC-1: ✓ обещание несуществующего `tausik verify --full` снято из pyproject.toml в обоих местах — из комментария к addopts и из описания маркера slow; вместо него названа переменная окружения TAUSIK_VERIFY_FULL=1 и прямо сказано, что флага нет. Квитанция: grep по дереву даёт совпадения только там, где текст УТВЕРЖДАЕТ отсутствие флага (pyproject.toml:37 и :108, tests/test_gate_outcome.py:201), плюс сгенерированное состояние tausik/ и история задач — то есть ни одна живая строка больше не отсылает к флагу. AC-2: ✓ два комментария, называвшие обещание «отдельным открытым дефектом», приведены в соответствие: scripts/gate_command_runner.py (у _FULL_LANE_REMEDY) и tests/test_gate_outcome.py. Оба теперь перечисляют реальные флаги verify: --task, --scope, --relevant-files, --no-tests-expected. AC-3: ✓ посылка задачи проверена и ОПРОВЕРГНУТА тремя замерами. Предупреждение не печатается на pytest 9.0.2 ни в одном режиме (обычный прогон, -rw, -W always), хотя шапка показывает asyncio_default_fixture_loop_scope=None; оно поднимается в pytest_configure до установки перехватчика — доказано python -W error::DeprecationWarning, который даёт INTERNALERROR с трассировкой до pytest_asyncio/plugin.py:247. Async-тестов в дереве ноль: `async def test` не встречается ни разу, в tests/test_gate_test_citation.py это строка-литерал, записываемая во временный файл. pytest-asyncio не объявлен ни в одном пути установки (CI: pytest ruff mypy bandit + requirements.txt; CONTRIBUTING: pytest pytest-xdist ruff pyyaml) — он в глобальном site-packages разработчика рядом с playwright и ansible. AC-4: ✓ ключ asyncio_default_fixture_loop_scope НЕ добавлен, и это решение обосновано замером: `pytest -o asyncio_default_fixture_loop_scope=function -p no:asyncio` печатает PytestConfigWarning: Unknown config option. То есть добавление обменяло бы невидимое предупреждение на одной машине на видимое в каждом окружении без плагина — во всех ячейках CI и у любого участника по CONTRIBUTING.md. Отказ записан в задаче, в CHANGELOG (обе версии) и в память проекта #436. AC-5: ✓ tests/test_gate_outcome.py::TestTheRefusalIsActionable::test_it_names_the_environment_variable_and_not_the_missing_flag зелёный — продукт по-прежнему называет переменную окружения и не называет флаг; входит в scoped-прогон верифая #1841 (exit 0) и в полную ленту 7438 passed / exit 0. Negative: отвергнут и второй способ «починить» — `-p no:asyncio` в addopts. Замер показывает, что блокировка отсутствующего плагина безвредна (`-p no:totally_absent_plugin_xyz` собирает 20 тестов без ошибок), то есть технически это работает; отвергнуто по последствию: в день, когда в дерево придёт первый async-тест, он молча не выполнится — тихая дыра дороже громкого предупреждения. Негативная проверка самой правки: если бы обещание флага осталось, утверждение AC-1 (grep) нашло бы живую строку вне списка «здесь сказано, что флага нет». Domain: вне тестов смысл в том, что читатель конфига получает исполнимую команду. Проверено на самом продукте: `.tausik/tausik verify --help` перечисляет только --task, --scope, --relevant-files, --no-tests-expected — набравший `verify --full` получил бы отказ argparse. Теперь и pyproject, и текст отказа гейта называют одно и то же имя, которое работает.
