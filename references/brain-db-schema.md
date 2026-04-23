# Brain Notion Databases — Schema v1

Design-doc для эпика `shared-brain`. Фиксирует структуру 4 Notion databases, которые образуют кросс-проектную базу знаний TAUSIK: `decisions`, `web_cache`, `patterns`, `gotchas`. Все проекты пользователя пишут сюда обобщаемые знания; приватная «суть» проекта остаётся в локальной `.tausik/tausik.db`.

Статус: **design-only**. Этот документ не содержит кода; реализация — в задачах `brain-notion-rest-client`, `brain-local-schema`, `brain-mcp-tools-*`.

## 1. Зачем именно 4 базы

Альтернатива — одна «flat»-база с дискриминатором `type`. Отвергнута: в Notion UI теряются нативные фильтры/views по колонкам (каждая сущность имеет свой набор полей: у `gotchas` есть `Wrong Way` / `Right Way`, у `web_cache` нет). Цена — сложнее pull-sync (4 курсора вместо одного), но это единичная стоимость в коде клиента.

Трёх-табличная альтернатива (слить `patterns` + `gotchas`) тоже отвергнута: противоположная семантика (one is "how to", other is "how NOT to") размывает поисковую выдачу.

## 2. Privacy-контур

Цель: по содержимому brain нельзя определить **какие именно проекты** пользуется агент. Из этого следуют инварианты:

- В каждой записи есть поле `Source Project Hash` = `SHA256(project_name_canonical)[:16]` — 16 hex-символов = 64 bit, коллизии для N=1000 проектов имеют вероятность ≈ 2.7e-14. Достаточно для уникальной идентификации без раскрытия имени.
- `project_name_canonical` — нормализованное имя проекта: `name.lower().strip().replace(" ", "-")`. Фиксируется в момент регистрации проекта в `~/.tausik-brain/projects.json` (задача `brain-project-registry`).
- Проект **никогда** не пишет в brain собственное имя, пути к файлам, имена приватных модулей, internal URLs, или любые values, которые попадут в `.tausik/` как `scope` или `notes`. Фильтрация — задача `brain-scrubbing` (pre-write linter).
- Hash **не обратим** без словаря всех канонических имён. Hash нельзя использовать для атрибуции решения конкретному проекту «со стороны», только внутри пользователя, у которого есть реестр.

Почему хэш, а не plaintext: если пользователь в будущем откроет integration на команду, hash не раскроет, что условный проект `kareta-jira-workspace` вообще существует.

## 3. Общие ограничения Notion API (v2022-06-28)

| Ограничение | Значение | Последствие для схемы |
|---|---|---|
| Rate limit | 3 req/s (burst-лимит, но throttle строгий) | клиент ждёт ≥350 ms между writes |
| `rich_text` длина одного блока | 2000 символов | длинный `Content` разбивается на N `rich_text`-элементов в массиве |
| `rich_text` кол-во блоков в property | ~100 | если контент >200 KB — писать как child-blocks на странице, в свойстве оставлять ссылку |
| `multi_select` options | ~100 на property | при приближении к лимиту — миграция на relation-базу `tags` (v2, пока не делаем) |
| `title` длина | 2000 символов | усекаем заголовок, полный вариант — в `Content`/`Description` |
| pagination | cursor-based, `start_cursor` + `has_more` | pull-sync делает while-loop до исчерпания |
| Error `409 Conflict` | конкурентная запись | не должна возникать для single-writer клиента; retry |
| Error `429` / `502` / `503` / `504` | rate-limit / transient | exponential backoff с jitter, max 5 retries |

## 4. Databases

### 4.1 `decisions` — архитектурные решения

Хранит обобщаемые решения: «выбрали urllib вместо requests — вот контекст и почему».

| Property | Notion type | Обязат. | Назначение |
|---|---|---|---|
| `Name` | title | да | Краткая формулировка решения (≤200 chars) |
| `Context` | rich_text | да | Что за проблема/ситуация была |
| `Decision` | rich_text | да | Что решили делать |
| `Rationale` | rich_text | да | Почему именно так |
| `Tags` | multi_select | нет | Домены: `architecture`, `testing`, `db`, `security`, `api`, `devops`, `performance`, `dx`, … |
| `Stack` | multi_select | нет | `python`, `typescript`, `go`, `rust`, `java`, … |
| `Date` | date | да | Когда решение принято (ISO `YYYY-MM-DD`) |
| `Source Project Hash` | rich_text | да | 16 hex-символов |
| `Generalizable` | checkbox | да | Default `true`. Если агент ставит `false` — запись помечается как «зря попала», будет отсекаться на sync |
| `Superseded By` | url | нет | Ссылка на другую запись `decisions`, если решение заменили |

