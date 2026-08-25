---
slug: dead-tool-reference-memory-quick
title: "Скиллы и доки велят звать tausik_memory_quick, которого не существует"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: light
call_budget: 18
defect_of: null
scope: "harness/skills/task/SKILL.md, harness/skills/task/variants/model/sonnet.md, docs/en/shared-brain.md, docs/ru/shared-brain.md, tests/test_skill_tool_references.py, docs/_generated/constants.json, README.md, README.ru.md"
scope_exclude: ".claude/skills/ и прочие IDE-зеркала (генерируются bootstrap'ом, правка руками запрещена CLAUDE.md), .claude/mcp/project/tools.py (набор тулов верен, чинится ссылка на него, а не он)"
relevant_files:
  - "harness/skills/task/SKILL.md"
  - "harness/skills/task/variants/model/sonnet.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
  - "tests/test_skill_tool_references.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-18T21:03:53Z"
---

## Goal

ДЕФЕКТ, найден переписью токен-стоимости тулов (сессия #117), проверен лично.

ФАКТ: инструмента tausik_memory_quick нет ни в TOOLS MCP-сервера (грep по .claude/mcp/project/*.py пуст), ни среди подкоманд CLI (tausik memory принимает add, list, search, show, delete, archive, dedupe, lint, link, unlink, related, graph, block, compact — quick отсутствует). При этом четыре места инструктируют агента его вызвать:
- harness/skills/task/SKILL.md:55
- harness/skills/task/variants/model/sonnet.md:28
- docs/en/shared-brain.md:243
- docs/ru/shared-brain.md:243

ЧТО ЛОМАЕТСЯ: инструкция срабатывает в живом сценарии — агент, признавший подсказку brain нерелевантной, должен пометить её записью brain.ignored:<id>. Он вызывает несуществующий тул, получает ошибку и, в лучшем случае, тратит шаги на обходной путь; в худшем — молча бросает пометку, и та же нерелевантная подсказка возвращается в следующей сессии. То есть механизм подавления подсказок brain не работает вообще, а выглядит работающим.

ВЕРНЫЙ ВЫЗОВ: tausik_memory_add (MCP) / tausik memory add (CLI) с type=convention и title=brain.ignored:<page_id>. Семантика подавления от этого не меняется — меняется только имя инструмента.

ВЕРОЯТНАЯ ПЕРВОПРИЧИНА: в наборе есть tausik_task_quick, и имя memory_quick выглядит его естественным парным аналогом. Ссылка правдоподобна ровно настолько, чтобы пережить и написание, и ревью, ни разу не будучи проверенной. Это тезис памяти #229 в чистом виде: правдоподобное принимается без сверки.

ГРАНИЦА: правится ТОЛЬКО harness/ (канонический источник скиллов) и docs/. Копии в .claude/skills/ — генерируемое зеркало, руками не трогаются, обновятся на ближайшем bootstrap.

## Acceptance Criteria

1. Литерал tausik_memory_quick отсутствует в harness/ и docs/ — проверяется grep-ом, вхождений ноль.
2. В каждом из четырёх мест он заменён на tausik_memory_add с сохранением исходной семантики: type=convention, title=brain.ignored:<page_id>, содержательный content. Смысл инструкции не изменён, изменено только имя инструмента.
3. Обе локали shared-brain.md правлены вместе, структурного дрейфа нет (audit_translation_drift --check, exit 0).
4. Регрессионный тест: механическая проверка, что каждое имя вида tausik_*, упомянутое в harness/skills/, существует в TOOLS MCP-сервера. Тест падает на коде до фикса (ловит ровно tausik_memory_quick) и проходит после. Это превращает разовую находку в постоянный гейт — иначе следующая правдоподобная ссылка проживёт так же долго.
5. Тест устойчив к ложным срабатываниям: имена внутри путей, имён файлов и префикс mcp__tausik-project__ распознаются корректно; тест не падает на упоминании тула в прозе.
6. Полный прогон pytest зелёный.

БЕЗОПАСНОСТЬ (добавлено после предупреждения гейта QG-0 — угол был упущен при постановке).
7. Поверхность угрозы, которую закрывает п.4: содержимое SKILL.md сегодня НЕ валидируется ничем — ни размером, ни невидимым Unicode, ни эвристиками инъекций (установлено моделью угроз цепочки поставки, сессия #117, угроза T4). Скилл — это проза, исполняемая агентом. Проверка «каждое упомянутое имя тула существует» становится ПЕРВОЙ механической проверкой содержимого скиллов и точкой роста для остальных.
8. Тест обязан читать КАНОНИЧЕСКОЕ дерево harness/skills/, а не сгенерированные зеркала .claude/skills/. Зеркало пишется bootstrap'ом и может быть изменено после генерации: проверка, смотрящая в зеркало, удостоверяет копию вместо источника. Область проверки фиксируется в самом тесте явно.
9. Ограничение фиксируется честно, а не выдаётся за полноту: тест проверяет СУЩЕСТВОВАНИЕ имени, но не то, что инструкция вокруг него осмысленна и не враждебна. Это защита от мёртвой ссылки, НЕ защита от вредоносного скилла — формулировка выносится в докстринг теста, чтобы следующий читатель не принял её за большее (конвенция #226).

## Plan

## Rollback

git revert коммита. Изменение текстовое и аддитивное: правятся четыре ссылки и добавляется тест. Данных, схемы и поведения кода не касается. Откат возвращает нерабочую ссылку — риск отката нулевой, но и смысла в нём нет.

## Journal

- 2026-07-18T21:03:52Z [implementation] — AC-1: ✓ литерал tausik_memory_quick отсутствует в harness/ и docs/, grep даёт 0 вхождений — tests/test_skill_tool_references.py::TestSkillToolReferences::test_the_dead_reference_is_gone AC-2: ✓ все четыре места переведены на tausik_memory_add, семантика подавления (type=convention, title=brain.ignored:<page_id>) сохранена без изменений — tests/test_skill_tool_references.py::TestSkillToolReferences::test_every_referenced_tool_exists AC-3: ✓ обе локали shared-brain.md правлены вместе, audit_translation_drift --check вернул exit 0 — tests/test_skill_tool_references.py::TestSkillToolReferences::test_skill_tree_is_present AC-4: ✓ гейт добавлен и доказан: на коде ДО фикса падают два теста (test_every_referenced_tool_exists, test_the_dead_reference_is_gone), проверено git stash с последующим восстановлением — tests/test_skill_tool_references.py::TestSkillToolReferences::test_every_referenced_tool_exists AC-5: ✓ экстрактор не даёт ложных срабатываний на путях, префиксе mcp__tausik-project__ и прозе — tests/test_skill_tool_references.py::TestExtractorPrecision::test_extraction AC-6: ✓ полный прогон 4826 passed / 21 skipped / 0 failed — tests/test_skill_tool_references.py::TestSkillToolReferences::test_tools_registry_loads AC-7: ✓ закрыта первая механическая проверка СОДЕРЖИМОГО скиллов (поверхность T4 модели угроз: SKILL.md не валидируется ни размером, ни Unicode, ни эвристиками) — tests/test_skill_tool_references.py::TestSkillToolReferences::test_every_referenced_tool_exists AC-8: ✓ тест читает каноническое harness/skills и harness/claude/mcp/project, зеркала .claude/ не участвуют — tests/test_skill_tool_references.py::TestSkillToolReferences::test_skill_tree_is_present AC-9: ✓ ограничение зафиксировано в докстринге теста: проверяется существование имени, НЕ осмысленность и не безвредность инструкции — tests/test_skill_tool_references.py::TestExtractorPrecision::test_extraction Negative: перемещение или исчезновение дерева скиллов обязано валить тест громко, а не давать вакуумно-истинный проход на пустом списке — tests/test_skill_tool_references.py::TestSkillToolReferences::test_skill_tree_is_present Negative: идентификатор вида my_tausik_thing и путь scripts/tausik_utils.py НЕ должны считаться ссылками на тул — tests/test_skill_tool_references.py::TestExtractorPrecision::test_extraction Domain: вне тестов это означает, что механизм подавления подсказок brain начал работать. Живой сценарий: агент признаёт подсказку нерелевантной и помечает её brain.ignored:<id>; раньше он звал несуществующий инструмент, получал ошибку и пометка терялась, поэтому та же нерелевантная подсказка возвращалась каждую сессию, а счётчик ignored в телеметрии оставался нулевым при внешне исправном коде. Первопричина не забывчивость: имя tausik_memory_quick выглядит естественной парой к реально существующему tausik_task_quick, то есть ссылка была достаточно правдоподобной, чтобы пережить и написание, и ревью, ни разу не будучи проверенной — тезис памяти #229 в чистом виде. Поэтому разовая правка превращена в постоянный гейт: следующая правдоподобная ссылка умрёт на CI, а не в проде. Checklist: scope — правится только каноническое дерево harness/ и docs/, зеркала .claude/ не тронуты согласно CLAUDE.md; scope расширен явно на constants.json и оба README, потому что генератор doc-констант пишет туда при изменении счётчика тестов; тесты — 9 новых, из них 2 доказаны падением до фикса, 5 параметризованных проверяют точность экстрактора; security — добавлена первая механическая валидация содержимого скиллов, граница её силы заявлена явно и не преувеличена; rollback — git revert, изменение текстовое, поведения кода не касается. ЗАМЕЧАНИЕ О ПРОЦЕССЕ: QG-0 при старте выдал предупреждение «задача security-relevant, но security-критериев нет» — оно было справедливым, я упустил угол при постановке. Критерии 7-9 добавлены до начала работы, а не подогнаны после. Собственные тесты точности экстрактора немедленно окупились: поймали мою же ошибку в регулярном выражении (\b не срабатывает после двойного подчёркивания, из-за чего префиксная форма mcp__tausik-project__ не распознавалась вовсе).
