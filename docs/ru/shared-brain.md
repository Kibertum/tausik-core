# Shared Brain — кросс-проектные знания в Notion

**Статус:** opt-in, pipeline готов, мастер настройки в работе.

Локальная проектная память TAUSIK (`.tausik/tausik.db`) — основной store для всего, что относится к *этому* репозиторию. **Shared Brain** — опциональный второй слой: база знаний в Notion, куда пишутся только **обобщаемые между проектами** знания — дорого добытые архитектурные инсайты, жёсткие подводные камни, стабильные паттерны, и HTTP-кэш, который полезен всем репозиториям.

Разделение намеренное. Локальная БД хранит проектно-специфичные следы (пути к файлам, имена модулей, слаги клиентов) — всё, что может утечь между несвязанными кодовыми базами. Brain хранит то, что ты хотел бы, чтобы свежий агент в *другом* репозитории унаследовал.

## Философия

| Слой | Store | Scope | Пример |
|---|---|---|---|
| Local | `.tausik/tausik.db` | Только этот проект | "auth-middleware.py строка 42 логирует PII — фикс в MR-1234" |
| Brain | Notion databases | Кросс-проектное | "SHA256-хэш проекта избегает утечки имён и уникален для N<1000" |

Ничто идентифицирующее проект не должно попасть в brain. Защита:
1. **Scrubbing linter** отклоняет записи с абсолютными путями, kebab-слагами ≥3 частей, командами `.tausik/tausik`, internal URLs.
2. **Classifier** решает, `local` или `brain` у записи; только `brain`-класс попадает в Notion.
3. **Source Project Hash** — каждая запись несёт `SHA256(canonical_name)[:16]`, так что даже если проектный идентификатор случайно проскочит аудит, читатель Notion не сможет сопоставить хэши с именами проектов без локального реестра.

## Архитектура

```
                     ┌────────────────────┐
                     │  Notion workspace  │
                     │  (4 databases)     │
                     │  decisions         │
                     │  web_cache         │
                     │  patterns          │
                     │  gotchas           │
                     └─────────┬──────────┘
                               │  Notion REST API
                               │  (Bearer + Notion-Version)
              ┌────────────────▼─────────────────┐
              │  scripts/brain_notion_client.py  │  stdlib urllib,
              │  throttle 350ms, 429/5xx retry   │  ноль зависимостей
              └────────────────┬─────────────────┘
                               │
                  ┌────────────┴─────────────┐
                  │                          │
         pages_create             iter_database_query
         (write path)             (pull с дельтой)
                  │                          │
                  │                          ▼
                  │           ┌──────────────────────────┐
                  │           │ scripts/brain_sync.py    │
                  │           │ map Notion→SQLite rows   │
                  │           │ upsert по page_id        │
                  │           │ продвижение sync_state   │
                  │           └────────────┬─────────────┘
                  │                        │
                  │                        ▼
                  │           ┌──────────────────────────┐
                  │           │ ~/.tausik-brain/brain.db │
                  │           │ brain_schema + FTS5      │
                  │           │ unicode61 tokenizer      │
                  │           └────────────┬─────────────┘
                  │                        │
                  │                        ▼
                  │           ┌──────────────────────────┐
                  │           │ scripts/brain_search.py  │
                  │           │ bm25-ранжированный поиск │
                  │           └────────────┬─────────────┘
                  │                        │
                  └────────────┬───────────┘
                               │
                  ┌────────────▼──────────────┐
                  │ scripts/brain_config.py   │
                  │ загрузка и валидация      │
                  │ project hash, token env   │
                  └───────────────────────────┘
```

## Модули (готовы)

| Файл | Назначение |
|---|---|
| [scripts/brain_config.py](../../scripts/brain_config.py) | Парсинг конфига + валидация; `compute_project_hash`, `get_brain_mirror_path` |
| [scripts/brain_schema.py](../../scripts/brain_schema.py) | Local SQLite DDL (4 таблицы + FTS5 + триггеры, `unicode61` токенизатор) |
| [scripts/brain_notion_client.py](../../scripts/brain_notion_client.py) | Stdlib Notion REST клиент (throttle + retry + pagination iterator) |
| [scripts/brain_sync.py](../../scripts/brain_sync.py) | Delta-pull Notion → local; маппинг Notion page JSON → SQLite rows |
| [scripts/brain_search.py](../../scripts/brain_search.py) | Локальный FTS5 поиск с bm25 и SQL `snippet()` |
| [references/brain-db-schema.md](../../references/brain-db-schema.md) | Design-doc — properties, JSON payload примеры, trade-offs |

## Настройка (вручную, пока не вышел `tausik brain init`)

Предпосылка: Notion workspace, который ты контролируешь.

### 1. Создать parent page

В сайдбаре Notion создай новую страницу "TAUSIK Shared Brain" (или любое имя). В ней разместятся 4 базы.

### 2. Создать 4 базы

Как inline databases внутри parent page — или как отдельные страницы:

- `decisions`
- `web_cache`
- `patterns`
- `gotchas`

Полный property-spec каждой — в [references/brain-db-schema.md](../../references/brain-db-schema.md). Минимум на базу: `Name` title, 1-2 text-property, `Source Project Hash` rich text, `Tags` multi-select. Sync терпимо относится к отсутствию необязательных (ставит NULL).

### 3. Создать integration

1. https://www.notion.so/my-integrations → "New integration".
2. Имя: "TAUSIK Brain".
3. Type: Internal.
4. Capabilities: Read, Update, Insert content.
5. Скопируй **internal integration token** (начинается с `secret_`).

### 4. Дать integration доступ к базам

Для каждой из 4 баз: открыть → справа вверху `...` → "Add connections" → выбрать "TAUSIK Brain".

### 5. Экспортировать токен

