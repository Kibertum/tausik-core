[English](../en/cli.md) | **Русский**

# TAUSIK CLI — Справочник команд

Все команды запускаются через обёртку: `.tausik/tausik <команда> [подкоманда] [аргументы]`

## Инициализация

```bash
init --name <slug>             # Инициализация проекта (создаёт .tausik/tausik.db)
status                         # Обзор проекта + предупреждение SENAR о длительности сессии
metrics                        # Метрики SENAR: производительность, время выполнения, доля успеха, уровень дефектов
```

## Иерархия

```bash
epic add <slug> <title> [--description TEXT]
epic list
epic done <slug>
epic delete <slug>             # CASCADE: удаляет все стори + задачи

story add <epic_slug> <slug> <title> [--description TEXT]
story list [--epic EPIC_SLUG]
story done <slug>
story delete <slug>            # CASCADE: удаляет все задачи
```

## Задачи

```bash
task add <title> [--group STORY_SLUG] [--slug SLUG] [--stack STACK] [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE] [--defect-of PARENT_SLUG]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]     # Выбрать следующую planning-задачу (по score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK]
task show <slug>               # Полная информация: план, заметки, решения, defect_of
task start <slug>              # planning → active (QG-0: требует goal + acceptance_criteria)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...]
                               # QG-2: --ac-verified подтверждает проверку AC (требует evidence в notes)
                               # --no-knowledge: явно подтвердить отсутствие знаний для фиксации
task block <slug> [--reason TEXT]
task unblock <slug>            # blocked → active
task review <slug>             # active → review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC] [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
task delete <slug>
task plan <slug> <шаг1> <шаг2> ...   # Задать шаги плана
task step <slug> <номер_шага>  # Отметить шаг N выполненным (нумерация с 1)
task log <slug> <сообщение>    # Добавить таймстемп-заметку (crash-safe журнал)
task move <slug> <new_story>   # Переместить задачу в другую стори
task claim <slug> <agent_id>   # Мульти-агент: занять задачу
task unclaim <slug>            # Освободить задачу
```

**Допустимые стеки:** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade

## Документирование тупиков (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Документирует неудачный подход с причиной. Сохраняется в memory как тип dead_end.
```

## Исследования (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]   # Начать исследование (по умолчанию: 30 мин)
explore end [--summary TEXT] [--create-task]    # Завершить (--create-task создаёт задачу по итогам)
explore current                                 # Показать активное исследование с прошедшим временем
```

## Мульти-агент

```bash
team                           # Задачи сгруппированные по агентам (claimed_by)
```

## Сессии

```bash
session start                  # Начать новую сессию (возвращает ID)
session end [--summary TEXT]   # Завершить активную сессию
session extend [--minutes N]   # Продлить сессию сверх лимита 180 мин (SENAR Rule 9.2)
session current                # Показать активную сессию
session list [--limit N]       # Последние сессии (по умолчанию: 10)
session handoff <json_data>    # Сохранить данные передачи для следующей сессии
session last-handoff           # Получить передачу предыдущей сессии
```

## Знания

```bash
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]          # Список решений (по умолчанию: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
memory list [--type TYPE] [--limit N]
memory search <query>          # FTS5 полнотекстовый поиск
memory show <id>
memory delete <id>

# Графовая память (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation> [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]  # Soft-invalidate (никогда не удаляет)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N] [--relation {supersedes,caused_by,relates_to,contradicts}] [--include-invalid] [--limit N]

# Агрегаторы (v1.2.0) — Memory Block re-injection + Dream-System-inspired консолидация
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]
```

**Типы памяти:** pattern, gotcha, convention, context, dead_end
**Типы узлов графа:** memory, decision
**Типы связей:** supersedes, caused_by, relates_to, contradicts

## Поиск и навигация

```bash
roadmap [--include-done]       # Полное дерево epic → story → task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Шлюзы качества

```bash
gates status                   # Показать все шлюзы и их конфигурацию
gates list                     # Список шлюзов с состоянием вкл/выкл
gates enable <name>            # Включить шлюз
gates disable <name>           # Выключить шлюз
```

## Навыки

```bash
skill list                     # Список навыков: активные, установленные, доступные
skill install <name>           # Установить из репо (clone + copy + deps)
skill uninstall <name>         # Удалить навык полностью
skill activate <name>          # Активировать установленный навык
skill deactivate <name>        # Деактивировать (файлы остаются)
skill repo add <url>           # Добавить TAUSIK-совместимый репозиторий
skill repo remove <name>       # Удалить репозиторий
skill repo list                # Список репозиториев и их навыков
```

## Пакетное выполнение

```bash
run <plan-file.md>             # Показать сводку плана пакетного выполнения
```

Планы — это markdown-файлы с нумерованными задачами, целями и списками файлов. Используйте `/run plan.md` в интерактивной сессии для автономного выполнения.

## События (Журнал аудита)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Обслуживание

```bash
update-claudemd [--claudemd PATH]     # Обновить секцию <!-- DYNAMIC --> в CLAUDE.md
fts optimize                          # Оптимизировать FTS5 индексы
hud                                   # Live dashboard: активная задача + сессия + gates + логи (v1.2.0)
suggest-model [complexity]            # Рекомендация Claude-модели: simple→Haiku, medium→Sonnet, complex→Opus (v1.2.0)
```

## Константы

| Концепция | Значения |
|-----------|----------|
| Статусы задач | `planning → active → blocked ↔ active → review → done` |
| Формат slug | `^[a-z0-9][a-z0-9-]*$` (макс. 64 символа) |
| Сложность → SP | simple=1, medium=3, complex=8 |
| Типы памяти | pattern, gotcha, convention, context, dead_end |
| Роли | Свободный текст (без ограничений) |
| Шлюзы SENAR | QG-0 (шлюз контекста при старте), QG-2 (шлюз реализации при завершении) |
| Лимит сессии | 180 мин по умолчанию (настраивается в config.json: session_max_minutes) |
