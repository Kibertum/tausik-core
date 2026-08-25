---
slug: rule5-checklist-keyword-theater
title: "Гейт Rule 5 проверяет СЛОВАРЬ, а не верификацию: «no checklist items found» снимается словом «scope» в заметках"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/gate_ac_check.py, scripts/service_ac_evidence.py (только чтение/переиспользование), tests/ (тесты гейта), docs/ru/agent-contract.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/service_gates.py и service_task.py (точки вызова не трогаем — меняется реализация предиката, не его место), конфиг-флаг task_done.checklist_hard (остаётся как есть)"
relevant_files:
  - "scripts/gate_ac_check.py"
  - "tests/test_checklist_hardgate.py"
  - "tests/test_agent_units_recording.py"
  - "scripts/hooks/bash_firewall.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T09:10:53Z"
---

## Goal

Хендофф сессии #132 зафиксировал, что предупреждение «verification checklist missing (SENAR Rule 5)» игнорировалось при КАЖДОМ закрытии, и поставил выбор: либо начать вести чеклист, либо перестать предупреждать. Разбор в сессии #133 показывает, что выбор ложный, потому что вести тут нечего. scripts/gate_ac_check.py::_checklist_keyword_scan считает вхождения слов из таблицы (_LIGHTWEIGHT_KW = ["scope","phantom","test tamper","secret","hardcoded secret"] и надмножества) в task.notes. Ноль вхождений → предупреждение. Одно вхождение → тишина. То есть предупреждение снимается не верификацией, а словом «scope», написанным где угодно в журнале.

При этом docstring соседней функции check_verification_checklist САМ это признаёт про v1.3: «That made QG-2 trivial to fool ("scope clean, no secrets" produced 2 hits) and gave nothing for AC traceability» — и объявляет заменой структурный парсер service_ac_evidence.build_report. Но замены не произошло: build_report ДОБАВЛЕН сверху, а keyword-скан остался и остался единственным источником этого предупреждения.

Хуже того, тот же keyword-скан работает ХАРД-ГЕЙТОМ: checklist_hard_block блокирует закрытие задач планировочного тира substantial/deep, если ни одно слово из таблицы не встретилось. Значит для самых дорогих задач условием закрытия является наличие словарного слова в тексте. Ремедиация в сообщении («Run /review, then log checklist evidence») буквальному исполнению не поддаётся: /review сам в notes не пишет, и выполнивший инструкцию агент гейт не снимет — снимет его тот, кто угадает словарь. Это ровно класс «обещанный путь, которого нет» из конвенции #282, но с ценой хард-блока.

Задача: решить и реализовать. Кандидат — привязать и предупреждение, и хард-гейт к структурному покрытию AC (build_report: covered/total_ac, test-refs, негативные сценарии), которое уже считается и уже честно отражает верификацию; keyword-таблицы удалить или свести к подсказке БЕЗ гейта. Обязательное требование: после правки закрытия сессии #133 (где evidence написан как «AC-N: ✓ tested via tests/...») должны проходить БЕЗ этого предупреждения, а закрытие с пустым evidence — не проходить. Проверить на реальных задачах из БД, а не на синтетике.

## Acceptance Criteria

1. Измерено на РЕАЛЬНЫХ данных БД, а не на синтетике: сколько закрытых задач получили предупреждение при наличии структурного AC-evidence, и сколько «прошли» чеклист-скан, не имея никакого evidence (т.е. чистое совпадение словаря). Обе цифры в журнал — они и есть обоснование правки.
2. Источник предупреждения и хард-гейта перестаёт быть подсчётом слов. И check_verification_checklist, и checklist_hard_block опираются на структурное покрытие AC (service_ac_evidence.build_report: covered/total_ac, test-refs, негативные сценарии) — на то, что уже считается и уже отражает верификацию.
3. Поведение на закрытиях сессии #133 (evidence вида «AC-N: ✓ tested via tests/...»): предупреждение НЕ выдаётся. Проверено на фактических notes этих задач из БД.
4. Обратная сторона: закрытие с пустым или бессодержательным evidence (нет ни одного AC с ✓/test-ref) предупреждение получает, а на тирах substantial/deep — блокируется. Проверено тестом.
5. Слово из старого словаря («scope», «secret») в заметках БОЛЬШЕ НЕ снимает гейт само по себе — тест на это обязателен, иначе правка не закрывает исходный дефект.
6. Если keyword-таблицы остаются как подсказка — они не влияют на вердикт, и это видно из кода. Если удаляются — удаляются вместе с _TIER_KEYWORDS/_TIER_COUNT и мёртвыми ссылками.
7. Документация приведена в соответствие: docs/ru/agent-contract.md (раздел Rule 5) описывает действующий механизм, а не прежний. pytest зелёный, CHANGELOG×2.
8. БЕЗОПАСНОСТЬ (поверхность угрозы этой задачи). Защищаемое свойство: «закрытие задачи требует доказательства верификации». Противник здесь — не внешний злоумышленник, а СВОЙ агент, оптимизирующий проход гейта: у него есть право писать в task notes, то есть во вход предиката. Требования: (а) новый предикат не должен снимать хард-гейт по признаку, который агент может выдать одной строкой прозы без выполнения работы, — конкретно, наличие подстроки «✓» или слова «tested» само по себе засчитываться НЕ должно, засчитывается только связка «номер AC + ссылка на существующий артефакт (tests/... :: имя теста)»; (б) тест на подделку обязателен: notes, состоящие из фраз-заглушек («AC-1: ✓», «all criteria verified», старые словарные слова), гейт НЕ снимают; (в) правка не должна ослаблять существующие блокирующие проверки — сравнение «до/после» по числу блокируемых закрытий на реальных данных, регресс в сторону послабления недопустим; (г) невозможность проверить существование теста (файл отсутствует) трактуется fail-closed, а не как успех.

