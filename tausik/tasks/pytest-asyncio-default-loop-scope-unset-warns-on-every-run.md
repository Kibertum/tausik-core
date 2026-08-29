---
slug: pytest-asyncio-default-loop-scope-unset-warns-on-every-run
title: "pytest-asyncio предупреждает на КАЖДОМ прогоне: asyncio_default_fixture_loop_scope не задан"
status: planning
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
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

## Plan

## Rollback

Одна строка asyncio_default_fixture_loop_scope в pyproject. Откат: git revert. Значение function совпадает с будущим умолчанием плагина, поэтому откат возвращает предупреждение, а не меняет поведение фикстур.

## Journal
