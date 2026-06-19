# Shared Brain — таксономия артефактов (v1.4)

Словарь для будущих **snippet-карточек** и publish-пайплайна без добавления пятой Notion-базы в v1.

## Определения

| Термин | Смысл | Хранилище в v1 |
|--------|--------|----------------|
| **Artifact** | Логическая единица знания, переносимая между репозиториями (идея + основание). Со временем может разойтись по нескольким строкам таблиц. | Отдельной строкой БД не является; указывается через `artifact_taxonomy_kind` при записи. |
| **Pattern** | Переиспользуемый рецепт / идиома (**как делать правильно**). | Таблица Notion **`patterns`** (уже есть). |
| **Snippet** | Минимальный переиспользуемый фрагмент (код, кусок YAML, короткая команда). Уже паттерна-«эссе». | v1: та же **`patterns`**, классификатор **`artifact_taxonomy_kind: "snippet"`** (опционально). Отдельная БД — бэклог. |

**Gotcha** по-прежнему **anti-pattern** (**как не надо**) в таблице **`gotchas`**. Такса разделяет *форму* (`pattern` / `snippet` / зонтик `artifact`); семантику «ловушки» задаёт категория БД.

## Минимальная JSON-карточка (логическая)

Для контрактов, MCP-клиентов и будущей валидации — не кладётся в Notion v1 как единое тело:

```json
{
  "scope": "testing",
  "artifact_taxonomy_kind": "snippet",
  "name": "pytest caplog assert",
  "description": "Захват логов в тестах через caplog.records",
  "example": "with caplog.at_level(logging.ERROR):\n    run()\nassert \"boom\" in caplog.text",
  "tags": ["pytest", "logging"],
  "stack": ["python"]
}
```

## Внешний репозиторий (опционально)

Опциональное **`external_repo_url`** для **`brain_store_pattern`**, **`brain_store_gotcha`** и **`brain_draft_artifact`**: ссылка `http(s)` на канонический репозиторий, документацию submodule и т.п.

- **Безопасность / opt-in:** По умолчанию TAUSIK выполняет **короткий исходящий HTTP GET** (ограниченное чтение тела), чтобы убедиться, что URL отвечает (отклоняются «битые» ссылки и явные ошибки вроде **404** / **410**). Это **исходящий трафик с машины, где крутится MCP** — передавайте только доверенные URL. Схемы кроме **`http`/`https`** отклоняются.
- **Офлайн / CI:** В `.tausik/config.json` установите **`brain.skip_external_repo_url_reachability_check`: `true`** — проверяется только синтаксис URL (схема + хост), **без сети**.
- **Notion v1:** Как и **`scope`**, поле проверяется и **не записывается** в свойства Notion — отдельной колонки пока нет.

## Поле MCP

- Инструменты **`brain_store_pattern`**, **`brain_store_gotcha`** принимают опциональное **`artifact_taxonomy_kind`**: `artifact` \| `pattern` \| `snippet`.
- Опциональное **`scope`** (только логическое): пустая строка → **`card_schema_blocked`**; **`brain.require_artifact_scope`: `true`** — обязателен непустой `scope` для pattern/gotcha.
- Поля в v1 **не** отправляются в свойства Notion: проверяются и удаляются на сервере до `pages.create`.
- **Строгий режим таксономии:** в `.tausik/config.json` → **`brain.require_artifact_taxonomy_kind`: `true`** — для pattern/gotcha обязателен валидный kind; без него или с опечаткой — **`taxonomy_blocked`**.

JSON Schema (draft 2020-12): [`harness/schemas/brain-artifact-card.schema.json`](../../harness/schemas/brain-artifact-card.schema.json).

**Поток публикации (v1.4):** MCP **`brain_draft_artifact`** — черновик без Notion + уровень **risk** классификатора. Если контент выглядит проектно-специфичным, **`brain_store_pattern`** / **`brain_store_gotcha`** вернут **`risk_blocked`**, пока не передан **`confirm_high_risk: true`**. CLI: `tausik brain draft` / `tausik brain publish` (`--json` или `--file`). Успешная публикация пишет **`write`** в `brain_events` с префиксом `artifact_publish:`.

См. также [shared-brain.md](shared-brain.md) и [brain-db-schema.md](brain-db-schema.md).
