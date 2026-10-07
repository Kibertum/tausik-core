[English](../en/cli-tasks.md) | **Русский**

# CLI: задачи и смены

<!-- doc-map: reader=user; zone=core-surface -->

Завести, начать, вести и закрыть работу. Часть справочника команд. Начало и рабочий набор — [cli.md](cli.md).
## Инициализация

```bash
--version                      # Напечатать установленную версию TAUSIK; проект и база не нужны
init --name <slug>             # Инициализация проекта (создаёт .tausik/tausik.db)
init --template aidd [--force] # Скаффолдит AIDD-слои (idea.md/vision.md/conventions.md) в корень проекта.
demo [--keep]                  # Посмотреть, как TAUSIK ловит ложное «тесты прошли», в одноразовой песочнице: без сети, без ключа LLM, ваш проект не трогается
                               #   Существующие файлы → 4-option prompt: overwrite / merge-append / skip / abort-all.
                               #   Default (Enter) = skip. `--force` перезаписывает без вопросов.
                               #   Неизвестное значение --template — exit ≠ 0, сообщение в stderr.
aidd autogen [--write] [--force] # Черновик vision.md, заполненный сигналами репо (имя+описание пакета,
                               #   заголовок/интро README, top-level каталоги, языки, тест-фреймворк).
                               #   По умолчанию печатает черновик в stdout (ничего не пишет); --write пишет в vision.md
                               #   через AIDD-prompt конфликтов (--force перезаписывает). Нет сигнала → placeholder,
                               #   никогда не падает. Только stdlib, без вызова LLM.
aidd validate                  # Проверяет claim'ы из conventions.md ## Code (язык/версия, lint/format, тест-фреймворк,
                               #   макс. размер файла) против реального состояния репо. Каждый claim →
                               #   ok / drift / unverifiable. Exit 1 при hard drift, 2 если нет conventions.md,
                               #   0 иначе. Пустой/непарсимый claim → unverifiable, никогда не падает. Только stdlib.
status [--compact]             # Обзор проекта + SENAR; --compact → JSON одной строкой
update-check [--now]           # Обновить кэш status/doctor (не чаще раза в сутки без --now); старт сессии всегда проверяет заново
metrics                        # Метрики SENAR: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
metrics target NAME min|max VALUE --basis "..."   # Задать цель; без --basis отказ (SENAR §9.4(c))
                                # Отчёт печатает метод, популяцию и период каждой цифры,
                                # «no population» вместо 0% при пустом знаменателе и каждую
                                # цель с основанием; пересечение пишет одно событие metric_target_crossed
metrics [--cost]               # С --cost: агрегат по usage_events по task_slug (то же что `metrics cost`)
metrics record-session         # Записать LLM usage (tokens/cost/tool/model) для текущей или явной сессии
metrics log-usage              # Одна строка manual в usage_events (--task-slug опционально; session_usage_metrics не трогаем)
metrics cost [--since ISO] [--until ISO]   # SUM токенов/cost и COUNT по task (slug NULL исключены)
metrics answers [--last N] [--json]   # Форма итоговых ответов агента: слова (медиана/p90), вердикт первой строкой %, доля списков, «вода»
metrics calls [--last N]             # Вызовы инструментов на закрытую задачу по видам (чтение/правка/запуск/скрипт/обряд/прочее), по сложности
metrics cohorts [--json]             # Естественные accepted-task когорты по версии TAUSIK и модели
metrics compare [selectors] [--json] # Сравнить две естественные когорты версии/модели/времени
metrics tokens [--host claude|codex|kilo] [--last N] [--rebuild] [--json]
                                                   # Нативный расход хоста; для Claude остаётся прежний вид по инструментам
                                # Источник: .tausik/token_metrics.jsonl — его пишет SessionEnd hook
                                #   scripts/hooks/session_metrics.py, обходя транскрипт и раскладывая
                                #   message-level usage по tool_use внутри сообщения.
                                # ГЛАВНАЯ КОЛОНКА — ctx_*: полный контекст сообщения
                                #   (input + cache_creation + cache_read). Именно она есть предмет
                                #   утверждения об экономии. Колонка in_* — НЕ вход:
                                #   при включённом кэше это неохваченный кэшем остаток, на нашем
                                #   дереве буквально 2 токена на сообщение, то есть удвоенный
                                #   счётчик вызовов.
                                # --rebuild заново выводит всю ленту из ВСЕХ транскриптов проекта
                                #   на диске. Нужен потому, что инкрементальный писатель видит лишь
                                #   транскрипт только что завершившейся сессии, и его охват бывает
                                #   куда уже реально существующей истории.
                                # Строка COVERAGE в шапке отчёта называет знаменатель: за сколько
                                #   смен из всех есть записи и с какой даты. Величина, которой в
                                #   данных нет, печатается словом «не измерено», НЕ нулём.
                                # Не путать с `metrics cost` — та считает деньги по usage_events в БД.
                                # Подробности: docs/{en,ru}/cost-telemetry.md.
doctor                         # Health check: venv + DB + MCP + skills + drift + устаревший байт-код
doctor --fix-bytecode          # Удалить РОВНО те .pyc, чей co_filename называет чужой каталог (после переезда дерева)
```