**JSON payload (`POST /v1/pages`):**

```json
{
  "parent": {"database_id": "<decisions_db_id>"},
  "properties": {
    "Name": {
      "title": [{"text": {"content": "Использовать urllib вместо requests"}}]
    },
    "Context": {
      "rich_text": [{"text": {"content": "Нужен HTTP-клиент для Notion API в TAUSIK, convention #19 (zero external deps)."}}]
    },
    "Decision": {
      "rich_text": [{"text": {"content": "Реализовать клиент на stdlib `urllib.request` + `http.client`, без `requests`/`httpx`."}}]
    },
    "Rationale": {
      "rich_text": [{"text": {"content": "Добавление зависимости ломает zero-deps принцип и усложняет bootstrap. Ценой ~100 LOC boilerplate получаем полный контроль над throttle/retry."}}]
    },
    "Tags": {"multi_select": [{"name": "architecture"}, {"name": "dx"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {
      "rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]
    },
    "Generalizable": {"checkbox": true}
  }
}
```

### 4.2 `web_cache` — кэш HTTP-ответов (WebFetch/WebSearch)

Каждый раз, когда агент делает `WebFetch` или `WebSearch`, PostToolUse-хук (задача `brain-webfetch-hook`) пишет сюда запись. Перед новым запросом агент сначала делает `brain_search_web_cache` — если есть свежая запись (не старше TTL), возвращает её без сетевого вызова.

| Property | Notion type | Обязат. | Назначение |
|---|---|---|---|
| `Name` | title | да | Title страницы или исходный запрос WebSearch (≤200 chars) |
| `URL` | url | да для WebFetch | Канонический URL; для WebSearch пусто |
| `Query` | rich_text | да для WebSearch | Поисковый запрос; для WebFetch дублирует URL |
| `Content` | rich_text (N blocks) | да | Markdown-контент. Если >180 KB — хранится в child-blocks страницы, а в property остаётся маркер `[see page body]` |
| `Fetched At` | date (with time) | да | ISO `YYYY-MM-DDTHH:MM:SS.000Z` |
| `TTL Days` | number | да | Default 30. `docs.*` — 90, SERP — 7, changelog/release pages — 3 |
| `Domain` | select | да | Хост URL (для WebSearch — `serp:google` / `serp:ddg`) |
| `Tags` | multi_select | нет | Темы (`notion-api`, `python-stdlib`, `sqlite-fts`) |
| `Source Project Hash` | rich_text | да | Какой проект впервые закешировал (для аудита, не для ACL) |
| `Content Hash` | rich_text | да | SHA256(content)[:16] — dedup при pull |

**Why `Content Hash`:** если тот же URL забирают 2 проекта, получим 2 записи с идентичным контентом. Классификатор на pull-sync смотрит `Content Hash` и игнорирует дубликат.

**JSON payload:**

```json
{
  "parent": {"database_id": "<web_cache_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "Notion API — Create a page"}}]},
    "URL": {"url": "https://developers.notion.com/reference/post-page"},
    "Query": {"rich_text": [{"text": {"content": "https://developers.notion.com/reference/post-page"}}]},
    "Content": {
      "rich_text": [
        {"text": {"content": "# Create a page\n\nCreates a new page..."}},
        {"text": {"content": "... (chunk 2, до 2000 символов)"}}
      ]
    },
    "Fetched At": {"date": {"start": "2026-04-23T10:15:00.000Z"}},
    "TTL Days": {"number": 90},
    "Domain": {"select": {"name": "developers.notion.com"}},
    "Tags": {"multi_select": [{"name": "notion-api"}, {"name": "docs"}]},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Content Hash": {"rich_text": [{"text": {"content": "9f8e7d6c5b4a3210"}}]}
  }
}
```

### 4.3 `patterns` — проверенные паттерны

Reusable рецепты: «как правильно X в Y». Отличие от `decisions` — паттерн универсален, `decisions` контекстно-зависим.

