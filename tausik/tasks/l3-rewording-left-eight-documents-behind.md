---
slug: l3-rewording-left-eight-documents-behind
title: "Переименование «high-risk closure» в «under-evidenced» дошло до кода и трёх доков, а ещё восемь мест печатают старую рамку"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: python
tier: moderate
call_budget: 30
defect_of: risk-l3-still-blocks-after-demotion
scope: "docs/, README.md, scripts/risk_l3_trigger.py, scripts/config_trust.py, scripts/external_reviewer.py, harness/claude/subagents/tausik-external-reviewer.md, tests/"
scope_exclude: null
relevant_files:
  - "scripts/risk_l3_trigger.py"
  - "scripts/config_trust.py"
  - "scripts/external_reviewer.py"
  - "scripts/risk_metrics.py"
scope_paths:
  - "docs/*"
  - README.md
  - README.ru.md
  - "scripts/risk_l3_trigger.py"
  - "scripts/config_trust.py"
  - "scripts/external_reviewer.py"
  - "scripts/risk_metrics.py"
  - "harness/claude/subagents/tausik-external-reviewer.md"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T19:38:49Z"
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

- 2026-08-01T19:38:16Z [planning] — РАЗВЕДКА СЕССИИ #155 (агент, только чтение; задача НЕ начата). Метод чист — Grep по репозиторию, БД не трогалась. ЧИСЛО НЕ СОШЛОСЬ, И ЭТО ВАЖНО: не восемь, а 15 строк в 11 файлах-ИСХОДНИКАХ. Все 10 позиций из перечня в теле задачи подтверждены чтением, плюс НАЙДЕНЫ ДВЕ, которых в перечне нет: - scripts/risk_metrics.py:54 — `lines.append(f"Recent high-risk: {slugs}")`. То есть `tausik metrics` ПЕЧАТАЕТ «Recent high-risk», при том что соседняя функция format_risk_status_line в ТОМ ЖЕ ФАЙЛЕ уже несёт «descriptive, not predictive». Расхождение внутри одного файла. - README.ru.md:196 — зеркало README.md:197. Если править только английский, зеркала разъедутся. ИСХОДНИКИ (15 строк, 11 файлов): scripts/risk_l3_trigger.py:165 (комментарий) и :203 (ТЕЛЕМЕТРИЯ — строка уходит в events и переживёт формулировку, это AC2), scripts/config_trust.py:142, scripts/external_reviewer.py:3, scripts/risk_metrics.py:54, harness/claude/subagents/tausik-external-reviewer.md:3, docs/en/senar.md:90 и :100, docs/ru/senar.md:90 и :100, docs/ru/agent-contract.md:166 (колонка enforcement «Hard (при high-risk)»; стр. 215 УЖЕ поправлена), docs/en/config-trust-tiers.md:14, docs/ru/config-trust-tiers.md:14, README.md:197, README.ru.md:196. ПОГРАНИЧНЫЕ — решить ЯВНО, а не молча: (1) harness/claude/subagents/tausik-external-reviewer.md:35 «Hunt the high-risk failure modes first» — это про режимы отказа В КОДЕ, а не про закрытие, но следующая фраза «the factors that escalated this closure» привязывает к тому же композиту. (2) docs/ru/research/failclosed-gates-audit.md:29 — research-аудит есть СНИМОК состояния на момент замера, формально исторический документ. НЕ ТРОГАТЬ: CHANGELOG.md:1549 и :4456 плюс зеркала CHANGELOG.ru.md:1563 и :4469 — записи выпуска v1.5, описывают прошлое. CHANGELOG.md:166-167 и зеркало уже несут НОВУЮ рамку. ЛОЖНЫЕ СРАБАТЫВАНИЯ, не путать: «high-risk» классификатора brain publish (brain_publish_flow.py, project_parser_brain.py, brain_cli_ops.py, test_brain_mcp_write.py) — ДРУГАЯ подсистема; «high-risk systems» из EU AI Act в docs/*/receipts.md — регуляторный термин. ЗАМЕЧАНИЕ ПО AC3, существенное: имеющийся тест tests/test_risk_l3_trigger.py:201-207 проверяет ТОЛЬКО строку отказа гейта. НИ ОДНА из 15 найденных строк им не ловится. Значит репозиторный гейт «нет `high-risk closure` вне тестов и CHANGELOG» действительно нужен — иначе перечень отрастёт снова.
- 2026-08-03T19:37:36Z [implementation] — AC1, ПЕРЕЧЕНЬ ПЕРЕПРОВЕРЕН, и он устарел в обе стороны — перечень из тела задачи собран grep'ом сессии #155. Мой первый grep нашёл ВОСЕМЬ мест, а не пятнадцать: русские формулировки пишутся иначе ('high-risk закрытие', 'закрытии высокого риска'), и англоязычный шаблон их не ловил. Проверил каждый пункт ОТКРЫТИЕМ файла — все на месте. ИСПРАВЛЕНО 15 строк в 11 файлах-исходниках: risk_l3_trigger.py:165 и :203, config_trust.py:142, external_reviewer.py:3, risk_metrics.py:54, docs/en/senar.md:90 и :100, docs/ru/senar.md:90 и :100, docs/ru/agent-contract.md:166, docs/en/config-trust-tiers.md:14, docs/ru/config-trust-tiers.md:14, README.md:197, README.ru.md:196, harness/claude/subagents/tausik-external-reviewer.md:3. ОТСУТСТВУЕТ, а не пропущено: docs/ru/research/failclosed-gates-audit.md:29 — файл существует, фразы в нём НЕТ, пограничный случай (2) из постановки отпал сам. ПОГРАНИЧНЫЙ СЛУЧАЙ (1) РЕШЁН ЯВНО: строка :35 'Hunt the high-risk failure modes first: the factors that escalated this closure' СМЕШИВАЛА два разных предмета — тяжесть дефектов в коде и толщину доказательства закрытия; перечисленные там факторы (тонкая дельта тестов, слабое доказательство AC) относятся ко второму, а названы были первым. Переписана так, чтобы факторы указывали, ГДЕ смотреть, а не ЧТО найдётся. AC2, ТЕЛЕМЕТРИЯ: строка в events переписана на 'under-evidenced closure'. УЖЕ ЗАПИСАННЫЕ строки в БД НЕ переписываются — старые события останутся со старой рамкой, и это ожидаемо, а не новый дефект: событие есть запись о том, что было сказано в тот момент. AC5: grep по scripts/, harness/, bootstrap/, tests/ и по json/yaml после переименования — фразу не разбирает НИКТО, единственное вхождение осталось в образцах моего же гейта. Контракт не сломан. AC4: 130 тестов области зелёные без правки ожиданий, порог и MIN_MEASURED_WEIGHT не тронуты.
- 2026-08-03T19:38:47Z [implementation] — AC-1: ✓ tests/test_l3_framing_is_uniform.py::test_no_shipped_text_calls_an_under_evidenced_closure_high_risk AC-2: ✓ tests/test_l3_framing_is_uniform.py::test_no_shipped_text_calls_an_under_evidenced_closure_high_risk AC-3: ✓ tests/test_l3_framing_is_uniform.py::test_the_guard_actually_scans_something AC-3: ✓ tests/test_l3_framing_is_uniform.py::test_the_patterns_would_actually_fire AC-3: ✓ tests/test_l3_framing_is_uniform.py::test_the_replacement_wording_is_not_itself_flagged AC-4: ✓ tests/test_risk_l3_trigger.py::TestTheRefusalStatesItsOwnBasis AC-5: ✓ tests/test_l3_framing_is_uniform.py::test_no_shipped_text_calls_an_under_evidenced_closure_high_risk AC-3 закрыт ТРЕМЯ проверками, а не одной, потому что гейт может быть зелёным по двум разным пустым причинам: он ничего не сканирует, или его шаблоны ни с чем не совпадают. Обе исключены отдельно, плюс четвёртая проверка запрещает гейту браковать САМУ замену — иначе починка была бы неприземляемой. AC-1: перечень из тела задачи ПЕРЕПРОВЕРЕН открытием каждого файла и оказался неполным в обе стороны. Исправлено 15 строк в 11 исходниках. ОТСУТСТВУЕТ, а не пропущено: docs/ru/research/failclosed-gates-audit.md — файл есть, фразы нет. AC-2: телеметрия events переписана; уже записанные строки НЕ переписываются, это названо в журнале как ожидаемое, а не дефект. AC-4 доказан прогоном: 130 тестов области зелёные без правки ожиданий; порог и MIN_MEASURED_WEIGHT не тронуты. AC-5: grep по scripts/, harness/, bootstrap/, tests/, json/yaml ПОСЛЕ переименования — фразу не разбирает никто. Домен: гейт сканирует ИСХОДНИКИ, а не сгенерированные копии .claude/.cursor/.kilo/.opencode/.qwen — иначе один дефект отчитывался бы пятикратно и «чинился» пересборкой вместо правки. Исследовательские заметки исключены осознанно: они фиксируют, что видел аудит В МОМЕНТ замера, и позднее переименование не делает их ложными.
- 2026-08-03T19:39:07Z [done] — Root cause (documentation): решение #212 переписало ОСНОВАНИЕ L3-эскалации (величина описывает толщину доказательства, а не предсказывает побег дефекта), и правка дошла до сообщения гейта и матрицы соответствия, но не до остальных мест, потому что переименование велось по НАЙДЕННЫМ вхождениям, а не по закрытой форме. Русские формулировки вдобавок пишутся иначе ('high-risk закрытие', 'закрытии высокого риска'), поэтому англоязычный grep их не показывал ни автору #212, ни первому проходу здесь. Prevention: единообразие рамки проверяется МЕХАНИЧЕСКИ — tests/test_l3_framing_is_uniform.py сканирует исходники на запрещённые формулировки в обоих языках и валится при появлении девятого места; сам гейт защищён тремя дополнительными проверками от пустоты (сканирует ли он что-нибудь, срабатывают ли шаблоны, не бракует ли он саму замену).
