[English](../en/stacks.md) | **Русский**

# Гайд по стек-плагинам

> **TL;DR.** Каждый стек — это декларация `stack.json` в `stacks/<name>/`. Фреймворк загружает их через `StackRegistry`. Чтобы добавить новый стек, пишете один JSON-файл; чтобы кастомизировать существующий — кладёте override в `.tausik/stacks/<name>/`.

## Зачем плагин-раскладка

До v1.6 каждый стек был захардкожен в пяти местах: `project_types.DEFAULT_STACKS`, `bootstrap_config.STACK_SIGNATURES`, `gate_stack_dispatch._EXT_TO_STACKS`, `default_gates.DEFAULT_GATES`, `project_config.STACK_GATE_MAP`. Добавление стека требовало править все пять с высоким риском drift'а. Плагин-модель сводит их к единому источнику истины: `stacks/<name>/stack.json`. Потребители читают реестр; реестр читает JSON.

## Встроенные стеки

```
stacks/
├── _schema.json       ← JSON Schema для stack.json (Draft-07)
├── python/
│   ├── stack.json
│   └── guide.md
├── typescript/
│   ├── stack.json
│   └── guide.md
└── ...                ← всего 25 встроенных стеков
```

Каждый `stack.json` соответствует `stacks/_schema.json`. `guide.md` — per-stack гайд для человека, который всплывает в выводе skill'ов.

## Поля stack.json

| Поле | Тип | Назначение |
|---|---|---|
| `name` | string (обязательно) | Lowercase slug. Должен соответствовать `^[a-z][a-z0-9_-]*$`. |
| `version` | string | Свободная версия decl'а. Default `"1"`. |
| `extends` | string | `"builtin:NAME"` для наследования от встроенного стека. Используется в user override. |
| `detect` | list of `{file, type, keyword?}` | Сигнатуры в корне проекта, используемые `detect_stacks()`. `type` ∈ `exact` / `glob` / `dir-marker`. Опциональный `keyword` фильтрует содержимое файла. |
| `extensions` | list of strings | Расширения файлов (с ведущей точкой), сигналящие об этом стеке. Питает `_EXT_TO_STACKS`. |
| `filenames` | list of strings | Lowercase имена файлов (например `dockerfile`), сигналящие о стеке независимо от расширения. |
| `path_hints` | list of strings | Фрагменты путей (`/playbooks/`), используемые для disambiguation YAML/JSON в IaC-деревьях. |
| `gates` | object | Gate-имя → gate-config dict. Значение `null` отключает унаследованный gate. |
| `guide_path` | string | Относительный путь к гайду стека. Default `"guide.md"`. |
| `extensions_extra` | list of strings | **Аддитивно** к унаследованным `extensions`. Полезно в user override. |

## Добавление нового встроенного стека

1. Создайте `stacks/<name>/stack.json`. Минимум:

   ```json
   {
     "name": "ruby",
     "detect": [{ "file": "Gemfile", "type": "exact" }],
     "extensions": [".rb"]
   }
   ```

2. (Опционально) Добавьте `stacks/<name>/guide.md` с секциями: `Testing`, `Review Checklist`, `Conventions`, `Common Pitfalls`. Тест skills-maturity проверяет их наличие.

3. (Опционально) Объявите gates в поле `gates` — например, RSpec gate, scoped на ruby. Конфиг gate соответствует форме `default_gates.UNIVERSAL_GATES`: `enabled`, `severity`, `trigger`, `command`, `description`, `timeout`, `stacks`.

4. Запустите `python bootstrap/bootstrap.py --no-detect`, чтобы обновить `.claude/stacks/`, `_STACKS_ENUM` в MCP `tools.py` и остальных потребителей.

5. Запустите `pytest tests/test_stack_registry.py` и `pytest tests/test_gates.py`, чтобы убедиться, что ничего не сломалось.

## Где читается реестр

Единственная точка импорта — `scripts/stack_registry.default_registry()`. После v1.6 все потребители роутятся через неё:

| Потребитель | Что потребляется |
|---|---|
| `project_types.DEFAULT_STACKS` | `all_stacks()` |
| `bootstrap_config.STACK_SIGNATURES` | `signatures_for(name)` |
| `gate_stack_dispatch._EXT_TO_STACKS` | `extensions_for(name)` |
| `gate_stack_dispatch._FILENAME_TO_STACKS` | `filenames_for(name)` |
| `gate_stack_dispatch._PATH_HINTS` | `path_hints_for(name)` |
| `default_gates.DEFAULT_GATES` (stack-scoped) | `gates_for(name)` |
| `project_config.STACK_GATE_MAP` | derived из `DEFAULT_GATES` |
| MCP `tools.py` `_STACKS_ENUM` | регенерируется bootstrap'ом из `all_stacks()` |

Каждый потребитель несёт hardcoded fallback, чтобы импорт модуля не падал, если реестр не загружается.

## Валидация

`scripts/stack_schema.validate_decl(decl, source)` возвращает список actionable-ошибок. Каждая ошибка называет source-файл, поле и нарушенное правило. Пустой список = валиден. Используйте программно при генерации decl'ов или запускайте полный lint через `tausik stack lint`.

## Тестирование

`tests/test_stack_registry.py` покрывает:

- Загрузка: отсутствующая директория, невалидный JSON, schema-invalid, скрытые директории, дубликаты.
- Override: `extends`, `extensions_extra` аддитивный merge, `null` gate disable, per-key gate override, неизвестный extends-target, standalone user-стеки.
- Reload + cache invalidation.
- Source tracking (`source_for`, `is_user_overridden`).

Запуск: `pytest tests/test_stack_registry.py -v`.

## DEFAULT_STACKS (25)

`python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker`. Список открыт для расширения через `.tausik/config.json` → `custom_stacks`.

## См. также

- [Кастомизация](customization.md) — как переопределить встроенный стек без правки `stacks/<name>/`.
- [Архитектура](architecture.md) — трёхслойная модель и место реестра.
