**Русский** | [English](/docs/skill-bundles)

# Bundles навыков

Bundle навыков — это логическая группировка vendor скиллов из `tausik-skills` (официальный `Kibertum/tausik-skills` repo, в dev зеркало в `skills-official/`). Один CLI вызов ставит все скиллы bundle — удобно подобрать набор под домен проекта (интеграции, извлечение данных, deep quality), не запоминая имена.

> **Статус (v1.4.0):** bundles конфигурируются локально — каждый consumer проект после ребутстрапа получает `skills-official/bundles.json` и `tausik skill bundle` CLI. Сам push маркетплейса в `github.com/Kibertum/tausik-skills` **отложен до релиза v1.4** (мораторий polish запрещает публичные push'и). Локальный CLI работает против in-tree `skills-official/` зеркала.

## Шесть bundles

| Bundle | Скиллы | Когда ставить |
|--------|--------|---------------|
| `integrations` | `jira`, `bitrix24`, `confluence`, `sentry` | Проекты с внешними сервисами: ticket workflows, CRM, docs publishing, error monitoring. Каждый скилл требует env credentials. |
| `data-formats` | `excel`, `pdf`, `markitdown` | Document-processing проекты: read/extract/convert бинарных форматов. |
| `quality-pro` | `audit`, `security`, `optimize`, `zero-defect`, `ultra` | Когда "вроде работает" — не приемлемая планка: security-sensitive код, perf-боттлнеки, precision-mode работа. |
| `automation` | `run`, `loop-task`, `dispatch` | Batch / loop / multi-worker workflows — автономное выполнение сверх single-task. |
| `workflow-helpers` | `daily`, `retro`, `presale`, `skill-test`, `docs` | Продуктивность, ретроспективы, presale estimation, doc-генерация, meta tooling. |
| `ru-locale` | *(пустой placeholder)* | Зарезервирован для RU-specific скиллов. Будет наполнен по мере появления. |

## CLI

```bash
.tausik/tausik skill bundle list                    # все bundles + counts
.tausik/tausik skill bundle list --json             # для скриптов

.tausik/tausik skill bundle show integrations       # содержимое bundle
.tausik/tausik skill bundle show integrations --json

.tausik/tausik skill bundle install integrations    # ставит все 4 скилла
.tausik/tausik skill bundle uninstall integrations  # удаляет все 4
```

`bundle install` переиспользует существующий `tausik skill install <name>` pipeline по каждому скиллу — тот же vendor cache, тот же pip resolver, тот же activation. Установка bundle:

- Маршрутизирует каждый скилл через стандартный install code path (per-skill safeguards остаются).
- Продолжает после per-skill ошибки — одна missing dep не аборт остальные. Ошибки идут как `[ERR]` строки в отчёте.
- Пропускает deprecated имена с явным migration сообщением (см. "Удалённые скиллы" ниже).
- Для `ru-locale` placeholder возвращает одну `placeholder` строку и выходит ничего не установив.

## Удалённые скиллы (deprecated)

Пять скиллов удалены из `skills-official/` и `registry.json` в v1.4 — дублировали built-in функционал.

| Удалён | Замена |
|--------|--------|
| `go` | Используй `/plan` + `/task` (built-in с QG-0 enforcement). |
| `next` | Используй CLI `tausik task next` (без установки скилла). |
| `diff` | `git diff` + `/review` (уже анализирует diff'ы). |
| `onboard` | Built-in `/start` для session onboarding; первичный setup — `python bootstrap/bootstrap.py --init`. |
| `init` | Первичная настройка — `python bootstrap/bootstrap.py --init`. |

Если попытаешься установить deprecated скилл через `tausik skill bundle install <bundle>` (бывает если устаревший third-party manifest всё ещё ссылается), CLI напечатает `[SKIP] <name>: deprecated: <migration message>` и продолжит с остальными скиллами bundle.

Для шагов миграции если у тебя уже стоят удалённые 5 скиллов локально — см. [Skill Bundles Migration](skill-bundles-migration.md).

## Свой кастомный bundles файл

Если ведёшь собственный skill repo, положи `bundles.json` рядом с `tausik-skills.json`. Schema:

```json
{
  "version": 1,
  "bundles": {
    "<bundle-name>": {
      "title": "Human-readable title",
      "description": "One-paragraph description.",
      "skills": ["skill-a", "skill-b"],
      "placeholder": false
    }
  },
  "deprecated": {
    "old-skill-name": "Migration message при попытке install bundle с этим именем."
  }
}
```

- `bundles.<name>.skills` — список имён скиллов которые должны существовать как `<repo>/<skill-name>/SKILL.md`.
- `bundles.<name>.placeholder = true` делает install/uninstall no-op'ом (зарезервировать слот под будущий bundle).
- `deprecated` записи advisory — влияют только на сообщение при bundle install; CLI ничего не удаляет на основе этого.

## Куда дальше

- **[Vendor skills](vendor-skills.md)** — repo trust, формат manifest, three-tier system
- **[Skill ecosystem](skill-ecosystem.md)** — как bundles вписываются с core skills + Claude-native sub-agents
- **[Skill Bundles Migration](skill-bundles-migration.md)** — для пользователей с установленными deprecated 5 скиллами