## Plan

## Rollback

git revert. Риск асимметричен и учтён: правка МОЖЕТ сделать гейт строже (задачи с пустым evidence начнут блокироваться на substantial/deep). Если это остановит работу — немедленный обход штатным config task_done.checklist_hard=false, затем откат; открыть дыру правка не может, т.к. заменяет более слабый предикат более сильным.

## Journal

- 2026-07-24T09:10:51Z [implementation] — AC-1: ✓ tested via tests/test_checklist_hardgate.py — замер на РЕАЛЬНОЙ БД через сервисный слой (SQLiteBackend.task_list/task_get, без ручного SQL): 1044 закрытых задачи, 851 с AC. Словарный скан против структурного покрытия расходятся на 380 (44.7%): 320 задач прошли скан, не имея реальных доказательств ни под одним критерием; 60 получали предупреждение при реальных доказательствах. AC-2: ✓ tested via tests/test_checklist_hardgate.py::TestChecklistHardBlock — и checklist_missing, и checklist_hard_block читают service_ac_evidence.build_report; _checklist_keyword_scan удалён. AC-3: ✓ проверено на ФАКТИЧЕСКИХ notes четырёх закрытий сессии #133 из БД: все четыре warning=no (real_test_AC = 1/1/5/2 при total_AC 4/5/5/6). AC-4: ✓ tested via tests/test_checklist_hardgate.py::test_substantial_without_checklist_blocks и ::test_bare_checkmarks_do_not_clear_the_gate. AC-5: ✓ tested via tests/test_checklist_hardgate.py::test_keyword_vocabulary_alone_no_longer_clears_the_gate — та же строка 'scope clean, no secret leak', которую прежний тест утверждал как ПРОХОДЯЩУЮ, теперь пиновано как блокирующая; плюс интеграционный ::test_substantial_still_blocked_by_checklist_vocabulary. AC-6: ✓ _TIER_KEYWORDS/_LIGHTWEIGHT_KW/_STANDARD_KW/_HIGH_KW/_CRITICAL_KW удалены целиком; grep по репозиторию подтверждает отсутствие висячих ссылок (остались только в .claude/, перезалито bootstrap'ом). _TIER_COUNT оставлен осознанно — он называет глубину ревью в тексте подсказки, а не решает вердикт. AC-7: ✓ docs/ru/agent-contract.md строка Rule 5 переписана под действующий механизм; CHANGELOG.md + CHANGELOG.ru.md. Полный pytest: 5630 passed, 23 skipped.
- 2026-07-24T09:10:51Z [implementation] — AC-8 БЕЗОПАСНОСТЬ: (а) ✓ tested via tests/test_checklist_hardgate.py::test_bare_checkmarks_do_not_clear_the_gate — голая галочка и фраза 'all criteria verified' хард-гейт не снимают; засчитывается только связка «номер AC + резолвимая ссылка на тест». (б) ✓ tested via ::test_keyword_vocabulary_alone_no_longer_clears_the_gate — подделка старым словарём пинована. (в) ✓ сравнение до/после на реальных данных: хард-гейт стал СТРОЖЕ (27 задач блокировались бы теперь, 3 блокировались обеими версиями), послабление ровно одно — release-1-3-docs-sweep; проверено адресно: задача цитирует tests/test_project_mcp.py, tests/test_mcp_integration.py, tests/test_bootstrap_generate_mcp.py, все три файла СУЩЕСТВУЮТ, то есть прежний гейт блокировал реально верифицированную задачу за отсутствие магического слова. Регресса в сторону послабления нет. (г) ✓ tested via ::test_unresolvable_test_reference_is_treated_as_no_evidence — несуществующий путь трактуется как отсутствие доказательства (fail-closed). Domain: результат осмыслен вне тестов — предикат теперь опирается на факт, который агент не может создать текстом (существование файла на диске), а не на слово, которое он может напечатать; это и есть содержательная разница между надзором и его имитацией. Побочно: из 561 задачи, признанной 'без доказательств', 61 (11%) цитирует существующий тест в неподдерживаемой форме — не замолчано, заведено задачей ac-evidence-parser-format-strict; сообщение гейта называет рабочую форму AC-N: ✓ tests/...::test_x. Попутно исправлены три падения полного прогона, вызванные этими правками: force_utf8_io в bash_firewall.py (не-ASCII в новом сообщении блокировки), пересбор docs/_generated/constants.json (вырос счётчик тестов), фикстура test_agent_units_recording (опиралась на словарную строку).
- 2026-07-24T09:11:07Z [done] — Negative: негативные сценарии критериев прогнаны явно, а не подразумеваются. (1) Подделка словарём — tests/test_checklist_hardgate.py::test_keyword_vocabulary_alone_no_longer_clears_the_gate, строка 'scope clean, no secret leak' даёт block=True. (2) Подделка галочкой — ::test_bare_checkmarks_do_not_clear_the_gate, '1. ✓ 2. ✓ all criteria verified' даёт block=True. (3) Несуществующий артефакт — ::test_unresolvable_test_reference_is_treated_as_no_evidence, ссылка на tests/test_does_not_exist.py даёт block=True (fail-closed). (4) Граница между двумя уровнями строгости — ::test_manual_run_counts_for_the_warning_but_not_the_hard_gate: ручной прогон снимает предупреждение, но НЕ хард-гейт. (5) Интеграционный негатив на реальном task_done — ::test_substantial_still_blocked_by_checklist_vocabulary, задача остаётся active.
