[English](../en/upgrade.md) | **Русский**

# Безопасное обновление

Что bootstrap трогает, что не трогает, и как обновляться без потери своей работы.

## Два дерева

```
<repo>/
├── stacks/                ← владение фреймворка. Bootstrap перезаписывает.
├── scripts/               ← владение фреймворка.
├── bootstrap/             ← владение фреймворка.
├── agents/                ← владение фреймворка.
├── .claude/               ← вывод bootstrap (можно игнорировать; регенерируется).
└── .tausik/               ← ВАШИ данные. Bootstrap НИКОГДА их не трогает.
    ├── tausik.db
    ├── config.json
    ├── stacks/            ← ваши stack-override
    └── venv/
```

## Bootstrap-owned vs user-owned

| Путь | Владелец | Переживает обновление? |
|---|---|---|
| `stacks/<name>/stack.json` | Фреймворк | Нет — перезаписывается на каждый bootstrap. |
| `agents/stacks/*.md` (legacy) | Фреймворк | Заменяется на bootstrap; только как legacy fallback. |
| `.claude/` | Вывод bootstrap | Регенерируется при каждом запуске. |
| `.tausik/stacks/<name>/stack.json` | **Вы** | **Да — bootstrap не трогает.** |
| `.tausik/config.json` | **Вы** | **Да.** |
| `.tausik/tausik.db` | **Вы** | **Да.** |

Тестовый набор `tests/test_bootstrap_non_destructive.py` форсит этот контракт. Каждый bootstrap-путь проверяется на то, что он не пишет внутрь `.tausik/`.

## Workflow обновления

1. `git pull` (или обновите фреймворк тем способом, как вы его установили).
2. `python bootstrap/bootstrap.py --no-detect` — обновляет `.claude/`, копирует новые `stacks/`, регенерирует блок `_STACKS_ENUM` в MCP.
3. `tausik stack lint` — валидирует, что ваши override всё ещё парсятся против новой схемы.
4. `tausik stack diff <name>` — для каждого override-стека, sanity-check, что встроенный не изменился способом, который ломает ваши предположения.

## Что может сломать stack-override

Нетривиальное обновление фреймворка *может* инвалидировать override, даже если файл не трогался:

- В схеме появилось обязательное поле. `tausik stack lint` сообщит.
- Поле было переименовано (например `detect[].kind` → `detect[].type`). `lint` сообщит об unknown-field ошибках.
- Цель `extends: "builtin:NAME"` была переименована или удалена. `lint` всплывёт "extends target not found".
- Имя gate перемещено между стеками. Ваш override, ссылающийся на него через `null` (для disable), станет no-op молча — проверьте через `stack export`.

Фреймворк предпочитает аддитивные изменения; ломающие изменения едут в major-версии с миграционной заметкой в changelog'е.

## Когда что-то пошло не так

| Симптом | Что делать |
|---|---|
| Bootstrap падает или warn'ит про `.tausik/stacks/` | Запустите `tausik stack lint`, чтобы увидеть validation-ошибки. |
| `tausik task add --stack X` отвергает стек, который вы определили | Подтвердите, что `.tausik/stacks/X/stack.json` существует и парсится; проверьте `tausik stack list`. |
| Gate перестал срабатывать после обновления | `tausik stack info <name>` показывает активные gates; `stack export <name>` подтверждает порядок merge. |
| Хочется начать заново | `tausik stack reset <name>` удаляет один override; `rm -rf .tausik/stacks/` сносит все. |

## Disaster recovery

Если `.tausik/` повреждён или вы хотите снести локальное состояние, только база данных (`.tausik/tausik.db`) незаменима — всё остальное регенерируется повторным запуском bootstrap. Сделайте бэкап `.tausik/tausik.db` и `.tausik/stacks/` перед чем-либо разрушительным.

## Версионная политика

- **Patch (x.y.Z)** — багфиксы, без изменений API/схемы.
- **Minor (x.Y.0)** — новые возможности, аддитивные миграции БД, API расширяется без break.
- **Major (X.0.0)** — breaking changes API/схемы, миграционная заметка в `CHANGELOG.md` обязательна.

`tausik doctor` после обновления покажет, есть ли drift или проблемы с конфигом.

## См. также

- [Кастомизация](customization.md) — как переопределять без правки фреймворковых файлов.
- [Архитектура](architecture.md) — модель слоёв и владений.
