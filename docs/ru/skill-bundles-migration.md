**Русский** | [English](/docs/skill-bundles-migration)

# Миграция на Skill Bundles (v1.4)

Короткое чтиво для пользователей у кого установлен хоть один из 5 vendor скиллов удалённых из `tausik-skills`. Если ты никогда не запускал `tausik skill install go|next|diff|onboard|init`, **ничего не меняется** — bundles чисто аддитивны.

## Что изменилось в v1.4

1. **5 vendor скиллов удалены** из `skills-official/` и `registry.json`: `go`, `next`, `diff`, `onboard`, `init`. Каждый дублировал built-in функционал (см. таблицу замен в [Skill Bundles](skill-bundles.md)).
2. **Новый `tausik skill bundle` CLI** для массовой установки/удаления — см. [Skill Bundles](skill-bundles.md).
3. **Физической реструктуризации** `skills-official/` НЕТ — каждый остальной скилл сохраняет свой путь. `tausik skill install <name>` работает для 20 оставшихся скиллов.

## Если у тебя установлен любой из 5 удалённых скиллов

### Шаг 1 — Посмотри что у тебя

```bash
.tausik/tausik skill list
```

В секциях `[ACTIVE]` и `[VENDORED]` ищи любые из: `go`, `next`, `diff`, `onboard`, `init`.

### Шаг 2 — Удали их

```bash
.tausik/tausik skill uninstall go        # повтори для каждого имени
```

Это убирает скилл из `.claude/skills/` и из `installed_skills` в `.tausik/config.json`. Vendor cache под `.tausik/vendor/tausik-skills/` общий с другими скиллами — оставь его в покое.

### Шаг 3 — Переключись на замену

| Удалён | Что использовать |
|--------|------------------|
| `go` | Запусти `/plan <free-form description>` потом `/task <slug>` — тот же one-phrase flow с QG-0 enforcement. |
| `next` | Запусти `.tausik/tausik task next` — без установки скилла. |
| `diff` | `git diff` напрямую или `/review diff` (стандартный `/review` уже понимает diff'ы). |
| `onboard` | Запусти `/start` (built-in) — покрывает состояние проекта, последнюю работу, suggested next. Для первичной настройки fresh проекта — `python bootstrap/bootstrap.py --init`. |
| `init` | Запусти `python bootstrap/bootstrap.py --init` — создаёт `.tausik/`, `.claude/`, project DB. Без скилла. |

### Шаг 4 — Re-bootstrap (только если у тебя локальная копия `skills-official/`)

Если ты трекаешь source repo (TAUSIK контрибьюторы), pull последнее и re-bootstrap чтобы удалённые директории скиллов пропали из `.claude/`:

```bash
git pull
python bootstrap/bootstrap.py --ide claude
```

Consumer проекты (которые vendor'или `tausik` через bootstrap script) подхватят изменение на следующий `python .tausik-lib/bootstrap/bootstrap.py` автоматически — ручная чистка не нужна.

## А если third-party repo всё ещё ссылается на deprecated скилл?

Bundle install CLI защитный: когда натыкается на deprecated имя, печатает

```
[SKIP] <name>: deprecated: <migration message>
```

и продолжает с остальными скиллами bundle. Ничего не ломается — install просто пропускает deprecated запись. Если ведёшь свой bundles файл, удали deprecated имена из `bundles.<name>.skills` чтобы избавиться от warning'а.

## Почему именно эти 5

Все пять дублировали функционал который уже есть в built-in core скиллах или CLI. Удаление:

- Срезает ~15-20 KB vendor surface которую пользователи должны были осмысливать.
- Упрощает вопрос "какой скилл использовать" — каждый оставшийся vendor скилл закрывает что-то чего core не делает.
- Убирает install/activate трение для поведения которое у агента есть с первого дня.

## Q: Список bundles потом изменится?

Push маркетплейса `tausik-skills` (публичная версия `bundles.json`) **отложен до релиза v1.4** по polish мораторию. Когда выйдет публично, 6 bundles описанные здесь — это v1.4 baseline. Будущие версии могут добавлять bundles (пустой `ru-locale` слот — очевидный следующий кандидат); существующие bundles стабильны.