## Иерархия

```bash
epic add <slug> <title> [--description TEXT]
epic update <slug> [--title T] [--description TEXT]   # замысел группы задач можно править
epic list [--stale-over N]     # stale = задач создано после последней правки описания; отчёт, не гейт
epic list
epic done <slug> [--verify-handle H]   # закрывает эпик; с H — гасит пул-чек от
                                        # `verify --epic` атомарно (закрываются все
                                        # участники или никто; одноразовый, с TTL)
epic delete <slug>             # CASCADE: удаляет все стори + задачи

story add <epic_slug> <slug> <title> [--description TEXT]
story update <slug> [--title T] [--description TEXT]
story list [--epic E] [--stale-over N]
story list [--epic EPIC_SLUG]
story done <slug> [--verify-handle H]   # закрывает стори; с H — гасит пул-чек от
                                        # `verify --story` атомарно
story delete <slug>            # CASCADE: удаляет все задачи
```

## Задачи

```bash
task add <title> [--story STORY_SLUG] [--slug SLUG] [--stack STACK]
                 [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE]
                 [--defect-of PARENT_SLUG]
                 [--call-budget N] [--tier {trivial,light,moderate,substantial,deep}]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]    # Следующая planning-задача: сначала объявленный
                                # порядок, затем score. Называет основание выбора
                                # и число задач, отложенных из-за предшественниц
task depends <slug> --after <slug>    # Объявить, что задача идёт ПОСЛЕ другой
task undepends <slug> --after <slug>  # Снять объявленный порядок
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
          [--full] [--top-n N] [--max-lines N]   # >25 строк — свёртка по статусу/роли; --full = полная таблица
task show <slug>                # Полная информация: план, заметки, решения, defect_of, AC
task show <slug> --package      # Ограниченный детерминированный контекст (8192 Б)
task show <slug> --package --max-bytes 4096
task show <slug> --work-packet --query "..." [--source PATH ...] [--max-bytes N]
                                # Один bounded JSON: task context, FTS, memory и полные
                                # scope-checked UTF-8 источники. Каждый результат имеет адрес;
                                # непоместившиеся/нечитаемые/out-of-scope источники перечислены
                                # в omitted, без тихого усечения. До половины ceiling (макс. 8192 Б)
                                # заранее выделено целому task context; лимит указан в allocations.
                                # Не более 16 --source.
task start <slug> [--package]   # planning → active; package возвращает bounded context в этом вызове
                                #   время сессии и ёмкость вызовов — совет в выводе, не отказ (1.10, #376)
                                #   --force отозван: флаг отвечает отказом с причиной
task obsolete <slug> --reason "..."   # закрыть задачу, которую решило время: запись остаётся, без QG-2,
                                #   вне FPSR/DER/cycle/lead/калибровки; причина >=10 символов; только CLI (#390)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...] [--evidence "..."]
                 [--message "final progress" --step N [--verify]]
                 [--verify-handle <run_id>.<nonce>]
                                # QG-2: --ac-verified подтверждает проверку AC (требует evidence в notes
                                #       ИЛИ --evidence inline). v1.5 Verify-First Contract: heavy gates
                                #       (pytest, tsc, cargo, ...) НЕ запускаются здесь — они на отдельной
                                #       команде `verify`.
                                # --verify-handle (1.8): ПРЕДЪЯВИТЬ хендл, который напечатал
                                #       `verify --task <slug>`, вместо поиска свежей строки. Хендл называет
                                #       ОДИН прогон, одноразовый, несёт свой срок годности (1 час) и
                                #       проверяется по ЖИВЫМ файлам и ЖИВОМУ конфигу гейтов — поэтому его
                                #       отказ говорит по существу («файлы изменились с момента verify»),
                                #       а не «промах кэша». Подробности: docs/ru/receipts.md.
                                # БЕЗ --verify-handle поведение прежнее: поиск свежего green из
                                #       verify cache (10 min TTL, тот же files_hash), закрытие за
                                #       миллисекунды. Если verify не запускался — блок с remediation.
                                #       Opt-out: .tausik/config.json → {"task_done":{"auto_verify":true}}
                                #       — старое поведение (heavy гейты inline). НЕТ --force.
                                # --gates-not-applicable (1.9): ЗАКРЫТЬ НА ПРОГОНЕ, В КОТОРОМ НЕ
                                #       ВЫПОЛНИЛСЯ НИ ОДИН ГЕЙТ. SENAR 1.4 §8.6(e): отсутствие
                                #       отрицательной находки НЕ ЕСТЬ положительный вердикт, поэтому
                                #       `verify --no-tests-expected` записывает заявление, а этот флаг —
                                #       ОТДЕЛЬНЫЙ ЗАПИСАННЫЙ АКТ его принятия. Для работы, которая
                                #       честно не мапится на тест: документация, конфиг, исследование.
                                #       НЕ спасает прогон, в котором гейт БЫЛ ПРИМЕНИМ и всё равно не
                                #       выполнился (COULD_NOT_RUN) — такой чинят, а не признают.
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked → active
task review <slug>              # active → review
task update <slug> [--title T] [--goal G] [--notes N] [--notes-overwrite] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER] [--ticket REF ...]
                                # --ticket (1.9): внешний тикет, на который отвечает задача.
                                #   ЧЕРЕЗ ПРОБЕЛ, не через запятую: --ticket github#7 gitlab#12
                                #   Форма `<трекер>#<номер>` либо полный https-адрес. Имя трекера
                                #   ОБЯЗАТЕЛЬНО, и голый `#7` отвергается при записи: у этого
                                #   репозитория два трекера, и GitHub #7 с GitLab #7 — РАЗНЫЕ
                                #   тикеты разных авторов. Тот же флаг есть у `task add`.
                                #   При закрытии задачи привязка ПЕЧАТАЕТ напоминание ответить
                                #   автору. Ничего никуда не отправляется и ни один тикет не
                                #   закрывается: тикет мог описывать больше, чем закрыла задача.
                                # ⚠ --notes ЗАМЕНЯЕТ весь журнал (notes — append-only история,
                                #   пишется через `task log`). По умолчанию перезапись непустого
                                #   журнала ОТКЛОНЯЕТСЯ; чтобы дописать — `task log`, чтобы
                                #   намеренно заменить — добавь --notes-overwrite.
