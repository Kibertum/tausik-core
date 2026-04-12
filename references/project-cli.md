# TAUSIK CLI — Справочник команд

Все команды запускаются через обёртку: `.tausik/tausik <команда> [подкоманда] [аргументы]`

## Инициализация

```bash
init [--name <slug>]           # Инициализация проекта (имя из папки если не указано)
status                         # Обзор проекта + предупреждение SENAR о длительности сессии
metrics                        # SENAR метрики: Throughput, Lead Time, FPSR, DER, Cycle Time, KCR
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
task done <slug> --ac-verified [--relevant-files FILE1 FILE2 ...]
                               # QG-2: --ac-verified подтверждает проверку AC (требует evidence в notes)
task block <slug> [--reason TEXT]
task unblock <slug>            # blocked → active
task review <slug>             # active → review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC] [--scope S] [--stack S] [--complexity C] [--role ROLE]
task delete <slug>
task plan <slug> <шаг1> <шаг2> ...   # Задать шаги плана
task step <slug> <номер_шага>  # Отметить шаг N выполненным (нумерация с 1)
task log <slug> <сообщение>    # Добавить таймстемп-заметку (crash-safe журнал)
task move <slug> <new_story>   # Переместить задачу в другую стори
task claim <slug> <agent_id>   # Мульти-агент: занять задачу
task unclaim <slug>            # Освободить задачу
```

**Допустимые стеки:** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade

## Dead End документирование (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Документирует неудачный подход с причиной. Сохраняется в memory как тип dead_end.
```

## Exploration (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]   # Начать investigation (по умолчанию: 30 мин)
explore end [--summary TEXT] [--create-task]    # Завершить (--create-task создаёт задачу из findings)
explore current                                 # Показать активное exploration с elapsed time
```

## Мульти-агент

```bash
team                           # Задачи сгруппированные по агентам (claimed_by)
```

## Сессии

```bash
session start                  # Начать новую сессию (возвращает ID)
session end [--summary TEXT]   # Завершить активную сессию
session current                # Показать активную сессию
session list [--limit N]       # Последние сессии (по умолчанию: 10)
session extend [--minutes N]   # Продлить лимит сессии на N минут (по умолчанию: 60)
session handoff <json_data>    # Сохранить handoff JSON для следующей сессии
session last-handoff           # Получить handoff последней сессии
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
```

**Типы памяти:** pattern, gotcha, convention, context, dead_end
**Типы узлов графа:** memory, decision
**Типы связей:** supersedes, caused_by, relates_to, contradicts

## Поиск и навигация

```bash
roadmap [--include-done]       # Полное дерево epic → story → task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Quality Gates

```bash
gates status                   # Показать все quality gates и их конфигурацию
gates list                     # Список gates с enabled/disabled статусом
gates enable <name>            # Включить gate
gates disable <name>           # Выключить gate
```

## Skills

```bash
skill list                     # Список: active, vendored, available из repos
skill install <name>           # Установить из repo (clone + copy + pip deps)
skill uninstall <name>         # Удалить skill полностью
skill activate <name>          # Активировать установленный skill
skill deactivate <name>        # Деактивировать (файлы остаются)
skill repo add <url>           # Добавить TAUSIK-совместимый repo
skill repo remove <name>       # Удалить repo
skill repo list                # Список repos и их skills
```

## События (Журнал аудита)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Обслуживание

```bash
update-claudemd [--claudemd PATH]   # Обновить секцию <!-- DYNAMIC --> в CLAUDE.md
fts optimize                        # Оптимизировать FTS5 индексы
```

## Константы

| Концепция | Значения |
|-----------|----------|
| Статусы задач | `planning → active → blocked ↔ active → review → done` |
| Формат slug | `^[a-z0-9][a-z0-9-]*$` (макс. 64 символа) |
| Сложность → SP | simple=1, medium=3, complex=8 |
| Типы памяти | pattern, gotcha, convention, context, dead_end |
| Роли | Свободный текст (без ограничений) |
| SENAR gates | QG-0 (Context Gate на task start), QG-2 (Implementation Gate на task done) |
| Session limit | 180 мин по умолчанию (настраивается в config.json: session_max_minutes) |