| Property | Notion type | Обязат. | Назначение |
|---|---|---|---|
| `Name` | title | да | Короткое название паттерна |
| `Description` | rich_text | да | Что делает, какую проблему решает |
| `When to Use` | rich_text | да | Контекст применения (и когда НЕ применять) |
| `Example` | rich_text | да | Код-пример; для длинных — child-blocks |
| `Tags` | multi_select | нет | `async`, `di`, `testing`, `error-handling`, `caching`, … |
| `Stack` | multi_select | да | Язык/фреймворк — где применим |
| `Source Project Hash` | rich_text | да | Откуда пришло (аудит) |
| `Date` | date | да | Когда добавлено |
| `Confidence` | select | да | `experimental` (1 применение) / `tested` (2–3) / `proven` (4+) |

**Пример payload:**

```json
{
  "parent": {"database_id": "<patterns_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "Mixin composition вместо наследования для Service Layer"}}]},
    "Description": {"rich_text": [{"text": {"content": "Разбить большой сервис на mixin'ы по функциональности (TaskMixin, KnowledgeMixin). Главный класс наследует все."}}]},
    "When to Use": {"rich_text": [{"text": {"content": "Когда service-класс >400 строк и имеет >2 ортогональных групп методов. НЕ применять если методы имеют общее состояние — это сигнал к отдельным сервисам."}}]},
    "Example": {"rich_text": [{"text": {"content": "class ProjectService(SessionMixin, HierarchyMixin, TaskMixin):\n    def __init__(self, backend):\n        self.backend = backend"}}]},
    "Tags": {"multi_select": [{"name": "architecture"}, {"name": "oop"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Confidence": {"select": {"name": "proven"}}
  }
}
```

### 4.4 `gotchas` — ловушки и dead-ends

| Property | Notion type | Обязат. | Назначение |
|---|---|---|---|
| `Name` | title | да | Краткое описание проблемы |
| `Description` | rich_text | да | Что именно происходит, как проявляется |
| `Wrong Way` | rich_text | да | Что НЕ работает (код/подход) |
| `Right Way` | rich_text | да | Что работает |
| `Tags` | multi_select | нет | — |
| `Stack` | multi_select | да | — |
| `Source Project Hash` | rich_text | да | — |
| `Date` | date | да | — |
| `Severity` | select | да | `low` (косметика) / `medium` (потерян час) / `high` (≥4 часов дебага) |
| `Evidence URL` | url | нет | Ссылка на GitHub issue / StackOverflow / commit |

**Пример payload:**

```json
{
  "parent": {"database_id": "<gotchas_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "SQLite FTS5 MATCH с кириллицей без unicode61 tokenizer ломается"}}]},
    "Description": {"rich_text": [{"text": {"content": "Default ascii tokenizer в FTS5 не знает про кириллицу — MATCH по слову на русском не возвращает результаты."}}]},
    "Wrong Way": {"rich_text": [{"text": {"content": "CREATE VIRTUAL TABLE fts USING fts5(content);"}}]},
    "Right Way": {"rich_text": [{"text": {"content": "CREATE VIRTUAL TABLE fts USING fts5(content, tokenize='unicode61 remove_diacritics 2');"}}]},
    "Tags": {"multi_select": [{"name": "sqlite"}, {"name": "fts"}, {"name": "i18n"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Severity": {"select": {"name": "medium"}},
    "Evidence URL": {"url": "https://sqlite.org/fts5.html#unicode61_tokenizer"}
  }
}
```

## 5. Delta-pull и индексы

Notion возвращает системное поле `last_edited_time` на каждой странице (ISO timestamp, с миллисекундами). Схема pull-sync:

1. Клиент хранит `sync_state.last_pull_at` (per-category) в локальной SQLite.
2. Query: `POST /v1/databases/<id>/query` с `filter` по `last_edited_time >= last_pull_at` и `sort` по `last_edited_time` asc.
3. Цикл пагинации по `has_more`/`next_cursor`.
4. После успешного прохода обновляет `last_pull_at` = `max(last_edited_time)` из batch.

**Зачем asc а не desc:** чтобы при падении посередине batch клиент не ломал монотонность — последний обработанный timestamp = high-water mark.

**Notion views** (создаются вручную в Notion при setup, не через API):
- `By Date` — sort desc по `Date`, дефолт.
- `By Stack` — group by `Stack`.
- `By Project Hash` — group by `Source Project Hash` (для личной ретроспективы).
- `High Severity` (gotchas) — filter `Severity = high`.
- `Fresh cache` (web_cache) — filter `Fetched At > now-7d`.

