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
| [brain-db-schema.md](brain-db-schema.md) | Design-doc — properties, JSON payload примеры, trade-offs |

## Настройка

Предпосылка: Notion workspace, который ты контролируешь.

### 1. Создать parent page

В сайдбаре Notion создай страницу "TAUSIK Shared Brain" (или любое имя). Wizard создаст под ней 4 базы.

### 2. Создать integration

1. https://www.notion.so/my-integrations → "New integration".
2. Имя: "TAUSIK Brain".
3. Type: Internal.
4. Capabilities: Read, Update, Insert content.
5. Скопируй **internal integration token** (начинается с `ntn_` или legacy `secret_`).

### 3. Дать integration доступ к parent page

Открой страницу "TAUSIK Shared Brain" → справа вверху `...` → "Add connections" → выбери "TAUSIK Brain". Wizard создаёт базы под этой страницей — integration должен её видеть.

### 4. Сохранить токен (выбери одно — v1.3.2+ поддерживает каскад)

Notion-токен резолвится в таком порядке приоритета:

1. **`os.environ[NOTION_TAUSIK_TOKEN]`** — env var. Высший приоритет. Подходит для CI / shared машин.
2. **`.tausik/.env`** — project-local `KEY=VALUE` файл. **Рекомендуется для индивидуальных разработчиков**: gitignored, не требует правки shell-rc, переживает ребут.
3. **`brain.notion_integration_token`** в `.tausik/config.json` — выдаёт stderr warning ("stored inline; prefer .tausik/.env"). Разрешено, но не рекомендуется.

**Рекомендуемый путь — `.tausik/.env`:**

```bash
echo "NOTION_TAUSIK_TOKEN=ntn_xxx" >> .tausik/.env
```

**Если предпочитаешь env-переменную:**

```bash
# Linux / macOS — для persistence добавь в ~/.bashrc / ~/.zshrc / ~/.profile
export NOTION_TAUSIK_TOKEN='ntn_xxx'
```

```powershell
# Windows — User-level (переживёт ребут, IDE restart подхватит)
[System.Environment]::SetEnvironmentVariable('NOTION_TAUSIK_TOKEN', 'ntn_xxx', 'User')
# Применить к текущей PowerShell-сессии:
$env:NOTION_TAUSIK_TOKEN = 'ntn_xxx'
```

После установки **перезапусти IDE** (Claude Code / Cursor / ...), чтобы MCP-subprocess подхватил новый env. С `.tausik/.env` IDE-restart не нужен — токен читается на каждом brain-вызове.

### 5. Запустить wizard

> **Один комплект из 4 баз на workspace, общий для всех проектов.** Приватность по проектам обеспечивает колонка `Source Project Hash` в каждой строке, а НЕ создание отдельных копий 4 баз для каждого проекта. Wizard это требование защищает (см. "Частые ошибки" ниже).

**Первый проект — создаём 4 базы:**

```bash
.tausik/tausik brain init
```

Non-interactive (для CI / скриптов):

```bash
.tausik/tausik brain init \
  --parent-page-id 'abc123...' \
  --token-env NOTION_TAUSIK_TOKEN \
  --project-name my-project \
  --yes --non-interactive
```

Parent page ID — 32-символьный hex после `notion.so/...-` в URL (с дефисами или без). Wizard:

1. **Pre-flight workspace search** (v1.3.3+): ищет канонически-озаглавленные BRAIN-базы (`Brain · Decisions / Patterns / Gotchas / Web Cache`), уже расшаренные с интеграцией. Если все 4 найдены — отказывается создавать дубли и направляет к `--join-existing`.
2. Четыре раза вызывает `POST /v1/databases` для `decisions`, `web_cache`, `patterns`, `gotchas` со схемами из [brain-db-schema.md](brain-db-schema.md).
3. Атомарно пишет `.tausik/config.json` с `brain.enabled=true`, 4 `database_ids`, `notion_integration_token_env`, именем проекта (для scrubbing blocklist).
4. **Никогда** не сохраняет сам токен в `config.json` — только **имя** env-переменной. Сам токен живёт в `.tausik/.env` (рекомендуется) или в shell-environment.

Повторный запуск в уже настроенном проекте упадёт с ошибкой; для перезаписи — `--force`.

**Второй / третий / N-ный проект — присоединяемся к существующим базам:**

```bash
.tausik/tausik brain init --join-existing
```

Wizard ищет в Notion-workspace канонические 4 BRAIN-базы (auto-discovery через `POST /v1/search`) и пишет их ID в `.tausik/config.json` этого проекта. **Новые базы не создаются.** Все проекты, указывающие на одни и те же 4 ID, делят один knowledge store; колонка `Source Project Hash` сохраняет различимость по проектам.

Если auto-discovery не находит базы (например, интеграция не приглашена на parent page), передай ID явно:

```bash
.tausik/tausik brain init --join-existing \
  --decisions-id  '...' \
  --web-cache-id  '...' \
  --patterns-id   '...' \
  --gotchas-id    '...' \
  --token-env NOTION_TAUSIK_TOKEN \
  --non-interactive --yes
```

**Аварийный выход — `--force-create`.** Если действительно нужен новый отдельный комплект из 4 баз (другой Notion-account, осознанно изолированное знание), передай `--force-create`. Wizard пропустит pre-flight проверку и создаст новые. **Используй с осторожностью** — проекты, указывающие на старый комплект, не будут видеть записи нового, и наоборот.

### Частые ошибки

- ❌ **Запустить обычный `brain init` во втором проекте, использующем тот же workspace** → создаст параллельный набор из 4 BRAIN-баз. Знание тихо разделится надвое; одни проекты увидят одну половину, другие — другую. v1.3.3 pre-flight check отказывается это делать по умолчанию — **не обходи через `--force-create`, если только не нужны действительно два независимых "мозга"**.
- ❌ **"Отдельные копии для приватности"** → не нужно. Используй колонку `Source Project Hash` (она уже есть на каждой строке) для фильтрации по проектам; 4 базы делятся между проектами.
- ❌ **Ручная правка `database_ids` в `config.json`** → используй `--join-existing --decisions-id ...`, чтобы wizard верифицировал каждый ID через Notion перед сохранением.

### 6. Smoke-тест

```python
from brain_config import load_brain, validate_brain, get_brain_mirror_path
from brain_notion_client import NotionClient
from brain_sync import open_brain_db, sync_all
import os

brain = load_brain()
errors = validate_brain()
assert not errors, errors

client = NotionClient(os.environ["NOTION_TAUSIK_TOKEN"])
conn = open_brain_db(get_brain_mirror_path())
result = sync_all(client, conn, brain["database_ids"])
print(result)
```

`get_brain_mirror_path()` принимает три формы входа: `None` (читает
`load_config()` сам), top-level dict `{"brain": {...}}`, либо уже
merged brain dict `{"enabled": ..., "local_mirror_path": ...}`
(то что возвращает `load_brain()`). Все три разрешаются в один
абсолютный путь.

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
