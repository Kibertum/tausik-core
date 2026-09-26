---
slug: adapt-dual-signature-implements-a-withdrawn-norm
title: "ADAPT требует двойной подписи — норму, которую ADR-011 отозвал как фикцию"
status: done
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_adapts.py"
  - "scripts/renar_drift.py"
  - "scripts/project_parser_adapts.py"
  - "scripts/backend_schema_adapts.py"
  - "scripts/backend_crud_adapts.py"
  - "harness/claude/mcp/project/tools_adapt.py"
  - "tests/test_adapts.py"
  - "tests/test_renar_drift.py"
  - "tests/test_enum_single_source.py"
  - "tests/test_renar_export.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - RENAR-CONFORMANCE.yaml
  - "renar/conformance.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_adapts.py"
  - "scripts/adapt_closed_lists.py"
  - "scripts/renar_drift.py"
  - "scripts/project_parser_adapts.py"
  - "scripts/backend_schema_adapts.py"
  - "scripts/backend_crud_adapts.py"
  - "harness/claude/mcp/project/tools_adapt.py"
  - "tests/test_adapts.py"
  - "tests/test_renar_drift.py"
  - "tests/test_enum_single_source.py"
  - "tests/test_renar_export.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on:
  - actz-the-contract-contour-artifact-is-missing
completed_at: "2026-09-06T12:53:11Z"
resolution: null
resolution_reason: null
---

## Goal

Команда `tausik adapt sign` объявляет в справке «Record a dual signature (§7.5); architect → ed25519». RENAR ADR-011 (accepted) подпись клиента с ADAPT СНЯЛ, и назвал причину: клиент подписывал инженерный документ, которого не читал и не мог оценить. Граница проведена по АУДИТОРИИ, а не по содержанию: показанное клиенту и утверждённое есть обязательство и живёт в ACTZ; не показанное есть интерпретация и живёт в ADAPT. Следствия для нас: подписывает ТОЛЬКО архитектор; состояние `client-ready` изымается из машины состояний ADAPT, потому что вынесение вопросов клиенту стало предметом ACTZ; каждая обратная находка обязана нести `decided-in` на пункт ПОДПИСАННОГО ACTZ. Задача: привести реализацию к принятой редакции, а не дописать ACTZ рядом со старым поведением. Отдельно проверить, что уже подписанные ADAPT в живых базах не становятся невалидными молча — миграция обязана назвать, что произошло. Это долг, а не улучшение: мы объявляем себя эталонной реализацией и предъявляем отозванную норму.

## Acceptance Criteria

AC-1 (новая подпись клиента невозможна): сервисный слой отказывает на роли client с сообщением, называющим ADR-011 и §7.5; CLI-справка `adapt sign` перестаёт обещать двойную подпись. Negative: попытка подписать за клиента даёт ServiceError, а не тихую запись.
AC-2 (утверждение требует подписи АРХИТЕКТОРА, и только её): переход в approved проверяет наличие подписи архитектора; отсутствие клиентской больше НЕ является нарушением. Negative: ADAPT в approved с подписью только архитектора — не находка; ADAPT в approved БЕЗ подписи архитектора — находка (мутация «проверка снята» убивается).
AC-3 (история не переписывается): CHECK на adapt_signatures.role ОСТАЁТСЯ допускающим client, миграции нет, и причина записана в комментарии схемы — уже записанная подпись есть запись аудита, V1 запрещает её стирать, а вычистка роли из CHECK потребовала бы удалить или переписать чужие строки. Тест: база с исторической клиентской подписью читается и не ломается.
AC-4 (историческое НАЗЫВАЕТСЯ, а не замалчивается): детектор дрейфа сообщает о каждой сохранившейся клиентской подписи как о записи по ОТОЗВАННОЙ норме (kind называет ADR-011), warn-only. Negative: база без таких подписей даёт ноль находок; мутация «находка снята» убивается.
AC-5 (перечень ролей выведен, а не переписан): SIGNATURE_ROLES остаётся единственным источником, и всё, что его читает (renar_drift, tools_adapt, project_parser_adapts, tests), продолжает работать без второй копии; тест единственного источника зелёный.
AC-6 (объявление в артефакте): §7.5 больше не заявляется исполненной в форме двойной подписи — RENAR-CONFORMANCE.yaml и renar/conformance.md перегенерированы, и там, где раньше упоминалась двойная подпись, стоит подпись архитектора.
AC-7: docs/{ru,en} правятся везде, где обещана двойная подпись; полный прогон, mypy, ruff, bootstrap --check; мутации объявлены и убиты ПО ВЕТВИ либо объявлены эквивалентными; CHANGELOG в обоих файлах; отклонение от плана отката (миграции нет) объявлено в CHANGELOG с причиной.

