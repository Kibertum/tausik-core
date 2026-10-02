**Русский** | [English](../en/skill-bundles.md)

# Bundles навыков

<!-- doc-map: reader=user; zone=ide-and-skills -->

Bundle навыков — необязательная группа, которую объявляет репозиторий навыков. Один CLI-вызов ставит всех участников, поэтому используйте bundle только когда проекту нужна вся группа; иначе ставьте один навык и не расширяйте промпт без пользы.

> **Откуда берутся бандлы (изменено в v1.8):** состав бандла принадлежит
> магазину, который поставляет скиллы. `bundles.json` едет *внутри*
> репозитория формата tausik-skills, рядом с его `tausik-skills.json`, а
> `tausik skill bundle` читает те репозитории, которые вы добавили командой
> `tausik skill repo add`.
>
> До v1.8 резолв искал только каталог `skills-official/` рядом с чекаутом
> ядра. Этот каталог существует при разработке фреймворка и не существует в
> поднятом вами проекте, поэтому у всех реальных пользователей команда падала
> с «no bundles manifest». Он сохранён только как путь для разработки.
>
> **Бандлы с одинаковым именем в разных магазинах ОБЪЕДИНЯЮТ свои списки
> скиллов.** Именно это сохраняет приватность приватного магазина: публичный
> может объявить бандл и оставить его пустым, а приватный — наполнить, и ни
> один манифест не называет содержимое другого. Признак placeholder снимается
> с бандла в тот момент, когда его кто-нибудь наполнил. Вариант «держать
> перечень в ядре» отвергнут ровно по этой причине: ядро зеркалится публично,
> и перечень членов на стороне ядра означал бы назвать приватные скиллы в
> публикуемом файле.

## Доступность

Официальный магазин TAUSIK не публикует bundles: в нём только `docs`, `excel` и `pdf`, которые устанавливаются по одному. Сторонние репозитории могут публиковать bundles. После добавления такого репозитория выполните `skill bundle list`. Core не копирует названия и состав bundles.

## CLI

```bash
.tausik/tausik skill bundle list                    # все bundles + counts
.tausik/tausik skill bundle list --json             # для скриптов

.tausik/tausik skill bundle show <name>             # содержимое bundle
.tausik/tausik skill bundle show <name> --json

.tausik/tausik skill bundle install <name>           # ставит всех участников
.tausik/tausik skill bundle uninstall <name>         # удаляет всех участников
```

`bundle install` переиспользует существующий `tausik skill install <name>` pipeline по каждому скиллу — тот же vendor cache, тот же pip resolver, тот же activation. Установка bundle:

- Маршрутизирует каждый скилл через стандартный install code path (per-skill safeguards остаются).
- Продолжает после per-skill ошибки — одна missing dep не аборт остальные. Ошибки идут как `[ERR]` строки в отчёте.
- Пропускает имена, помеченные репозиторием как deprecated, и показывает его migration message.
- Для placeholder bundle возвращает одну строку `placeholder` и выходит без установки.

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
