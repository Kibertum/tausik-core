[English](../en/i18n-strategy.md) | **Русский**

# Стратегия локализации

## Подход

TAUSIK использует **директории для локализации**: `docs/en/` (English) + `docs/ru/` (Russian).

- **Основной язык** для GitHub: English (`README.md`)
- Каждый файл имеет language switcher со ссылкой на другую версию
- Все документы локализованы в обоих направлениях

## Структура

```
README.md          ← English (основной)
README.ru.md       ← Russian

docs/
├── en/            ← English документация (13 файлов)
│   ├── quickstart.md, workflow.md, skills.md, hooks.md
│   ├── cli.md, mcp.md, architecture.md, adding-new-ide.md
│   ├── vendor-skills.md, senar-compliance-matrix.md, i18n-strategy.md
├── ru/            ← Russian документация (13 файлов, зеркало en/)
│   └── ...
└── README.md      ← Навигационный хаб (билингвальный)

references/        ← Агентский контекст (компактные версии для AI)
├── QUICKSTART.md / .en.md
├── architecture.md / .en.md
└── project-cli.md
```

## Что локализуется

| Расположение | RU | EN | Примечание |
|-------------|----|----|------------|
| `README.md` / `README.ru.md` | ✓ | ✓ (основной) | Точка входа для GitHub |
| `docs/en/` + `docs/ru/` (13 файлов) | ✓ | ✓ | Пользовательская документация |
| `references/QUICKSTART.md` / `.en.md` | ✓ | ✓ | Онбординг агента |
| `references/architecture.md` / `.en.md` | ✓ | ✓ | Дизайн системы |

## Что НЕ локализуется

- **CLAUDE.md** — внутренние инструкции проекта, следует языку пользователя
- **CHANGELOG.md** — исторический документ, на оригинальном языке
- **Skills (SKILL.md)** — инструкции агента, EN frontmatter + RU контент
- **CLI help text** — на русском (следует локали пользователя)
- **Комментарии в коде** — на английском
- **references/project-cli.md** — технический справочник, русский

## Как добавить новый язык

1. Создать директорию `docs/{lang}/`
2. Скопировать файлы из `docs/en/`, перевести текст
3. Добавить language switcher: `[English](../en/file.md) | [Язык](../lang/file.md)`
4. Код-блоки, пути и технические термины оставить как есть
5. Обновить `docs/README.md` навигационный хаб