## Plan

## Rollback

git revert коммита задачи. Схема НЕ меняется и миграции нет — по замеру: client-ready в нашей машине состояний отсутствует, adapt_signatures пуста, а CHECK намеренно оставлен допускающим client, чтобы исторические подписи в чужих базах не стали невалидными. Поэтому откат возвращает только код, справку и документацию; данные ни при каком исходе не затрагиваются.

## Journal

- 2026-09-06T12:37:36Z [planning] — ЗАМЕР ДО ПРАВКИ, ТРИ НАХОДКИ, ДВЕ МЕНЯЮТ ФОРМУ РАБОТЫ. (1) ПРЕМИСА ПОДТВЕРЖДЕНА ТЕКСТОМ СТАНДАРТА, а не только ADR: корпус standards/renar/standard/07-adapt.md §7.5 уже назван «Утверждение ADAPT — подпись архитектора», таблица подписей содержит ОДНУ строку (архитектор со стороны исполнителя), и отдельный абзац «Почему подпись клиента здесь отсутствует» объясняет причину. То есть нормативные правки ADR-011 в корпус ВНЕСЕНЫ, хотя фронтматтер самого ADR ещё говорит «правки не вносятся до согласования пакета» — читать надо ТЕКСТ, а не только заголовок решения. Мы действительно предъявляем отозванную норму. (2) СОСТОЯНИЯ client-ready У НАС НЕТ ВОВСЕ: grep по scripts/harness/tests пуст, ADAPT_STATUSES = draft/review/asked/answered/approved/frozen/superseded. Половина задачи («изъять client-ready из машины состояний») беспредметна — изымать нечего. (3) МИГРАЦИЯ ДАННЫХ, КОТОРОЙ ТРЕБУЕТ ПЛАН ОТКАТА, В ЖИВОЙ БАЗЕ НЕ ИМЕЕТ ПРЕДМЕТА: adapt_signatures пуста (ноль строк по обеим ролям), adapts — одна запись в draft. В базах потребителей строки возможны, и это решает форму починки. ФОРМА, КОТОРУЮ ВЫБИРАЮ, И ПОЧЕМУ ОНА ОТЛИЧАЕТСЯ ОТ ПЛАНА В ЗАДАЧЕ: НЕ переписывать таблицу миграцией, а (а) закрыть запись новых клиентских подписей на сервисном слое, (б) ОСТАВИТЬ CHECK допускающим значение client, потому что уже записанная подпись есть запись аудита, а V1 запрещает её стирать — миграция, вычищающая роль из CHECK, обязала бы удалить или переписать чужие исторические строки, то есть сделала бы ровно то, чего задача требует избежать («не становятся невалидными молча»), (в) объявить это прямо в комментарии схемы и найти оставшиеся клиентские подписи детектором дрейфа как записи по отозванной норме. Это и есть «миграция обязана назвать, что произошло» в форме, не трогающей чужие данные. Отклонение от плана отката записываю здесь как решение по существу, а не молча.
- 2026-09-06T12:44:26Z [implementation] — ПОЧИНКА. SIGNATURE_ROLES = ("architect",) — то, что МОЖНО записать; рядом HISTORICAL_SIGNATURE_ROLES = ("client","architect") — то, что схема ещё принимает, чтобы уже записанное не стало невалидным. adapt_sign отказывает на роли client сообщением, называющим ADR-011, §7.5 и ACTZ; approved наступает по подписи архитектора; ветвь «ждём остальных» оставлена и объяснена (решение принимается по МНОЖЕСТВУ ролей, а не по счёту). renar_drift: клиентская подпись — находка signature-role-withdrawn (warn), а не «неверная роль»; чужое значение по-прежнему signature-role-invalid; проверка approved требует только архитектора. Комментарий в backend_schema_adapts объясняет, почему CHECK не сужается: сузить — значит удалить или переписать чужие строки, то есть сделать ровно то, чего задача велит избежать (V1). МИГРАЦИИ НЕТ ПО ЗАМЕРУ, отклонение от плана отката объявлено. Носители «двойной подписи» найдены обходом и поправлены: справка CLI, описания двух инструментов MCP (их читают агенты), docs/{ru,en}/cli.md и mcp.md, докстринги service_adapts и backend_crud_adapts; в исторической миграции v36 формулировка ОСТАВЛЕНА — она описывает, что построила. Гейт области отказывал ДВАЖДЫ и оба раза по делу: mcp.md и tools_adapt не были в ACL — расширял ПО ЗАМЕРУ. Манифест регенерирован до v20, «двойной подписи» в артефактах ноль. МУТАЦИИ 8: убито 6 сразу, две выжили и разобраны ДО КОНЦА. D5 (ветвь чужой роли снята) выжила, потому что мой тест ПРОПУСКАЛСЯ: CHECK не даёт вставить 'notary', и pytest.skip делал мутацию невидимой — тест переписан на таблицу БЕЗ CHECK, что и есть настоящий сценарий детектора (старая схема, миграция с выключенными проверками), D5 убита. D7 (исторические роли схлопнуты) выжила, потому что 'client' ловится ветвью раньше — написан тест, сверяющий HISTORICAL_SIGNATURE_ROLES с ЖИВЫМ CHECK через check_domain, D7 убита. Итог 8/8.
- 2026-09-06T12:46:45Z [implementation] — ПОЛНАЯ ЛЕНТА НАШЛА ТО, ЧЕГО НЕ НАШЛИ ЦЕЛЕВЫЕ ФАЙЛЫ: 20 падений в tests/test_renar_export.py плюс одно в test_adapts. Причина настоящая, не помеха: фикстура экспорта подписывала ADAPT ЗА КЛИЕНТА (svc.adapt_sign("adapt-one","client",...)), а отказ теперь честный, и падал КАЖДЫЙ тест, которому нужна засеянная база. Это подтверждение правила «полный прогон перед каждым пушем» (память #592): целевые файлы задачи были зелёными. ПОЧИНЕНО ПО СУЩЕСТВУ: фикстура пишет строку подписи АРХИТЕКТОРА прямо в таблицу (сервисный слой потребовал бы ключ проекта, которого у фикстуры быть не должно), утверждение о роли в frontmatter обновлено, а тест «подписать снятый ADAPT» подписывает архитектором. Гейт области отказал ТРЕТИЙ раз и снова по делу — test_renar_export.py не был в ACL.
- 2026-09-06T12:48:59Z [implementation] — AC-1: ✓ tests/test_adapts.py::test_a_client_signature_is_refused_and_the_refusal_says_why — отказ называет ADR-011, строка не записывается, статус не меняется (мутации D2 «отказ снят» и D3 «отказ перестал называть ADR» убиты); справка CLI и оба описания инструментов MCP переписаны на подпись архитектора AC-2: ✓ tests/test_adapts.py::test_the_architect_signature_alone_completes_and_verifies (одна подпись даёт approved и проходит верификацию). Negative: tests/test_renar_drift.py::test_adapt_approved_without_the_architect_signature — approved без подписи архитектора остаётся находкой, с подписью очищается (мутация D6 «approved требует отозванную роль» убита) AC-3: ✓ CHECK не сужен, миграции нет; комментарий в scripts/backend_schema_adapts.py объясняет причину (V1: сузить — значит переписать чужие записи аудита). tests/test_renar_drift.py::test_the_historical_roles_are_what_the_schema_actually_admits сверяет HISTORICAL_SIGNATURE_ROLES с ЖИВЫМ CHECK через check_domain (мутация D7 убита ПОСЛЕ разбора) AC-4: ✓ tests/test_renar_drift.py::test_a_surviving_client_signature_is_named_not_erased — находка signature-role-withdrawn, severity=warn, сообщение называет ADR-011, строки на месте (мутация D4 убита). Negative: tests/test_renar_drift.py::test_a_role_that_is_neither_current_nor_historical_is_still_invalid — чужая роль по-прежнему signature-role-invalid, и ветвь достижима на таблице БЕЗ CHECK (мутация D5 убита ПОСЛЕ разбора: прежний тест ПРОПУСКАЛСЯ) AC-5: ✓ tests/test_enum_single_source.py::test_parser_adapt_choices_derive_from_service и ::test_mcp_adapt_enums_match_service — enum MCP и choices CLI сузились сами, второй копии нет (мутация D8 «choices переписаны литералом» убита); tests/test_adapts.py::test_signature_roles_and_link_targets_closed (мутация D1 «роль client снова записываема» убита) AC-6: ✓ RENAR-CONFORMANCE.yaml регенерирован до v20 и renar/conformance.md перевыпущен; grep «dual signature|двойн» по обоим артефактам даёт 0 AC-7: ✓ docs/{ru,en}/cli.md и mcp.md, докстринги service_adapts и backend_crud_adapts; формулировка оставлена только в исторической миграции v36 (она описывает, что построила); полный прогон ленты, mypy, ruff, bootstrap --check, renar export --check; мутации 8/8; CHANGELOG в обоих файлах с объявленным отклонением от плана отката (миграции нет и почему) Domain: RENAR §7.5 (утверждение ADAPT), ADR-011 (расщепление ADAPT/ACTZ), V1 (неизменяемость записей аудита), §13.3.3 p.77 (approved с подписью архитектора).
- 2026-09-06T12:50:55Z [implementation] — ГЕЙТ РАЗМЕРА ОТКАЗАЛ НА ЗАКРЫТИИ И ПО ДЕЛУ: service_adapts.py дорос до 508 строк — мои же объяснения про отзыв нормы. Вынос сделан по существу, а не косметикой: закрытые перечни (категории находок, роли подписи, исторические роли, цели ссылок, статусы ADAPT, схема тела) переехали в новый scripts/adapt_closed_lists.py — это ОБЪЯВЛЕНИЯ, которыми распоряжается стандарт, тогда как service_adapts есть поведение. service_adapts РЕЭКСПОРТИРУЕТ их, поэтому ни один из двух десятков импортов не тронут. Размеры после выноса: 467 и 68 строк. ОХРАНА ВТОРОЙ КОПИИ СРАБОТАЛА СРАЗУ И ПО ДЕЛУ: test_no_second_literal_list_of_finding_categories покраснел, потому что разрешающий список называл scripts/service_adapts.py как источник, а источник переехал — запись исправлена на новый файл с причиной. Гейт области отказал ЧЕТВЁРТЫЙ раз за задачу (новый модуль не в ACL) и снова верно.
- 2026-09-06T12:53:09Z [implementation] — AC-1: ✓ tests/test_adapts.py::test_a_client_signature_is_refused_and_the_refusal_says_why — отказ называет ADR-011, строка не записывается, статус не меняется (мутации D2 «отказ снят» и D3 «отказ перестал называть ADR» убиты); справка CLI и оба описания инструментов MCP переписаны на подпись архитектора AC-2: ✓ tests/test_adapts.py::test_the_architect_signature_alone_completes_and_verifies (одна подпись даёт approved и проходит верификацию). Negative: tests/test_renar_drift.py::test_adapt_approved_without_the_architect_signature — approved без подписи архитектора остаётся находкой, с подписью очищается (мутация D6 «approved требует отозванную роль» убита) AC-3: ✓ CHECK не сужен, миграции нет; комментарий в scripts/backend_schema_adapts.py объясняет причину (V1: сузить — значит переписать чужие записи аудита). tests/test_renar_drift.py::test_the_historical_roles_are_what_the_schema_actually_admits сверяет HISTORICAL_SIGNATURE_ROLES с ЖИВЫМ CHECK через check_domain (мутация D7 убита ПОСЛЕ разбора) AC-4: ✓ tests/test_renar_drift.py::test_a_surviving_client_signature_is_named_not_erased — находка signature-role-withdrawn, severity=warn, сообщение называет ADR-011, строки на месте (мутация D4 убита). Negative: tests/test_renar_drift.py::test_a_role_that_is_neither_current_nor_historical_is_still_invalid — чужая роль по-прежнему signature-role-invalid, и ветвь достижима на таблице БЕЗ CHECK (мутация D5 убита ПОСЛЕ разбора: прежний тест ПРОПУСКАЛСЯ) AC-5: ✓ tests/test_enum_single_source.py::test_parser_adapt_choices_derive_from_service и ::test_mcp_adapt_enums_match_service — enum MCP и choices CLI сузились сами, второй копии нет (мутация D8 «choices переписаны литералом» убита); tests/test_adapts.py::test_signature_roles_and_link_targets_closed (мутация D1 «роль client снова записываема» убита) AC-6: ✓ RENAR-CONFORMANCE.yaml регенерирован до v20 и renar/conformance.md перевыпущен; grep «dual signature|двойн» по обоим артефактам даёт 0 AC-7: ✓ docs/{ru,en}/cli.md и mcp.md, докстринги service_adapts и backend_crud_adapts; формулировка оставлена только в исторической миграции v36 (она описывает, что построила); полный прогон ленты, mypy, ruff, bootstrap --check, renar export --check; мутации 8/8; CHANGELOG в обоих файлах с объявленным отклонением от плана отката (миграции нет и почему) Domain: RENAR §7.5 (утверждение ADAPT), ADR-011 (расщепление ADAPT/ACTZ), V1 (неизменяемость записей аудита), §13.3.3 p.77 (approved с подписью архитектора).