```bash
export NOTION_TAUSIK_TOKEN='secret_xxx'
```

Windows:

```powershell
setx NOTION_TAUSIK_TOKEN "secret_xxx"
```

### 6. Настроить

Правь `.tausik/config.json` в проекте:

```json
{
  "brain": {
    "enabled": true,
    "notion_integration_token_env": "NOTION_TAUSIK_TOKEN",
    "database_ids": {
      "decisions":  "<uuid из URL базы decisions>",
      "web_cache":  "<uuid>",
      "patterns":   "<uuid>",
      "gotchas":    "<uuid>"
    },
    "project_names": ["имя-проекта-канонически"],
    "ttl_web_cache_days": 30
  }
}
```

UUID базы — в URL Notion: `notion.so/...?v=<viewid>` — 32-символьный hex-id перед `?`. Notion принимает и с дефисами и без.

### 7. Smoke-тест

```python
from brain_config import load_brain, validate_brain, get_brain_mirror_path
from brain_notion_client import NotionClient
from brain_sync import open_brain_db, sync_all
import os

cfg = {"brain": load_brain()}
errors = validate_brain(cfg)
assert not errors, errors

client = NotionClient(os.environ["NOTION_TAUSIK_TOKEN"])
conn = open_brain_db(get_brain_mirror_path(cfg))
result = sync_all(client, conn, cfg["brain"]["database_ids"])
print(result)
```

Ожидание: 4 ключа (decisions/web_cache/patterns/gotchas), каждый — `{fetched: N, upserted: N, last_edited_time: ...}` или `{error: ...}`. На свежем пустом setup все четыре — `{fetched: 0, upserted: 0, last_edited_time: null}`.

## Приватность

1. **Plaintext-имя проекта никогда не уходит с машины.** Единственный per-project идентификатор в brain — `SHA256(canonical_name)[:16]`. Canonical name берётся из `project_names[0]` локального `.tausik/config.json` и сам никуда не отсылается.
2. **Scrubbing linter** (задача `brain-scrubbing`, в планах) будет перехватывать каждую запись до клиента. Отклоняет: абсолютные Windows/POSIX пути, internal-domain URLs, любой текст, совпавший с regex-списком `brain.private_url_patterns`, kebab-слаги похожие на internal-идентификаторы.
3. **Classifier** (задача `brain-classifier`, в планах) выбирает `local` vs `brain` по записи. Только `brain`-класс пушится. Консервативный default: неоднозначное → `local`.
4. **Можно отозвать в любой момент.** Отозвать integration в Notion или убрать `NOTION_TAUSIK_TOKEN`; следующий sync/write падает с `NotionAuthError`, а локальное зеркало продолжает работать для read-only поиска.

## Edge cases / failure modes

| Сценарий | Что происходит | Что делать |
|---|---|---|
| **Отозвали integration token** | Следующий API-вызов бросает `NotionAuthError` (401/403) без retry | Восстановить токен; данные не теряются — local mirror цел |
| **Rate-limit 429** | Клиент ретраит с учётом `Retry-After`; исчерпано → `NotionRateLimitError` | Обычно автоматом. Если упорно: снизить частоту sync |
| **Offline / DNS fail** | `URLError` ретраится backoff-ом; исчерпано → `NotionError` | `brain_search.search_local()` работает по локальному зеркалу |
| **Content >180 KB** | В property `[see page body]`; полный текст в child blocks | Держи заметки компактными; большие web-страницы труncate-ятся |
| **Чувствительные данные проскочили scrubbing** | Удалить Notion page руками; следующий pull заметит 404 | Улучшить `private_url_patterns` regex |
| **Schema drift баз** | Отсутствующие properties читаются как NULL; лишние игнорируются | Добавить недостающие properties (шаг 2) |
| **Два проекта с одинаковым canonical name** | Коллизия хэшей — записи мешаются в Notion views | Переименовать один в `project_names[]` |

## Плюсы / минусы

| Плюсы | Минусы |
|---|---|
| Пиши один раз — ищи по всем проектам | Нужен Notion-аккаунт + setup |
| Notion UI для просмотра/правки | Rate limits (3 req/s) на bulk writes |
| bm25 local search работает offline | Надо управлять integration-токеном |
| Ноль внешних Python-зависимостей (stdlib urllib) | Нужно активно фильтровать что "обобщаемое" |
| Privacy-preserving hash, ноль plaintext имён | До выхода `brain-scrubbing` возможны случайные утечки |
| FTS5 поддерживает кириллицу / диакритику | Нет shared-team режима (single-user в v1) |

## Альтернатива: Outline (TODO)

Outline (https://www.getoutline.com/) — self-hosted markdown-first альтернатива. Потенциальные плюсы: нет rate-limit-а, на который нельзя повлиять; проще data-модель; open-source. Минусы: нет native-понятия "databases" — всё markdown-страницы, фильтры/views беднее. Не реализовано; трекается отдельно.

## Что вошло в этот релиз

- Полный read-path (Notion → pull → mirror → bm25 search) — **end-to-end offline-тестирован** через mocked `urlopen`
- Типизированная иерархия ошибок (`NotionAuthError`, `NotionNotFoundError`, `NotionRateLimitError`, `NotionServerError`)
- 102/102 новых тестов зелёные; 0 внешних зависимостей

## Ещё в плане

`brain-mcp-tools-write`, `brain-mcp-tools-read`, `brain-mcp-server-wiring`, `brain-webfetch-hook`, `brain-classifier`, `brain-scrubbing`, `brain-decide-auto-route`, `brain-search-proactive`, `brain-skill-ui`, `brain-project-registry`, `brain-init-wizard`, `brain-fallback-offline`, `brain-notion-space` (ручное), `brain-integration-token` (ручное).