task delete <slug>
task delegate <slug>            # Orchestrator-worker: делегировать задачу complexity<=medium воркеру-сабагенту (рекоменд. модель + parent session; complex отвергается)
task undelegate <slug>          # Очистить делегирование
task handoff <slug>             # Печать детерминированного handoff-контракта воркера (JSON: goal/AC/scope/model/skills) для spawn через Agent tool
task summary-back <slug> "<summary>" [--changed F] [--gates S] [--ac-evidence E] [--follow-ups U]  # Воркер -> координатор структурный результат
task plan <slug> <шаг1> <шаг2> ...   # Задать шаги плана
task step <slug> <номер_шага> [--message "Step N done: ..."]
                                # --message композирует log → step через существующие операции сервиса
task log <slug> <сообщение>    # Таймстемп-заметка (crash-safe журнал)
task logs <slug> [--phase PHASE] # Чтение структурированных логов (planning/implementation/review/testing/done)
task reason-step <slug> <kind> <content>  # RENAR шаг рассуждения (kind: intent|premise|action|verification)
task replay <slug> [--output FILE]  # Хронологический таймлайн: logs + reasoning + events + verification
task move <slug> <new_story>   # Переместить задачу в другую стори
task claim <slug> <agent_id>   # Мульти-агент: занять задачу
task unclaim <slug>            # Освободить задачу
```

Составной переход не вводит отдельное состояние задачи. `task step --message` выполняет
`task_log`, затем `task_step`. Финальное `task done --message ... --step N --verify`
добавляет тот же scoped verify и `task_done`. При отказе успешные ранние переходы
остаются записанными, JSON называет точную стадию отказа, а CLI завершается с ненулевым кодом.
`--verify` и `--verify-handle` взаимоисключающие: переданный stale handle не заменяется новым прогоном.

### Порядок работ выражается рёбрами, а не номерами

`task depends B --after A` означает: B не будет предложена, пока A не `done`.
Не `active`, не `review` — именно `done`: «после» есть утверждение о ЗАВЕРШЁННОЙ
работе, и выдать B, пока A ещё пишется, значит выдать её в неготовый мир.

Ребро, а не число приоритета, потому что план формулирует порядок именно так:
«эта первой», «та только после неё». Числовое поле пришлось бы перенумеровывать
при каждой вставке и не сохраняло бы ПРИЧИНУ порядка.

Цикл отвергается в момент объявления и печатает путь целиком — «обнаружен цикл»
сообщает автору, что он неправ, не сообщая, КАКОЕ из его прежних утверждений
противоречит новому. Повторное объявление того же ребра — не ошибка: скрипт
плана обязан сходиться при повторном прогоне, а не падать на середине.

`task next` теперь различает три состояния, которые раньше сливались в «No
available tasks»: очередь пуста; очередь есть, но каждая задача ждёт незавершённую
предшественницу; задача есть. Второе — остановившийся план, и читать его как
законченный нельзя.

Ребро ЕДЕТ в проекцию (`depends_on` во frontmatter задачи), потому что это
намерение, а не телеметрия: план, исчезающий при клонировании, и есть тот дефект,
ради которого механизм построен.

**Опциональные подсказки модели:** если в `.tausik/config.json` задано `{"task_next":{"model_hint":true}}`, команды `task next` и `hud` выводят дополнительный неблокирующий маршрут по сложности задачи. Маршрут использует семейство активной модели, когда оно известно (Claude, OpenAI/Codex или GLM); иначе берёт семейство по умолчанию из конфига. Только opt-in; без ключа или при `false` поведение как раньше.

`task delegate` применяет маршрут только через новый ограниченный контекст воркера. Claude Code и Codex позволяют выбрать модель создаваемого сабагента; Kilo/GLM остаётся advisory, пока не подтверждена поверхность spawn самого хоста. Работающая сессия координатора никогда не помечается как переключённая. Выбранный маршрут становится `applied` лишь после старта делегированной задачи воркером; неудачный или отменённый spawn остаётся `selected`. Глубина делегирования ограничена единицей, а verify, доказательства и закрытие остаются у координатора.

**Допустимые стеки (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom-стеки добавляются через `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Бюджеты >400 принимаются; tier label cap'ается на `deep`.

## Сессии

```bash
session start [--host-id ID]    # Свежая проверка релиза, затем старт; новая версия запрещает, unknown предупреждает; --host-id идемпотентен
session end [--summary TEXT] [--host-id ID]  # Завершить активную; с --host-id — ровно сессию этого хоста
session current                 # Показать активную сессию
session list [--limit N]        # Последние сессии (default: 10); столбец handoff показывает, у каких он записан
session handoff [json] [--host-id ID]  # Handoff из журнала; json — авторские next_steps/warnings поверх (1.10)
session last-handoff [--session N]  # Живой handoff; с --session — handoff сессии N (нет сессии / нет handoff — разные отказы)
session extend [--minutes N]    # Поднять порог совета по active-time (`session_max_minutes`; совет, не ворота)
session recompute               # Retro: сравнить wall-clock vs active (gap-based) минуты
```

Время сессии считается по **active** time (gap-based, пауза после 10 мин idle), не wall clock; порог `session_max_minutes` — совет, не отказ (1.10). См. `session-active-time.md`.
На `session end` TAUSIK также делает best-effort запись usage через `scripts/hooks/session_metrics.py --auto --record` (поддержаны transcript roots и Claude, и Cursor).