Views не влияют на API и не требуются коду; документируем их в `brain-onboarding-docs` как рекомендуемый пост-setup.

## 6. Pagination и rate-limit — на стороне клиента

- Все writes проходят через единую throttle-очередь с интервалом ≥350 ms.
- 429 → `Retry-After` header + exponential backoff `min(2^attempt, 30)` с jitter ±20%.
- 5xx → backoff как на 429, max 5 попыток.
- 404 на `pages.retrieve` для известного page_id → запись удалить из local mirror (ISR).
- 401/403 → немедленная ошибка, disable brain-flag до следующего wizard-запуска.

## 7. Trade-offs

| Решение | Альтернатива | Почему выбрано |
|---|---|---|
| 4 отдельных базы | 1 flat-база с `type` | Нативные Notion UI / filters; schema-driven properties; acceptable sync-overhead |
| `multi_select` для `Tags` | relation на `tags`-базу | Дешевле (1 API call вместо 2), проще; лимит 100 options пока не близко |
| `rich_text` chunks для Content | child-blocks страницы | Chunks — для ≤180 KB, дёшево; блоки — только для >180 KB (редкий случай) |
| `SHA256(name)[:16]` hash | Plaintext имя / UUID4 | Privacy без раскрытия клиентов; стабильный при повторной генерации |
| Отдельное `Content Hash` | Хэшировать URL | URL → разный контент в разное время (SPA, A/B тесты); content-hash надёжнее для dedup |
| `Confidence` как select | Число (count of uses) | UI фильтрация проще, семантика яснее; для point-in-time inflation лучше использовать отдельный `Uses` number в v2 |
| `Generalizable` checkbox | Не хранить приватные решения вообще | Классификатор может ошибиться → ставим флаг и фильтруем на sync; легче чем полный rollback |

## 8. Negative scenarios (обязательные fallback'и в коде)

| Сценарий | Реакция |
|---|---|
| Integration не имеет доступа к database (403) | Disable brain глобально, лог + сообщение пользователю «run brain init», fallback на local-FTS |
| Пропавший database_id (404 на query) | Disable brain, то же сообщение |
| Rate-limit 429 | Ретрай по backoff; если ≥5 подряд — temp disable на 1 минуту |
| Network timeout / DNS fail | Fallback на local-FTS mirror, уведомление в UI |
| `Generalizable = false` детектнут после записи | Pull-sync игнорирует такие записи; в Notion запись остаётся для ручной ревизии |
| Sensitive data проскочило scrubbing | Ручное удаление в Notion → local pull удалит при следующем sync (404 на retrieve) |
| Content >180 KB | Property: `[see page body]` + rich_text chunks с урезанной версией; полный текст в child-blocks |
| Title >2000 chars | Усечение до 200 chars + «…» + полный вариант в Description/Content |

## 9. Что **не** включено в v1 (out of scope)

- Relation-базы для Tags/Stack — ждём сигнала приближения к 100 options.
- Version-history entries — Notion UI показывает page history, API-level переписать пока не нужно.
- Cross-entity links (patterns → gotchas) — отдельная relation-property, в v2.
- Attachments (images, diagrams) — отдельная задача, требует обработку upload API.
- Shared access (команда) — однопользовательская v1.
- Full-text поиск по Notion API — используем только query + local FTS5 mirror для поиска.

## 10. Связь с локальной схемой

Локальный SQLite mirror (`~/.tausik-brain/brain.db`, задача `brain-local-schema`) повторяет эти 4 таблицы 1:1:
- Каждая колонка Notion → колонка SQLite с совместимым типом (rich_text → TEXT, multi_select → JSON TEXT array, date → TEXT ISO, number → INTEGER/REAL, checkbox → INTEGER 0/1, select → TEXT).
- Primary key — `notion_page_id` (UUID-строка от Notion).
- `last_edited_time TEXT` индексируется для delta-pull.
- Для каждой таблицы — FTS5 virtual table с `content=<table>`, `content_rowid=<pk>` и полями `Name`/текстовыми свойствами.
- Таблица `sync_state` (PK=category) хранит `last_pull_at` и `last_error`.

Детали локальной схемы — в `references/brain-local-schema.md` (задача `brain-local-schema`).
