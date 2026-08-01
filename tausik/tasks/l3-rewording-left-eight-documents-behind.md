---
slug: l3-rewording-left-eight-documents-behind
title: "Переименование «high-risk closure» в «under-evidenced» дошло до кода и трёх доков, а ещё восемь мест печатают старую рамку"
status: planning
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: moderate
call_budget: 30
defect_of: risk-l3-still-blocks-after-demotion
scope: "docs/, README.md, scripts/risk_l3_trigger.py, scripts/config_trust.py, scripts/external_reviewer.py, harness/claude/subagents/tausik-external-reviewer.md, tests/"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Найдено ревью сессии #154. Задача risk-l3-still-blocks-after-demotion (решение #212) переписала основание L3-эскалации: величина ОПИСЫВАЕТ толщину доказательства и не предсказывает побег дефекта. Сообщение гейта, senar-compliance-matrix EN+RU и agent-contract.md приведены в соответствие. Остальные места — нет, и они продолжают подавать величину как оценку РИСКА, то есть как то, чем она по измерению не является.

МЕСТА, названные ревью (проверить каждое перед правкой — список составлен grep'ом, не чтением):
- scripts/risk_l3_trigger.py:165,203 — телеметрия понижения пишет в events строку «l3_block_on_high=false — high-risk closure (measured {ms})». Событие переживёт формулировку и будет читаться в метриках.
- docs/en/senar.md и docs/ru/senar.md, около строк 90 и 100.
- docs/ru/agent-contract.md:166 (строка 217 уже поправлена, эта — нет).
- docs/en/config-trust-tiers.md:14 и docs/ru/config-trust-tiers.md:14.
- README.md:197.
- scripts/config_trust.py:142 — описание гарда.
- scripts/external_reviewer.py:3 и harness/claude/subagents/tausik-external-reviewer.md:3.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Решение #206 ровно в том и состояло, что число, поданное как вердикт о качестве, читается как вердикт о качестве. Пока восемь мест зовут закрытие «высокорисковым», понижение сделано в одном месте, а прочитано будет в девяти — то же расхождение решения с текстом, которое эта серия задач и закрывает, просто вынесенное из кода в доки.

ПРОВЕРЕНО РЕВЬЮ И НЕ ТРЕБУЕТ ДЕЙСТВИЙ: строку «High-risk closure» никто не РАЗБИРАЕТ — grep по harness/, bootstrap/, .claude/, hooks/, JSON и YAML нашёл её только в тестах, которые утверждают её ОТСУТСТВИЕ, и в одной строке журнала задачи. То есть смена формулировки контракт не ломает.

## Acceptance Criteria

1. Каждое место из перечня в цели ПРОВЕРЕНО ЧТЕНИЕМ и либо приведено к формулировке решения #212, либо в журнале сказано, почему в этом месте прежняя рамка уместна. Перечень собран grep'ом и мог устареть — пункт, которого не оказалось, отмечается как отсутствующий, а не молча пропускается.
2. ТЕЛЕМЕТРИЯ ОТДЕЛЬНО: строка, уходящая в таблицу events при l3_block_on_high=false, переживает форматирование вывода и читается позже в метриках, поэтому она обязана нести ту же рамку. Прежние строки в БД не переписываются — сказать об этом в журнале, чтобы расхождение старых и новых записей не выглядело новым дефектом.
3. ЕДИНООБРАЗИЕ ПРОВЕРЯЕТСЯ МЕХАНИЧЕСКИ, а не глазами: тест или гейт, который валится при появлении «high-risk closure» в коде, доках или harness вне тестов, утверждающих её отсутствие. Иначе девятое место появится на следующей правке.
4. НЕГАТИВ: смысл гейта не изменён. l3_block_on_high по-прежнему блокирует по умолчанию, tests/test_risk_l3_trigger.py::TestTheRefusalStatesItsOwnBasis зелёный без правки ожиданий, порог и MIN_MEASURED_WEIGHT не тронуты. Это задача про формулировку, и любое изменение поведения в ней — выход за область.
5. НЕГАТИВ ПО КОНТРАКТУ: подтверждено, что строку не разбирает никто (ревью проверило grep'ом по harness/, bootstrap/, .claude/, hooks/, JSON, YAML) — проверку повторить после правки, чтобы переименование не сломало парсер, добавленный с тех пор.
6. Полный pytest зелёный; ruff и mypy чистые; bootstrap drift отсутствует (правится harness — обязателен bootstrap --ide all).
Записи в CHANGELOG НЕ ДОБАВЛЯЮТСЯ: пользовательское изменение уже описано записью про L3-эскалацию в этом же [Unreleased]. Закрывать с --no-changelog, причину — в журнал.

## Plan

## Rollback

git revert

## Journal
