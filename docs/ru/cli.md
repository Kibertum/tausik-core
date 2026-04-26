[English](../en/cli.md) | **Русский**

# TAUSIK CLI — Справочник команд (v1.3)

Все команды запускаются через обёртку: `.tausik/tausik <команда> [подкоманда] [аргументы]`.
На Windows обёртка — `.tausik/tausik.cmd`. Тот же surface также доступен через MCP (`tausik_*` инструменты); см. `mcp.md`.

## Инициализация

```bash
init --name <slug>             # Инициализация проекта (создаёт .tausik/tausik.db)
status                         # Обзор проекта + предупреждение SENAR (active vs wall)
metrics                        # Метрики SENAR: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
doctor                         # Health check: venv + DB + MCP + skills + drift
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
task add <title> [--story STORY_SLUG] [--slug SLUG] [--stack STACK]
                 [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE]
                 [--defect-of PARENT_SLUG]
                 [--call-budget N] [--tier {trivial,light,moderate,substantial,deep}]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]    # Выбрать следующую planning-задачу (по score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
task show <slug>                # Полная информация: план, заметки, решения, defect_of, AC
task start <slug> [--force]     # planning → active (QG-0: требует goal + AC + negative scenario)
                                # --force байпасит session capacity gate (audit event + note)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...] [--evidence "..."]
                                # QG-2: --ac-verified подтверждает проверку AC (требует evidence в notes
                                #       ИЛИ --evidence inline). Запускает scoped pytest gate (basename
                                #       match на tests/test_<file>.py для каждого relevant-файла). Verify
                                #       cache (10 min TTL) пропускает re-run при том же files_hash.
                                #       НЕТ --force.
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked → active
task review <slug>              # active → review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER]
task delete <slug>
task plan <slug> <шаг1> <шаг2> ...   # Задать шаги плана
task step <slug> <номер_шага>  # Отметить шаг N выполненным (нумерация с 1)
task log <slug> <сообщение>    # Таймстемп-заметка (crash-safe журнал)
task logs <slug> [--phase PHASE] # Чтение структурированных логов (planning/implementation/review/testing/done)
task move <slug> <new_story>   # Переместить задачу в другую стори
task claim <slug> <agent_id>   # Мульти-агент: занять задачу
task unclaim <slug>            # Освободить задачу
```

**Допустимые стеки (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom-стеки добавляются через `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Бюджеты >400 принимаются; tier label cap'ается на `deep`.

## Верификация

```bash
verify [--task SLUG] [--scope {lightweight,standard,high,critical,manual}]
                                # Запустить scoped quality gates ad-hoc; пишет в verify cache
```

## Шлюзы качества

```bash
gates status                    # Все gates и их конфигурация
gates list                      # Список gates с состоянием вкл/выкл
gates enable <name>             # Включить gate
gates disable <name>            # Выключить gate
```

## Стеки

```bash
stack info <stack>              # Резолвленный стек: gates per language + override info
stack list                      # Список встроенных + custom-стеков
stack export <stack>            # Печать резолвленного декларации как JSON
stack diff <stack>              # Diff между встроенным и user override
stack reset <stack>             # Удалить user override в .tausik/stacks/<stack>/
stack lint                      # Валидировать user-override stack.json против схемы
stack scaffold <name>           # Создать .tausik/stacks/<name>/{stack.json,guide.md} skeleton
```

## Роли

```bash
role list
role show <slug>
role create <slug> <title> [--description TEXT] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                       # Bootstrap из agents/roles/*.md и использования в задачах
```

Хранение ролей гибридное: SQLite-метаданные + markdown-профиль `agents/roles/{role}.md`. Роли в задачах остаются свободным текстом (`--role developer/architect/qa/...`).

## Сессии

```bash
session start                   # Начать новую сессию (возвращает ID)
session end [--summary TEXT]    # Завершить активную сессию
session current                 # Показать активную сессию
session list [--limit N]        # Последние сессии (default: 10)
session handoff <json_data>     # Сохранить данные передачи для следующей сессии
session last-handoff            # Получить передачу предыдущей сессии
session extend [--minutes N]    # Продлить active-time лимит сверх 180 мин (SENAR Rule 9.2)
session recompute               # Retro: сравнить wall-clock vs active (gap-based) минуты
```

Лимит сессии — 180 мин **active** time (gap-based, паузится после 10 мин idle), не wall clock. Threshold настраивается в `.tausik/config.json` → `session_idle_threshold_minutes`. См. `session-active-time.md`.

## Знания

```bash
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]           # Список решений (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
memory list [--type TYPE] [--limit N]
memory search <query>           # FTS5 полнотекстовый поиск
memory show <id>
memory delete <id>

