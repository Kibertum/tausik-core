[English](../en/skill-profiles.md) | **Русский**

# Профили skills и каталог `variants/` (v1.4)

Обычно skill — один файл **`SKILL.md`**. Если поведение зависит от хоста (Claude / Codex / обёртка GPT) и **не нужно дублировать весь skill**, используйте **оверлеи профиля**.

## Структура

```
agents/skills/<skill-name>/
  SKILL.md              # Общие инструкции + YAML frontmatter
  variants/
    claude.md           # Фрагмент, если профиль разрешился в claude
    codex.md            # Фрагмент для codex
```

## Frontmatter (опционально)

| Поле | Смысл |
|------|--------|
| `profile_fallback` | Если для запрошенного профиля **нет** файла `variants/<profile>.md`, один раз попробовать этот профиль для поиска оверлея (slug: нижний регистр, `a-z0-9-`). |

Остальные поля TAUSIK (`name`, `description`, `context`, `effort`, …) без изменений.

## Алгоритм разрешения

1. Загрузить **`SKILL.md`** как базу (включая frontmatter).
2. Если профиль не передан → только база.
3. Если есть **`variants/<запрошенный>.md`** → дописать его тело к базе (разделитель `<!-- tausik-profile:<slug> -->`).
4. Иначе, если задан **`profile_fallback`** и есть **`variants/<fallback>.md`** → дописать этот оверлей.
5. Иначе → только база; **неизвестный профиль не вызывает ошибки**.

Реализация: `scripts/skill_profile.py` (`merge_skill_markdown`, `resolve_variant_overlay`).

## Пример

Каталог **`agents/skills/_profile-demo/`** (эталонная структура — не копируется в IDE; префикс `_`): общее тело и **`variants/claude.md`**, **`variants/codex.md`**. Запрос профиля `gpt` при `profile_fallback: claude` подставит оверлей Claude, если нет `variants/gpt.md`.
