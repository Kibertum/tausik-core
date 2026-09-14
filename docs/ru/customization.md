[English](../en/customization.md) | **Русский**

# Кастомизация

> **Контракт:** TAUSIK никогда не трогает вашу директорию `.tausik/`. Всё, что вы кладёте в `.tausik/stacks/<name>/`, переживает каждое обновление фреймворка.

## Что можно кастомизировать

| Цель | Где |
|---|---|
| Добавить новый стек только для своего проекта | `.tausik/stacks/<name>/stack.json` |
| Подправить встроенный стек (больше расширений, своя команда gate, выключить gate) | `.tausik/stacks/<name>/stack.json` с `"extends": "builtin:<name>"` |
| Stack-specific gates (например `ruff --select=E,W`) | Override gate внутри `gates`-карты стека |
| Процесс-уровневые флаги gate (enabled/disabled) | `.tausik/config.json` под ключом `"gates"` |

## Быстрый старт: переопределить существующий стек

Допустим, встроенный стек `python` поставляется с gate `pytest`, но ваш проект хочет ещё Pyright type-checking и расширение `.pyi` как Python-файл.

1. Создайте override-файл:

   ```bash
   mkdir -p .tausik/stacks/python
   ```

2. Положите туда `stack.json`:

   ```json
   {
     "name": "python",
     "extends": "builtin:python",
     "extensions_extra": [".pyi"],
     "gates": {
       "pyright": {
         "enabled": true,
         "severity": "warn",
         "trigger": ["task-done"],
         "command": "pyright {files}",
         "description": "Pyright type check (custom)",
         "stacks": ["python"]
       }
     }
   }
   ```

3. Проверьте:

   ```bash
   .tausik/tausik stack lint           # валидация stack.json
   .tausik/tausik stack export python  # резолвленный decl (built-in + override)
   .tausik/tausik stack diff python    # что именно меняет ваш override
   ```

## Семантика merge

Когда вы указываете `"extends": "builtin:NAME"`:

- **`extensions_extra`** — аддитивно. Добавляется к унаследованному списку `extensions`. Используйте, чтобы *добавить* расширения; используйте `extensions` целиком только для полной замены.
- **`gates`** — пер-key override. Ключи в вашем decl переопределяют унаследованные. Ключ со значением `null` **отключает** унаследованный gate.
- **`detect`, `filenames`, `path_hints`, `version`, `guide_path`** — заменяются, если присутствуют в override; иначе наследуются без изменений.

User-decl **без** `extends` и с именем, совпадающим со встроенным, — это **полная замена**: встроенный полностью отбрасывается.

User-decl с новым именем — **standalone**-стек: добавляется в реестр независимо.

## Отключение унаследованного gate

```json
{
  "name": "python",
  "extends": "builtin:python",
  "gates": { "pytest": null }
}
```

Этого достаточно. `null` убирает gate из резолвленного decl. Встроенный стек на диске не трогается.

## Когда использовать `.tausik/config.json`

Используйте `config.json → gates.<name>.enabled`, когда нужно просто включить/выключить gate проектно-уровнево без изменения команды, severity или stack scope. Используйте `.tausik/stacks/<name>/stack.json`, когда нужно изменить определение gate или добавить новые.

## Сброс override

```bash
.tausik/tausik stack reset python      # запрашивает подтверждение
.tausik/tausik stack reset python --yes
```

Это удалит `.tausik/stacks/python/`. Встроенный стек не пострадает.

## Инструменты валидации

| Команда | Назначение |
|---|---|
| `tausik stack lint` | Валидирует каждый `.tausik/stacks/*/stack.json` против `_schema.json`. |
| `tausik stack export <name>` | Печатает резолвленный decl как JSON (для проверки merge). |
| `tausik stack diff <name>` | Unified diff между built-in и вашим override. |

## Чего делать НЕЛЬЗЯ

- **Не редактируйте `stacks/<name>/stack.json` напрямую.** Это дерево принадлежит bootstrap'у. Ваши правки будут перетёрты на следующем `python bootstrap/bootstrap.py` (CI может принудительно ребутстрэпить). Всегда работайте через `.tausik/stacks/`.
- **Не кладите per-task overrides в stack.json.** Per-task ручки — в `.tausik/config.json`.

## Добавление совершенно нового стека

Если ваш проект использует стек, которого нет в TAUSIK — например, Elixir:

```json
{
  "name": "elixir",
  "detect": [{ "file": "mix.exs", "type": "exact" }],
  "extensions": [".ex", ".exs"],
  "gates": {
    "mix-test": {
      "enabled": true,
      "severity": "block",
      "trigger": ["task-done"],
      "command": "mix test",
      "description": "Run Elixir tests",
      "stacks": ["elixir"],
      "timeout": 240
    }
  }
}
```

После прохождения `tausik stack lint` можно использовать `--stack elixir` в `task add`, и реестр корректно обнаружит gates.

## См. также

- [Stacks Plugin Guide](stacks.md) — полная схема.
- [Upgrade Safety](upgrade.md) — что bootstrap трогает, а что нет.
