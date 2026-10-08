# План версий: экономия TAUSIK 1.11 в Claude Code, Kilo/GLM и Codex

<!-- doc-map: reader=maintainer; zone=research -->

**Статус: утверждено владельцем 1 октября 2026, решение #410.** Локальный состав и GitHub синхронизированы; обратная сверка всех 85 исходных тикетов прошла. Созданы 8 недостающих продуктовых тикетов и 3 группирующих: всего 96 открытых, из них 16 в 1.11 (13 задач и 3 группы). Все 13 задач связаны с GitHub через tracker refs. GitLab не изменён. Исторический slug draft-эпика сохранён ради ссылок. ROADMAP.md выпущен штатным генератором; решение #411 явно связывает состав с утверждённым charter #410.

Запланированы 13 продуктовых задач для 1.11: 6 новых и 7 переиспользованных. Отдельная административная задача фиксирует синхронизацию roadmap после утверждения. Цель — измеримая экономия на принятой задаче при сохранении качества. По уточнению владельца обязательны Claude Code, Kilo Code с GLM и Codex; основной количественный полигон — Codex. Cursor/OpenRouter включаются через общее ядро и ограниченную дополнительную адаптацию.

Группы GitHub: [измерения #203](https://github.com/Kibertum/tausik-core/issues/203), [контекст и workflow #204](https://github.com/Kibertum/tausik-core/issues/204), [приёмка #205](https://github.com/Kibertum/tausik-core/issues/205). Первая задача: [общий контракт наблюдений #195](https://github.com/Kibertum/tausik-core/issues/195).

Проверки планирования: цели/AC/шаги/откат/области файлов заданы для всех 13 задач; зависимости без циклов; ранние улучшения Codex не ждут GLM, но GLM обязателен для выпуска. Формальное закрытие административной работы пока не прошло общий verify: запуск #3227 выявил несовпадение области проверки с изменёнными файлами и bootstrap drift шести развёрнутых копий `tausik_version.py`. Проверки не отключались; продуктовая экономия ещё не реализована и не измерена.

| Версия | Вопрос версии | Граница |
|---|---|---|
| 1.10.x | Исправен ли уже опубликованный релиз? | Текущая правка публичного snapshot/CI; сверка обещаний GitLab #10. Сайт остаётся отдельным незавершённым обещанием 1.10, не растворяется в 1.11. |
| **1.11** | **Можно ли выполнять ту же работу дешевле без потери проверяемого качества?** | Общее ядро экономии; Claude Code, Kilo/GLM и Codex обязательны. Cursor/OpenRouter — ограниченная совместимость без задержки релиза. |
| 1.12, кандидат | Можно ли доверять памяти между задачами и проектами? | Идентичность, отмена/происхождение, поиск и бенчмарк, lint, затем релевантность/консолидация; небольшие улучшения рабочего процесса. |
| 1.13, кандидат | Чем подтверждаются наши обещания вовне? | TC/P8, внешние проверки, RENAR first-party при выполненных предпосылках, квитанции и ограниченное продвижение. |
| 2.0 | Можно ли ставить и обновлять TAUSIK один раз для многих проектов? | Пакет, пути/реестры хостов, изоляция и version skew, миграция, затем расширение. Удалённый транспорт требует отдельного решения, не следует автоматически из локальной глобальной установки. |
| Planning | Какие гипотезы пока не заслужили места в версии? | Альтернативный backend, граф кода, майнинг истории и другие исследования без доказанного выигрыша. |

Для 1.12/1.13 это распределение кандидатов и порядок приоритетов, не обещание выпустить весь накопленный список одним релизом. Даты не назначаются до утверждения состава и уточнения результатов 1.11.

## Основания и проверка прежнего плана

Проверены все 83 открытые локальные записи на момент снимка (включая эту работу по планированию и параллельно активное исправление), все 85 открытых GitHub issues, описания четырёх milestones, последние изменённые issues и все 18 issues GitLab с обсуждением #10. Снимки API и исходных локальных записей сохранены только локально в `.tausik/planning/release-111/`. Полное распределение — в приложениях ниже; по нему ни одна исходная запись не потеряна.

1. GitHub 1.11 содержит **49 кандидатов**, а описание milestone прямо говорит, что это не состав. Основные темы — память и внешняя деятельность. Принять всё и добавить экономию сверху означало бы лишить версию фокуса.
2. [GitHub #193](https://github.com/Kibertum/tausik-core/issues/193), создан 01.10: нативный учёт токенов/кэша/лимитов Codex. Совпадает с уже заведённой задачей baseline: переиспользуем, не создаём дубль. Отдельно учитываем неверную идентификацию модели и отсутствие потребительских скриптов.
3. [GitHub #194](https://github.com/Kibertum/tausik-core/issues/194), создан 01.10: проверка реального enforcement через patch/shell/code-mode и отражение результата в doctor. Это **запрос на проверку возможностей**, не уже доказанный обход защиты. В API title/body содержат буквальные `?` вместо части кириллицы. После утверждения предлагаем восстановить понятное английское описание; оригинал сохранён в локальном снимке.
4. [GitLab #10](https://gitlab.yumash.ru/kibertum/clients/kibertum/standards/tausik/core/-/issues/10) — единственный открытый тикет, создан в августе. Новых открытых нет; #8, #11 и #18 закрыты 30.09. Патчи 0001–0003 уже разобраны в обсуждении. Для 0004 задача `scope-gate-baseline-never-moves-after-first-start` фиксирует решение через git-anchor и необходимость сообщить потребителю после 1.10. Сверить поставку и удаление патчей; не переизобретать дефект в 1.11 и не закрывать автоматически.
5. `memory-tail-by-relevance-not-recency` (#125) требует пока отсутствующих счётчиков обращений к записям, слоёв памяти и обратимой гигиены. Его текущие AC не сокращают контекст автоматически. Это 1.12; ограниченный пакет контекста 1.11 не должен зависеть от полной переработки памяти.
6. `cold-start-drill`, `read-lever-chosen-and-measured`, перепроверка формы ответов и сокращение бессодержательных тестов полезны для 1.11, поэтому переиспользованы. Исторические метрики Claude не выдаются за baseline Codex/GLM.
7. Задача о миграциях всё ещё опиралась на старый прогноз схемы 47→55. Цель сохранена, AC уточнены до реальных миграций 1.11 и проверяемого восстановления. Большой общий рефакторинг хостов из 2.0 не является предварительным условием небольших адаптеров 1.11.
8. `MCP-first versus skills-over-CLI` — ограниченное сравнение одинаковых операций в основных хостах. Решение принимает измерение, не отраслевой лозунг. До отдельного решения MCP-first сохраняется.

## Контракт универсальности

Разделяем четыре оси: **хост → провайдер → модель → тип оплаты**. Codex — хост; GLM — семейство моделей. Одна и та же модель через другой хост может иметь другой формат журнала, hooks и доступность лимитов.

Общее ядро: нормализация usage, идентичность события, атрибуция задачи, бюджеты контекста, пакет задачи, проверка и доказательства. Адаптер хоста: обнаружение сессии, чтение доступного интерфейса/журнала, формат событий, загрузка инструкций и наблюдаемые права. Тариф/квота — отдельный необязательный источник с датой и свежестью.

- Вход включает кэшированный вход там, где так устроен источник; reasoning не складывается повторно с output. Семантику cache-write адаптер объявляет явно.
- Неизвестный host/model не превращается в Claude. Настроенная модель и наблюдаемая модель различаются; старое имя тарифа не считается свежим подтверждением подписки.
- API-стоимость, реальные токены и процент общей подписной квоты — разные поля и отчёты. Суммарная квота не приписывается одному проекту при параллельной работе.
- Если данных нет, показывается «не измерено» со временем последнего измерения. Недоступная квота не блокирует кодирование и не изображается нулём.
- Никаких пользовательских сообщений, ключей или полных транскриптов в публичной проекции/тикетах; собираются необходимые локальные счётчики и происхождение.
- Новые модели добавляются данными, не ветвями бизнес-логики. Автоматическое понижение модели в 1.11 не включается: сначала экономия на том же качестве модели.

**Основные хосты подтверждены владельцем: Claude Code, Kilo Code (GLM) и Codex.** Для GLM исходная интеграция — Kilo; прямой z.ai и OpenRouter различаются как провайдеры и не наследуют тарифы/лимиты друг друга. Формат API не гарантирует доступность тех же полей из хоста: это проверяется в адаптерной задаче.

| Уровень | Что входит в 1.11 | Приёмка |
|---|---|---|
| Общее ядро | Пакет задачи, компактные инструкции и ответы, операции workflow, нормализация usage и capabilities | Единые контрактные проверки; настройки модели/провайдера не меняют бизнес-логику |
| Claude Code, Kilo/GLM, Codex | Обязательная адаптация; использование существующих механизмов Claude, а не переписывание их заново | Живой lifecycle, usage при наличии источника, проверки отказов и восстановление на каждом хосте |
| Cursor | Общие улучшения через существующую интеграцию; тонкий адаптер только при доступном интерфейсе | Smoke-проверка реально доступных функций; неизвестное enforcement/usage явно отмечено |
| OpenRouter | Провайдерный адаптер нормализует доступные usage/model/provider поля через выбранный хост | Контрактные fixtures; живая сверка только при доступной рабочей связке. Не обещается квота подписки или управление hooks провайдером |

На **всю дополнительную** проверку и тонкую адаптацию Cursor/OpenRouter предлагается максимум **25 вызовов инструментов сверх основной оценки**. Это ограничение расширения охвата, не лимит исправления дефектов основных трёх хостов. Если нужны reverse engineering, собственный extension/proxy, новый транспорт или глубокая переработка — остановить дополнительную интеграцию, записать пробел и вынести задачу в Planning/2.0. Релиз 1.11 от неё не зависит. Полная матрица всех хостов со всеми провайдерами не требуется.

Официальные источники, проверенные 01.10.2026: [z.ai cache](https://docs.z.ai/guides/capabilities/cache) описывает `usage.prompt_tokens_details.cached_tokens`; [z.ai Kilo integration](https://docs.z.ai/devpack/tool/kilo) описывает подключение провайдера. Эти документы не являются доказательством живой интеграции TAUSIK. [OpenAI pricing](https://learn.chatgpt.com/docs/pricing) отдельно описывает влияние модели, контекста, инструментов и кэша на лимиты.

## Состав 1.11 и порядок выполнения

У всех 13 задач в БД есть цель, проверяемые AC с негативными сценариями, область работ, откат, три шага, бюджет вызовов инструментов, явные scope_paths и relevant_files. Новые имена файлов в relevant_files — запланированные точки реализации, не утверждение об уже существующем коде; при уточнении решения список обновляется до записи. Состав утверждён решением #410. Административные задачи вынесены в отдельную историю вне 13 продуктовых задач.

| № | Задача | Результат приёмки | Бюджет вызовов |
|---|---|---|---:|
| 1 | `r111-runtime-observation-contract` — новая | Общие поля host/provider/model/usage; неизвестное остаётся неизвестным; regression Claude | 60 |
| 2 | `1-11-establish-a-codex-usage-baseline-that-can` — существующая, #193 | Native Codex, инкрементальный учёт, дельты, свежесть лимитов; замороженные корпус и baseline | 90 |
| 3 | `r111-glm-host-usage-adapter` — новая | GLM через выбранный хост в тот же ledger; реальная сверка и честные ограничения | 90 |
| 4 | `r111-live-enforcement-capabilities` — новая, #194 | Doctor различает установку и доказанный отказ до записи; доступные маршруты записи в трёх основных хостах | 100 |
| 5 | `mcp-first-rule-versus-skills-over-cli` — существующая, #130 | Ограниченный сравнительный замер и решение; одинаковые гарантии | 40 |
| 6 | `r111-budgeted-context-package` — новая | Короткие постоянные инструкции + нужный контекст задачи; без потери правил и AC | 90 |
| 7 | `r111-compound-workflow-results` — новая | Меньше обращений модели, те же проверки, явные частичные ошибки | 90 |
| 8 | `read-lever-chosen-and-measured` — существующая | Один выбранный рычаг чтения с замером и решением сохранить/откатить | 60 |
| 9 | `cold-start-drill` — существующая, #150 | Восстановление после прерывания без рукописного спасательного промпта; устаревшая проверка не принимается | 60 |
| 10 | `test-suite-is-cut-to-what-guards-behaviour` — существующая | Удаление/объединение бессодержательных проверок с картой сохранённых гарантий | 90 |
| 11 | `answer-rules-remeasured-after-three-sessions` — существующая | Проверка формы ответов отдельно по хостам без потери существенных выводов | 25 |
| 12 | `schema-migrations-of-the-release-run-as-one-campaign` — существующая, #156 | Только реальные миграции 1.11, безопасный upgrade и обратный путь | 45 |
| 13 | `r111-cross-host-economy-acceptance` — новая | Парное сравнение Codex; живые Claude Code и Kilo/GLM; сохранённое качество и явные границы Cursor/OpenRouter | 120 |

**Порядок с ранней экономией:** 1 → 2 → 4 → 6 → 5 → 7. После первого сокращения контекста/workflow идут 3, 8, 10 и 11; затем 9. Задача 12 после контракта 1 проверяет только реально возникающие миграции. Все результаты сходятся в 13; финальная приёмка также ждёт устранения дефекта публичного snapshot 1.10.x. Реализация общих механизмов начинается с Codex, живые проверки Claude/Kilo обязательны до релиза. Граф зависимости не заставляет ждать адаптера GLM перед первым полезным улучшением Codex.

### Как двигаться при критическом недельном лимите

1. **Минимальный замер:** общий формат и нативные счётчики Codex. Сначала сверка офлайн с журналом, затем наблюдение за полезной текущей задачей. Не строить dashboard, общий plugin registry или новую систему тарифов.
2. **Первый эффект:** уменьшить постоянный контекст и убрать повторные служебные обращения. Каждый рычаг проверяется отдельно на той же модели; принятый эффект сразу используется в dev-профиле TAUSIK. В потребительские проекты он попадает через проверенный артефакт обновления, без ручных вечных патчей и без неразрешённой публикации.
3. **Распространение:** после первого выигрыша довести общие изменения до Claude Code и Kilo/GLM, проверить восстановление и upgrade. Cursor/OpenRouter остаются в дополнительном лимите 25 вызовов.
4. **Приёмка и релиз:** независимые проверки, bounded comparison и публичный snapshot. Полная лента — на согласованной контрольной точке/релизе; после каждого небольшого изменения только релевантные проверки и обязательные gates. Изменение входов аннулирует старую проверку.

Рабочий режим: один исполнитель и одна задача, независимый ревьюер только по требованию риска/правил; не копировать полную историю в параллельные агенты по умолчанию. Новый контекст — на границе задачи после сохранённой передачи состояния, если старый стал нерелевантным; не сбрасывать его по таймеру. Не повторять полное обследование проекта, когда задача уже содержит проверенные пути/AC. Не добавлять улучшения вне состава в текущий проход.

960 вызовов — оценка объёма реализации, **не разрешение потратить их заранее**. По каждому завершённому этапу сравнивать фактический расход и полезный результат. При повторном одинаковом отказе сначала фиксировать причину и менять подход, а не циклически повторять verify. Ужесточение бюджетов включать только на корректном учёте; экономить выключением доказательств запрещено.

До изменения контекста замораживается корпус/протокол в задаче 2. Базовые cold-start сценарии включаются в этот протокол и воспроизводятся на сохранённой исходной версии, даже если итоговая задача 9 выполняется позже. Нельзя после реализации придумать удобную базовую линию.

Сумма исходных ориентиров — **960 вызовов** для продукта; до **25 дополнительных** на Cursor/OpenRouter, ещё **35** на публикационную сверку после утверждения. Это первоначальная оценка работы агентов; не долларовая цена, не число обращений модели и не срок в днях. После начального обследования уточняется стоимость живой приёмки трёх хостов; число 960 не является обещанием неизменной цены расширенного охвата. Сначала измеряем Codex, существующую Claude-интеграцию сохраняем и проверяем, Kilo/GLM подключаем через тот же контракт. Приёмка требует все три основных хоста.

## Проверка экономии и качества

Предлагаемый ориентир: **не менее 30% снижения медианы суммарных измеренных токенов на принятую задачу Codex**, на фиксированной модели/effort/speed, при отсутствии регрессий на независимом корпусе. Это инженерный критерий на ограниченной выборке, не обещание экономии недельной квоты на 30% и не универсальная статистическая гарантия.

Отдельно публикуются обычный/кэшированный вход, выход, число обращений модели и инструментов, p90, сложность задач, качество, переделки, ревью, продолжительность и доля неизвестных данных. Общий total не скрывает перехода от дешёвого кэшированного входа к дорогому выходу. Если более экономный total противоречит измеренному расходу квоты/стоимости, подписная экономия не заявляется.

Сначала офлайн-сверка счётчиков и короткий пилот. Затем, только с объявленным бюджетом измерения, Codex: 6 задач, по 2 каждой сложности, 2 повтора каждой стороны — 24 выполнения. Kilo/GLM и Claude Code: по 3 парных кейса разных сложностей — по 6 выполнений, плюс живые сценарии жизненного цикла и отказов. Это 36 основных выполнений; Cursor/OpenRouter не получают отдельный полный benchmark в 1.11. Пользовательские задачи не повторяются в их рабочих деревьях. Эффект сравнивается внутри каждого провайдера; токенизаторы и тарифы не усредняются между моделями.

Проверки качества фиксируются до оптимизации: поведенческие AC, отрицательные сценарии QG-0/QG-2, stale evidence, upgrade/restore, public snapshot и холодное восстановление. Итог включает все неуспешные попытки и повторные работы. Бюджет не разрешает отключать проверки. Если цель не достигнута — уменьшаем/откатываем изменение или выносим владельцу новый состав с честными результатами.

## Что перенести и почему

- **1.12:** память как связная последовательность: безопасность локального/общего хранилища и identity → supersession и retrieval-first → измеряемый поиск/lint → слои/консолидация. Нынешний #125 сначала требует данных обращений; `core-memory-block` и `memory-tail` не должны стать двумя конкурирующими механизмами без одного решения. Небольшие задачи blocked/rename/commit/friction допускаются после основного контура, не как расширение 1.11.
- **1.13:** TC/P8 и внешние доказательства. Независимые проверочные кейсы 1.11 не требуют внедрять весь жизненный цикл TC/P8. RENAR first-party возможен только с замороженным концептом и подписью; не обещаем сертификат или соответствие автоматически. Публичные заявления проверяются до публикации; маркетинговые тикеты не становятся блокерами экономии.
- **2.0:** сохраняется общий смысл глобальной установки. `gmcp-packaging`, `v2-engine-standalone-package`, `pypi-package-uvx-tausik-init` — пересекающиеся грани одной поставки; нужен единый результат, не три независимые реализации. Аналогично plugin/import/export/signing и клиентское расширение зависят от базового пакета и проверенного bootstrap. Полная изоляция агентов и ownership (#151/#152) относится к общему runtime; корректные идентификаторы usage 1.11 не требуют закончить эту архитектуру.
- **Planning:** #60 каталог, #63 Outline, #99 дополнительные антирационализационные тексты, #100–103 исследования и #80 административная разборка сирот. Исследование не удалено, но не обещано датированной версией без bounded spike и критерия остановки. Сверка сирот частично выполнена этим отчётом; закрытие #80 требует утверждённого распределения, не просто таблицы кандидатов.

## Предложение по GitHub после утверждения

Текущие 85 открытых issues: 49 в 1.11, 32 в 2.0, 2 в 1.10, 2 без milestone. Предложение для **этих же** issues: 5 в 1.11, 23 в 1.12, 13 в 1.13, 34 в 2.0, 8 Planning, 2 в 1.10. Всего **48 изменений milestone**; остальные 37 остаются на месте. Новые issues для задач draft-состава в эти числа ещё не входят.

После утверждения:

1. Записать решение о составе и проверить фактические изменения с момента снимка. Перегенерировать ROADMAP.md штатной командой из данных; не переписывать вручную и не заменять историю 1.10 задним числом.
2. Обновить описание 1.11, создать 1.12/1.13 как кандидатные milestones и применить таблицу ниже. У 1.10 описание всё ещё ссылается на старые #376/#378 — привести к фактической истории/оставшемуся сайту, не закрывать milestone автоматически.
3. Переиспользовать #193, #194, #130, #150, #156; создать **8** недостающих продуктовых issues и до **3** групповых issues для трёх draft-историй. Не создавать отдельный дубль baseline поверх #193. Административная задача синхронизации не является продуктовым обещанием релиза.
4. Для #194 предложен заголовок `Codex: verify live hook enforcement across patch, shell and code-mode in doctor`; новое тело взять из AC задачи `r111-live-enforcement-capabilities`, обозначив восстановление повреждённого текста. Не утверждать недоказанный bypass.
5. Обновить групповые #169/#170 под 1.12/1.13, сохранив ссылки и историю. Не закрывать исходные тикеты только потому, что они перенесены. Дата `updated_at` и исходные значения хранятся в manifest для обнаружения конфликтов/отката.
6. GitLab #10: отдельный короткий ответ с проверенными release/commit и инструкцией снятия 0004, затем закрытие только при подтверждённой поставке/выполнении обещания. Это отдельное внешнее действие, не подразумеваемая часть одного лишь переноса GitHub milestones.

Исполнительная запись: `roadmap-sync-after-version-plan-approval`. Решение #410 разрешило согласованную синхронизацию GitHub; снимок до неё перепроверен, конфликтующих изменений нет. GitLab #10 остаётся отдельным действием. Итоговые номера созданных issues и read-back проверка записываются в журнал этой задачи.

## Приложение A. Полная карта существующих GitHub issues

| Issue | Previous milestone | Proposed milestone | Task |
|---|---|---|---|
| [#37](https://github.com/Kibertum/tausik-core/issues/37) | v2.0.0 | v2.0.0 | v2-mcp-request-time-db-routing |
| [#38](https://github.com/Kibertum/tausik-core/issues/38) | v2.0.0 | v2.0.0 | v2-elicitation-input-required-with-request-state |
| [#39](https://github.com/Kibertum/tausik-core/issues/39) | v2.0.0 | v2.0.0 | v2-auth-oauth21-cloud-and-header-key-local |
| [#40](https://github.com/Kibertum/tausik-core/issues/40) | v2.0.0 | v2.0.0 | gmcp-packaging |
| [#41](https://github.com/Kibertum/tausik-core/issues/41) | v2.0.0 | v2.0.0 | gmcp-init-lite |
| [#42](https://github.com/Kibertum/tausik-core/issues/42) | v2.0.0 | v2.0.0 | gmcp-migrate-submodule |
| [#43](https://github.com/Kibertum/tausik-core/issues/43) | v2.0.0 | v2.0.0 | v2-engine-standalone-package |
| [#44](https://github.com/Kibertum/tausik-core/issues/44) | v2.0.0 | v2.0.0 | gmcp-global-hooks |
| [#45](https://github.com/Kibertum/tausik-core/issues/45) | v2.0.0 | v2.0.0 | gmcp-version-skew |
| [#46](https://github.com/Kibertum/tausik-core/issues/46) | v2.0.0 | v2.0.0 | gmcp-multi-ide |
| [#47](https://github.com/Kibertum/tausik-core/issues/47) | v2.0.0 | v2.0.0 | gmcp-docs-global |
| [#48](https://github.com/Kibertum/tausik-core/issues/48) | v2.0.0 | v2.0.0 | ext-p0-derisk-spike |
| [#49](https://github.com/Kibertum/tausik-core/issues/49) | v2.0.0 | v2.0.0 | ext-p2-extension-mvp |
| [#50](https://github.com/Kibertum/tausik-core/issues/50) | v2.0.0 | v2.0.0 | ext-p4-migration-rollout |
| [#56](https://github.com/Kibertum/tausik-core/issues/56) | v2.0.0 | v2.0.0 | group issue |
| [#57](https://github.com/Kibertum/tausik-core/issues/57) | v2.0.0 | v2.0.0 | group issue |
| [#58](https://github.com/Kibertum/tausik-core/issues/58) | v2.0.0 | v2.0.0 | group issue |
| [#59](https://github.com/Kibertum/tausik-core/issues/59) | v2.0.0 | v2.0.0 | group issue |
| [#60](https://github.com/Kibertum/tausik-core/issues/60) | v1.11.0 | Planning | v14c-skill-web-catalog |
| [#62](https://github.com/Kibertum/tausik-core/issues/62) | v1.11.0 | v1.12.0 | brainh-capture-ux |
| [#63](https://github.com/Kibertum/tausik-core/issues/63) | v1.11.0 | Planning | brainh-outline-spike |
| [#64](https://github.com/Kibertum/tausik-core/issues/64) | v2.0.0 | v2.0.0 | ext-p3-enforcement-provider-ux |
| [#65](https://github.com/Kibertum/tausik-core/issues/65) | v1.11.0 | v1.12.0 | l26-memory-decay |
| [#66](https://github.com/Kibertum/tausik-core/issues/66) | v1.11.0 | v1.12.0 | kb-global-promote |
| [#67](https://github.com/Kibertum/tausik-core/issues/67) | v1.11.0 | v1.12.0 | km-stable-identity-backfill |
| [#68](https://github.com/Kibertum/tausik-core/issues/68) | v1.11.0 | v1.12.0 | km-topics-aliases-index |
| [#69](https://github.com/Kibertum/tausik-core/issues/69) | v1.11.0 | v1.12.0 | km-retrieval-first-write-path |
| [#70](https://github.com/Kibertum/tausik-core/issues/70) | v1.11.0 | v1.12.0 | km-memory-lint-report |
| [#71](https://github.com/Kibertum/tausik-core/issues/71) | v1.11.0 | v1.12.0 | km-promote-mechanical-checks-blocking |
| [#78](https://github.com/Kibertum/tausik-core/issues/78) | v2.0.0 | v2.0.0 | v2-projection-hook-covers-every-write |
| [#80](https://github.com/Kibertum/tausik-core/issues/80) | v1.11.0 | Planning | backlog-orphans-invisible-to-roadmap |
| [#88](https://github.com/Kibertum/tausik-core/issues/88) | v1.11.0 | v1.12.0 | agent-friction-becomes-a-filed-defect-not-a-swallowed-one |
| [#89](https://github.com/Kibertum/tausik-core/issues/89) | v1.11.0 | v1.13.0 | outward-text-passes-a-forbidden-forms-gate-not-goodwill |
| [#92](https://github.com/Kibertum/tausik-core/issues/92) | v1.11.0 | v1.12.0 | shared-store-has-no-threat-model-and-no-secret-detector |
| [#93](https://github.com/Kibertum/tausik-core/issues/93) | v1.11.0 | v1.12.0 | blocked-is-a-status-without-a-question-to-unblock-it |
| [#94](https://github.com/Kibertum/tausik-core/issues/94) | v1.11.0 | v1.12.0 | memory-retrieval-has-no-published-benchmark |
| [#96](https://github.com/Kibertum/tausik-core/issues/96) | v2.0.0 | v2.0.0 | agent-plugins-import-and-export |
| [#97](https://github.com/Kibertum/tausik-core/issues/97) | v1.11.0 | v1.12.0 | memory-lint-cannot-see-an-unlinked-contradiction |
| [#98](https://github.com/Kibertum/tausik-core/issues/98) | v2.0.0 | v2.0.0 | nothing-scans-the-installed-harness-state |
| [#99](https://github.com/Kibertum/tausik-core/issues/99) | v1.11.0 | Planning | skills-do-not-anticipate-the-rationalization |
| [#100](https://github.com/Kibertum/tausik-core/issues/100) | v1.11.0 | Planning | r-capture-tool-traces-and-prove-they-answer-something |
| [#101](https://github.com/Kibertum/tausik-core/issues/101) | v1.11.0 | Planning | r-mine-history-into-memory-candidates-30-or-dead-end |
| [#102](https://github.com/Kibertum/tausik-core/issues/102) | v1.11.0 | Planning | r-code-graph-versus-fts5-on-hidden-dependencies |
| [#103](https://github.com/Kibertum/tausik-core/issues/103) | v1.11.0 | Planning | r-is-longmemeval-applicable-to-project-fact-memory |
| [#107](https://github.com/Kibertum/tausik-core/issues/107) | v1.11.0 | v1.12.0 | knowledge-locality-check-delete-the-file-and-rewrite-it |
| [#108](https://github.com/Kibertum/tausik-core/issues/108) | v1.11.0 | v1.12.0 | history-to-harness-loop-deterministic-candidates-human-verdict |
| [#110](https://github.com/Kibertum/tausik-core/issues/110) | v1.11.0 | v1.13.0 | senar-has-an-independent-implementation-and-says-nothing |
| [#111](https://github.com/Kibertum/tausik-core/issues/111) | v1.11.0 | v1.13.0 | phase-is-silent-about-a-203-star-neighbour |
| [#112](https://github.com/Kibertum/tausik-core/issues/112) | v1.11.0 | v1.13.0 | senar-window-is-one-to-two-years-institutions-are-coming |
| [#113](https://github.com/Kibertum/tausik-core/issues/113) | v2.0.0 | v2.0.0 | sign-layer-over-agent-plugins |
| [#114](https://github.com/Kibertum/tausik-core/issues/114) | v1.11.0 | v1.13.0 | intoto-predicate-work-closure |
| [#115](https://github.com/Kibertum/tausik-core/issues/115) | v2.0.0 | v2.0.0 | pypi-package-uvx-tausik-init |
| [#116](https://github.com/Kibertum/tausik-core/issues/116) | v2.0.0 | v2.0.0 | claude-code-plugin-and-catalog-listing |
| [#117](https://github.com/Kibertum/tausik-core/issues/117) | v1.11.0 | v1.13.0 | tausik-verify-github-action-badge |
| [#119](https://github.com/Kibertum/tausik-core/issues/119) | v1.11.0 | v1.13.0 | pr-into-awesome-harness-engineering |
| [#122](https://github.com/Kibertum/tausik-core/issues/122) | v2.0.0 | v2.0.0 | ratchet-for-mcp-cli-surface-parity |
| [#125](https://github.com/Kibertum/tausik-core/issues/125) | v1.11.0 | v1.12.0 | memory-tail-by-relevance-not-recency |
| [#127](https://github.com/Kibertum/tausik-core/issues/127) | v1.11.0 | v1.12.0 | weighted-links-and-recallable-reasoning-chains |
| [#129](https://github.com/Kibertum/tausik-core/issues/129) | v1.11.0 | v1.12.0 | epistemic-overview-what-this-project-knows |
| [#130](https://github.com/Kibertum/tausik-core/issues/130) | v1.11.0 | v1.11.0 | mcp-first-rule-versus-skills-over-cli |
| [#131](https://github.com/Kibertum/tausik-core/issues/131) | v2.0.0 | v2.0.0 | package-skills-and-mcp-as-one-plugin |
| [#132](https://github.com/Kibertum/tausik-core/issues/132) | v1.11.0 | v1.13.0 | p8-the-test-author-is-not-the-implementer |
| [#133](https://github.com/Kibertum/tausik-core/issues/133) | v1.11.0 | v1.13.0 | score-tausik-on-repocompliancebench |
| [#134](https://github.com/Kibertum/tausik-core/issues/134) | v1.11.0 | v1.13.0 | pdd-paper-unread-blocks-the-uniqueness-claim |
| [#135](https://github.com/Kibertum/tausik-core/issues/135) | v2.0.0 | v2.0.0 | four-byte-identical-copies-of-the-harness |
| [#136](https://github.com/Kibertum/tausik-core/issues/136) | v1.11.0 | v1.13.0 | tc-as-a-first-class-artifact-coverage-from-statements |
| [#140](https://github.com/Kibertum/tausik-core/issues/140) | v1.11.0 | v1.12.0 | nothing-can-rename-a-task-and-the-slug-is-published |
| [#144](https://github.com/Kibertum/tausik-core/issues/144) | v1.11.0 | v1.12.0 | core-memory-block-the-agent-maintains |
| [#145](https://github.com/Kibertum/tausik-core/issues/145) | v1.11.0 | v1.12.0 | memory-supersede-edges-are-data |
| [#147](https://github.com/Kibertum/tausik-core/issues/147) | v1.11.0 | v1.12.0 | commit-per-closed-task |
| [#150](https://github.com/Kibertum/tausik-core/issues/150) | v1.11.0 | v1.11.0 | cold-start-drill |
| [#151](https://github.com/Kibertum/tausik-core/issues/151) | v1.11.0 | v2.0.0 | task-ownership-is-a-dead-primitive |
| [#152](https://github.com/Kibertum/tausik-core/issues/152) | v1.11.0 | v2.0.0 | isolation-model-for-parallel-agents |
| [#153](https://github.com/Kibertum/tausik-core/issues/153) | v2.0.0 | v2.0.0 | provider-generates-artifacts-not-the-if-ide-ladder |
| [#154](https://github.com/Kibertum/tausik-core/issues/154) | v2.0.0 | v2.0.0 | four-ide-registries-collapse-into-one |
| [#155](https://github.com/Kibertum/tausik-core/issues/155) | v2.0.0 | v2.0.0 | bundled-root-separate-from-vendored-copy |
| [#156](https://github.com/Kibertum/tausik-core/issues/156) | v1.11.0 | v1.11.0 | schema-migrations-of-the-release-run-as-one-campaign |
| [#161](https://github.com/Kibertum/tausik-core/issues/161) | v2.0.0 | v2.0.0 | kilo-has-a-plugin-and-permission-surface-we-do-not-use |
| [#169](https://github.com/Kibertum/tausik-core/issues/169) | v1.11.0 | v1.12.0 | group issue |
| [#170](https://github.com/Kibertum/tausik-core/issues/170) | v1.11.0 | v1.13.0 | group issue |
| [#186](https://github.com/Kibertum/tausik-core/issues/186) | v1.11.0 | v1.13.0 | renar-first-party-confirmation-is-available |
| [#188](https://github.com/Kibertum/tausik-core/issues/188) | v1.10.0 | v1.10.0 | group issue |
| [#189](https://github.com/Kibertum/tausik-core/issues/189) | v1.10.0 | v1.10.0 | site-is-rebuilt-from-the-core-docs-of-the-release |
| [#193](https://github.com/Kibertum/tausik-core/issues/193) | no milestone | v1.11.0 | 1-11-establish-a-codex-usage-baseline-that-can |
| [#194](https://github.com/Kibertum/tausik-core/issues/194) | no milestone | v1.11.0 | r111-live-enforcement-capabilities |

## Приложение B. Все исходные открытые локальные задачи

Таблица относится к снимку перед созданием шести новых продуктовых и одной административной задачи. Новые записи перечислены выше. Утверждённое распределение применено к локальным историям; состав 1.12/1.13 остаётся кандидатным, отдельные задачи перед исполнением потребуют актуализации.

| Task | Original status | Proposed version |
|---|---|---|
| `public-snapshot-tests-read-excluded-files` | active | 1.10.x corrective release |
| `backlog-orphans-invisible-to-roadmap` | planning | Planning |
| `brainh-outline-spike` | planning | Planning |
| `r-capture-tool-traces-and-prove-they-answer-something` | planning | Planning |
| `r-code-graph-versus-fts5-on-hidden-dependencies` | planning | Planning |
| `r-is-longmemeval-applicable-to-project-fact-memory` | planning | Planning |
| `r-mine-history-into-memory-candidates-30-or-dead-end` | planning | Planning |
| `skills-do-not-anticipate-the-rationalization` | planning | Planning |
| `v14c-skill-web-catalog` | planning | Planning |
| `prepare-a-cross-host-release-plan-focused-on` | active | Planning administration |
| `site-is-rebuilt-from-the-core-docs-of-the-release` | blocked | v1.10.0 |
| `1-11-establish-a-codex-usage-baseline-that-can` | planning | v1.11.0 |
| `answer-rules-remeasured-after-three-sessions` | planning | v1.11.0 |
| `cold-start-drill` | planning | v1.11.0 |
| `mcp-first-rule-versus-skills-over-cli` | planning | v1.11.0 |
| `read-lever-chosen-and-measured` | planning | v1.11.0 |
| `schema-migrations-of-the-release-run-as-one-campaign` | planning | v1.11.0 |
| `test-suite-is-cut-to-what-guards-behaviour` | planning | v1.11.0 |
| `agent-friction-becomes-a-filed-defect-not-a-swallowed-one` | planning | v1.12.0 |
| `blocked-is-a-status-without-a-question-to-unblock-it` | planning | v1.12.0 |
| `brainh-capture-ux` | planning | v1.12.0 |
| `commit-per-closed-task` | planning | v1.12.0 |
| `core-memory-block-the-agent-maintains` | planning | v1.12.0 |
| `epistemic-overview-what-this-project-knows` | planning | v1.12.0 |
| `history-to-harness-loop-deterministic-candidates-human-verdict` | planning | v1.12.0 |
| `kb-global-promote` | planning | v1.12.0 |
| `km-memory-lint-report` | planning | v1.12.0 |
| `km-promote-mechanical-checks-blocking` | planning | v1.12.0 |
| `km-retrieval-first-write-path` | planning | v1.12.0 |
| `km-stable-identity-backfill` | planning | v1.12.0 |
| `km-topics-aliases-index` | planning | v1.12.0 |
| `knowledge-locality-check-delete-the-file-and-rewrite-it` | planning | v1.12.0 |
| `l26-memory-decay` | planning | v1.12.0 |
| `memory-lint-cannot-see-an-unlinked-contradiction` | planning | v1.12.0 |
| `memory-retrieval-has-no-published-benchmark` | planning | v1.12.0 |
| `memory-supersede-edges-are-data` | planning | v1.12.0 |
| `memory-tail-by-relevance-not-recency` | blocked | v1.12.0 |
| `nothing-can-rename-a-task-and-the-slug-is-published` | planning | v1.12.0 |
| `shared-store-has-no-threat-model-and-no-secret-detector` | planning | v1.12.0 |
| `weighted-links-and-recallable-reasoning-chains` | planning | v1.12.0 |
| `intoto-predicate-work-closure` | planning | v1.13.0 |
| `outward-text-passes-a-forbidden-forms-gate-not-goodwill` | planning | v1.13.0 |
| `p8-the-test-author-is-not-the-implementer` | planning | v1.13.0 |
| `pdd-paper-unread-blocks-the-uniqueness-claim` | planning | v1.13.0 |
| `phase-is-silent-about-a-203-star-neighbour` | planning | v1.13.0 |
| `pr-into-awesome-harness-engineering` | planning | v1.13.0 |
| `renar-first-party-confirmation-is-available` | planning | v1.13.0 |
| `score-tausik-on-repocompliancebench` | planning | v1.13.0 |
| `senar-has-an-independent-implementation-and-says-nothing` | planning | v1.13.0 |
| `senar-window-is-one-to-two-years-institutions-are-coming` | planning | v1.13.0 |
| `tausik-verify-github-action-badge` | planning | v1.13.0 |
| `tc-as-a-first-class-artifact-coverage-from-statements` | planning | v1.13.0 |
| `agent-plugins-import-and-export` | planning | v2.0.0 |
| `bundled-root-separate-from-vendored-copy` | planning | v2.0.0 |
| `claude-code-plugin-and-catalog-listing` | planning | v2.0.0 |
| `ext-p0-derisk-spike` | planning | v2.0.0 |
| `ext-p2-extension-mvp` | planning | v2.0.0 |
| `ext-p3-enforcement-provider-ux` | planning | v2.0.0 |
| `ext-p4-migration-rollout` | planning | v2.0.0 |
| `four-byte-identical-copies-of-the-harness` | planning | v2.0.0 |
| `four-ide-registries-collapse-into-one` | planning | v2.0.0 |
| `gmcp-docs-global` | planning | v2.0.0 |
| `gmcp-global-hooks` | planning | v2.0.0 |
| `gmcp-init-lite` | planning | v2.0.0 |
| `gmcp-migrate-submodule` | planning | v2.0.0 |
| `gmcp-multi-ide` | planning | v2.0.0 |
| `gmcp-packaging` | planning | v2.0.0 |
| `gmcp-version-skew` | planning | v2.0.0 |
| `isolation-model-for-parallel-agents` | planning | v2.0.0 |
| `kilo-has-a-plugin-and-permission-surface-we-do-not-use` | planning | v2.0.0 |
| `nothing-scans-the-installed-harness-state` | planning | v2.0.0 |
| `package-skills-and-mcp-as-one-plugin` | planning | v2.0.0 |
| `provider-generates-artifacts-not-the-if-ide-ladder` | planning | v2.0.0 |
| `pypi-package-uvx-tausik-init` | planning | v2.0.0 |
| `ratchet-for-mcp-cli-surface-parity` | planning | v2.0.0 |
| `renar-11-description-set-model` | planning | v2.0.0 |
| `sign-layer-over-agent-plugins` | planning | v2.0.0 |
| `task-ownership-is-a-dead-primitive` | planning | v2.0.0 |
| `v2-auth-oauth21-cloud-and-header-key-local` | planning | v2.0.0 |
| `v2-elicitation-input-required-with-request-state` | planning | v2.0.0 |
| `v2-engine-standalone-package` | planning | v2.0.0 |
| `v2-mcp-request-time-db-routing` | planning | v2.0.0 |
| `v2-projection-hook-covers-every-write` | planning | v2.0.0 |
