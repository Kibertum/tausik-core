---
slug: volna-roya-sessii-117-verifitsirovannye-nahodki-po-7
title: "Волна роя сессии #117: верифицированные находки по 7 задачам релиза 1.8"
type: context
tags:
  - audit
  - release-1.8
  - security
  - session-117
  - swarm
task: null
edges: []
---

Семь read-only агентов. Ниже — только то, что я ПЕРЕПРОВЕРИЛ лично открытием кода; остальное см. в задачах.

БЕЗОПАСНОСТЬ, срочное. skill_activate обходит всю защиту установки: check_skill_signature имеет РОВНО ОДНУ точку вызова — skill_manager.py:301 (путь install). service_skills.py:119-133 (путь activate) делает copytree без проверки подписи И без ignore-фильтра, который в install вырезает hooks/, .claude-plugin/, CLAUDE.md. _find_vendor_skill:91-97 находит скилл по одному наличию SKILL.md в любом vendor-репо, манифест не читает, os.listdir без сортировки (first-wins, перехват имени). Через MCP activate доступен агенту напрямую и force не требует. Починка дешёвая: позвать верификатор + вынести готовый фильтр skill_manager.py:254-266 в общую функцию. Плюс skills.json: 4 из 5 внешних скиллов на ref=main (mutable), один на теге.

НАРРАТИВ. README противоречит коду в трёх проверенных местах: README.md:104 «Both are fail-closed» против verify_receipt_check.py:39-41 (except Exception -> return True, пропускает); README.md:82 «No --force» против существующего task start --force; README.md:7 «hard gates it physically cannot skip» против handlers.py:593 tausik_gates_disable, доступного агенту как обычный тул. Внутренний слой доков (architecture.md, research/failclosed-gates-audit.md) при этом ЧЕСТЕН — расходится только витрина. Итого 9 правок, 8 из них в двух файлах README.

ЁМКОСТЬ РОЯ. 41 открытая задача: 4 simple / 28 medium / 9 complex, фильтр делегирования (<=medium) проходят 32. НО acceptance_criteria есть ровно у ОДНОЙ задачи (kb-export-global). Настоящий потолок роя — не complexity, а отсутствие AC: по QG-0 остальные 40 нельзя стартовать. У 9 делегируемых не объявлен scope, и это НЕ формальность: scope_write_gate.py:165-166 снимает ACL ГЛОБАЛЬНО — одна активная задача без scope_paths открывает запись всем воркерам волны. kb-docs-map и kb-docs-swarm объявляют scope как весь docs, запирая 5 задач в один кластер.

MCP-ДЕПРЕКАЦИИ: нагрузка нулевая. Ноль употреблений sampling/createMessage/roots/list/set_logging_level/elicit во всём дереве .py (единственное совпадение — «content-head sampling» про выборку байт). Диагностика уже на stderr. ВАЖНО: критерий приёмки №3 у gmcp-spike-roots уже содержит отрицательную ветку («если roots не поддержан — зафиксировать fallback»), поэтому депрекация роадмап не ломает, а отвечает на вопрос спайка. l26-roots-premise-fix — редактура, complexity medium завышена. Премиса SEP-2577 в репозитории НЕ подтверждается ничем: ни спеки, ни research-дока. Задача «исправить премису» сама стоит на непроверенной премисе.

ТОКЕН-СТОИМОСТЬ ТУЛОВ: 117 тулов (не 150/190), 45507 симв. с префиксом, ОЦЕНКА ~13k токенов ±20-25% (точного замера нет, нужен count_tokens с ключом). 57% бюджета — inputSchema, не описания, поэтому ужимать описания бессмысленно (потолок косметики ~9%). Главное: deferred loading ЦЕЛИКОМ КЛИЕНТСКИЙ, серверу менять нечего — mcp 1.27.0 уже поддерживает ListToolsResult/курсор. Побочный баг: скиллы ссылаются на несуществующий tausik_memory_quick (harness/skills/task/SKILL.md:55, variants/model/sonnet.md:28, docs/{ru,en}/shared-brain.md:243).

КОНФИГ: три расхождения. R1 doctor строит ожидаемый CLAUDE.md из load_config() (слитые тиры), а генератор — из load_bootstrap_config() (сырой файл): один коммит даёт разный вердикт на разных машинах. R2 подпись гейтов считается из живого конфига дважды и нигде не хранится — смена тира между verify и task done блокирует закрытие с сообщением про не тот файл. R3 risk_compute делит вмороженный числитель на живой знаменатель. Кэширования конфига в памяти НЕТ вообще (grep по lru_cache/functools.cache пуст) — все три про пересчёт в двух моментах времени. conftest.py:69-80 обнуляет трастовые тиры во ВСЁМ прогоне, из-за чего класс ошибок тестами неотличим от корректного поведения.

EMBEDDINGS: brainh-semantic-search в эпике brain-hardening, в 1.8 НЕ входит. Реализации embeddings нет, только FTS5+bm25; ChromaDB выпилен четырьмя закрытыми задачами. Главное: kb-brain-deprecate (в 1.8) сносит brain-сервер, поверх которого родитель собирался строить поиск — под родителем разбирают фундамент.

ДОКИ: 51 файл ru / 50 en, agent-contract.md без EN-пары, 3 пары намеренно сокращены под skip-маркером. Гейта на translation drift НЕТ — audit_translation_drift.py существует, но в CI не вызывается ни разу (грep по .github/ пуст), сравнивает только структуру. Правило для роя: пара ru+en = один владелец. cli.md, mcp.md и architecture.md — точки сбора всех зон, идут отдельной фазой последними. docs/_generated/constants.json правит только генератор, руками не трогать.

УСТАРЕЛО: prompt.md:19-24 фиксирует объём релиза как 20+15=35 задач, фактически 23+18=41 после вчерашней реструктуризации. i18n-strategy.md:20 говорит «13 файлов» при фактических 50.