# Графовая память (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation>
            [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]   # Soft-invalidate (никогда не удаляет)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N]
             [--relation {supersedes,caused_by,relates_to,contradicts}]
             [--include-invalid] [--limit N]

# Агрегаторы
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]
```

**Типы памяти:** pattern, gotcha, convention, context, dead_end
**Типы узлов графа:** memory, decision
**Типы связей:** supersedes, caused_by, relates_to, contradicts

## Документирование тупиков (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Документирует неудачный подход с причиной. Сохраняется как memory тип dead_end.
```

## Исследования (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]    # Начать исследование (default: 30 мин)
explore end [--summary TEXT] [--create-task]    # Завершить (--create-task создаёт задачу)
explore current                                 # Показать активное исследование
```

## Периодический аудит (SENAR Rule 9.5)

```bash
audit check                     # Показать, просрочен ли периодический аудит
audit mark                      # Отметить аудит выполненным
```

## Мульти-агент

```bash
team                            # Задачи сгруппированные по агентам (claimed_by)
```

## Навыки

```bash
skill list                      # Активные, vendored, доступные
skill install <name>            # Установить из репо (clone + copy + deps)
skill uninstall <name>          # Удалить полностью
skill activate <name>           # Активировать установленный
skill deactivate <name>         # Деактивировать (файлы остаются)
skill repo add <url>            # Добавить TAUSIK-совместимый репо
skill repo remove <name>        # Удалить репо
skill repo list                 # Список репозиториев и навыков
```

## Shared Brain (cross-project)

```bash
brain init                      # Инициализация: 4 Notion DB + конфиг
brain status                    # Mirror freshness, sync state, registered проекты
brain move <source_id> --to-brain --kind {decision,pattern,gotcha} [--keep-source]
brain move <notion_page_id> --to-local --category {decisions,patterns,gotchas,web_cache} [--force]
```

## Поиск и навигация

```bash
roadmap [--include-done]        # Полное дерево epic → story → task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Пакетное выполнение

```bash
run <plan-file.md>              # Парсинг и показ сводки batch-run плана
```

Планы — markdown с нумерованными задачами, целями и списками файлов. Используйте `/run plan.md` в интерактивной сессии для автономного выполнения.

## Извлечение документов

```bash
doc extract <path>              # Конвертировать DOCX/PPTX/XLSX/HTML/EPUB/PDF в markdown через markitdown
```

Opt-in: требует `markitdown` и Python ≥3.11.

## События (Журнал аудита)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Обслуживание

```bash
update-claudemd [--claudemd PATH]     # Обновить секцию <!-- DYNAMIC --> в CLAUDE.md
fts optimize                          # Оптимизировать FTS5 индексы
hud                                   # Live dashboard: задача + сессия + gates + логи
suggest-model [complexity]            # Рекомендация Claude-модели: simple→Haiku, medium→Sonnet, complex→Opus
```

## Константы

| Концепция | Значения |
|-----------|----------|
| Статусы задач | `planning → active → blocked ↔ active → review → done` |
| Формат slug | `^[a-z0-9][a-z0-9-]*$` (макс. 64 символа) |
| Сложность → SP | simple=1, medium=3, complex=8 |
| Tiers (call calls) | trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400 |
| Типы памяти | pattern, gotcha, convention, context, dead_end |
| Роли | Свободный текст (без enum); реестр в `agents/roles/{slug}.md` |
| SENAR gates | QG-0 (Context Gate на `task start`), QG-2 (Implementation Gate на `task done`) |
| Лимит сессии | 180 мин **active** по умолчанию (настраивается: `session_max_minutes`, idle threshold: `session_idle_threshold_minutes`) |
