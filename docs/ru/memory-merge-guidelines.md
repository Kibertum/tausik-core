**Русский** | [English](/docs/memory-merge-guidelines)

# Память: merge или новая запись

Как не засорять **локальную** память проекта (`.tausik/tausik.db`) и опциональный **Shared Brain** (Notion). Это **редакционные** правила. Они **дополняют**, а не заменяют:

- **`scripts/brain_classifier.py`** (`classify()`) — направляет контент в **local** vs **brain** (маркеры, blocklist).
- **`brain_scrubbing`** (перед записью в Notion) — **блокирует** небезопасный текст вне зависимости от того, слили вы заметки или нет (см. *Scrubber важнее*).

## Таблица решений

| Ситуация | Предпочтительно |
|----------|-----------------|
| Тот же топик: новый нюанс, правка формулировки | **Объединить**: обновить существующую запись (один источник истины). |
| Тот же *симптом*, другая **причина** | **Новая** запись; при необходимости связать строки через [`memory link`](cli.md#знания) / граф. |
| Дословный дубликат (копипаста) | **Удалить** лишнюю запись после проверки. |
| Инсайт из задачи, но может пригодиться вне репозитория | Сначала локально; обобщить формулировку перед выгрузкой в brain (`move_to_brain`, MCP, `brain publish`). |

Если сомневаетесь — сначала **`tausik search`** / **`memory_search`** (и brain-поиск, если включён).

## Согласование с classifier

`classify()` отвечает только **куда** можно писать (`local` / `brain`). Он **не** сливает и не дедуплицирует строки. Сигналы «проектное» (пути, длинные slug, blocklist) → **local** — правило merge/new всё равно нужно **внутри** локальной памяти для качества FTS.

Решения с привязкой к задаче (`task_slug`) по политике остаются локальными — см. `decide` в `service_knowledge.py`.

## Негативное исключение: scrubber важнее намерения «объединить»

Вы можете слить две заметки в одну «чистую» для brain — но если в итоге остаются **абсолютные пути**, **email**, **приватные URL** или **имена из blocklist**, слой scrubbing **отклонит** запись в Notion (`scrub_blocked`). **Конфиденциальность важнее:** сначала обезличить текст, потом публиковать. Это **не** противоречит гайду по merge: гайд про редакцию; scrubber задаёт **жёсткий потолок** для выгрузки наружу.

## Короткие примеры

1. **Merge:** две `pattern` про pytest `tmp_path` для SQLite — одна карточка, общие буллеты, слабую строку удалить.
2. **Новая:** «флаки» из-за async vs из-за глобального состояния — две gotcha, при желании перекрёстная ссылка.
3. **Scrubber:** при слиянии затесался `D:\Work\…` — запись в brain блокируется, пока пути не убраны.

## CLI гигиены (B9, v1.4 polish)

Когда long-running проект накопил шум и FTS перестаёт давать релевантные ответы — две read-safe команды для уборки. Обе работают **только** с локальной `.tausik/tausik.db`, brain не затрагивают.

```bash
# Soft-архив: спрятать записи старше N времени из `memory list/search`.
# По умолчанию dry-run; --confirm проставляет `archived_at` (идемпотентно).
tausik memory archive --before 90d            # preview
tausik memory archive --before 90d --confirm  # применить

# Найти пары почти-дублей по similarity порогу (read-only).
tausik memory dedupe                  # порог по умолчанию 0.85
tausik memory dedupe --threshold 0.9 --limit 500
```

Грамматика длительности: `<int><unit>` где `unit ∈ d|w|m|y` (`m=30 дней`, `y=365 дней`). Иначе — ошибка.

`memory list` и `memory search` по умолчанию фильтруют `archived_at IS NOT NULL`; флаг `--include-archived` (CLI) или `include_archived: true` (MCP) возвращает их в выдачу. `memory show <id>` всё равно работает на архивированной записи — содержание не теряется.

Dedupe считает `SequenceMatcher.ratio()` по `title || content` и сравнивает только записи **одного типа** — `pattern` никогда не предложит слить с `gotcha`. Команда suggest-only; консолидируй вручную через `memory show` + `memory delete`, или перепиши одну запись, чтобы поглотить другую.

## Эвристика universality (B3, v1.4 polish)

Когда тело memory или decision упоминает один из общеизвестных кросс-проектных топиков, TAUSIK печатает однострочный hint в stderr:

```
Universal pattern(s) detected: jwt, retry — consider promoting via `brain_draft_artifact` (or skip with `confirm: cross-project`).
```

Hint **только подсказка** — не блокирует запись, не выбрасывает исключений, молчит когда совпадений нет. Детект идёт после успешной записи в `service_knowledge.memory_add` и в success-путях `brain_runtime.try_brain_write_decision` / `try_brain_write_web_cache`.

Покрытые топики (regex/keyword, case-insensitive, word-boundary aware):

- `rbac` — RBAC, role-based access
- `jwt` — JWT, JSON Web Tokens
- `oauth` — OAuth / OAuth2
- `rate-limit` — rate-limit(ed/ing/er), throttle
- `pagination` — paginate, cursor pagination
- `retry` — retry, retries, exponential backoff
- `idempotency` — idempotent, idempotency-key
- `webhook` — webhook(s)
- `csrf` — CSRF, XSRF, Cross-Site Request Forgery
- `graphql` — GraphQL, gql query/mutation/subscription/schema/resolver
- `feature-flag` — feature flag, feature toggle
- `circuit-breaker` — circuit breaker, bulkhead pattern

Word-boundary защита убирает false positives (например, `aggregate` НЕ триггерит `rate-limit`). Расширить — править `_TOPIC_PATTERNS` в [scripts/brain_universality.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_universality.py).

## Семантический слой universality (C2, v1.4 polish)

Regex выше быстрый, но слепой к **синонимам** ("access control" → `rbac`, "token bucket" → `rate-limit`). Семантический слой закрывает это без ML-зависимостей: запрашивает локальный brain mirror через FTS5 и поднимает топики из существующих brain-записей, чьи теги совпадают с known-universal темой И bm25 score достаточно сильный для нового контента.

```
Semantic universality hint: rbac — new content resembles existing brain entries on these topics (consider promoting via `brain_draft_artifact`).
```

Как работает:

1. После regex-слоя контент токенизируется (lowercase, stopwords отсекаются, длина ≥ 4).
2. До 8 distinctive токенов ищутся в локальном brain mirror (FTS5 по `brain_decisions` / `brain_patterns` / `brain_gotchas` / `brain_web_cache`).
3. Для каждого хита `tags` пересекаются с `KNOWN_UNIVERSAL_TOPICS`. Топики с bm25 score ≤ threshold (default 8.0; ниже = сильнее матч) эмитятся.
4. Топики, уже пойманные regex-слоем, **дедуплицируются** — видишь только новый сигнал.

Activation gate (defaults в `scripts/brain_config.py`):

- `brain.enabled` is `true`
- `brain.semantic_universality_enabled` is `true` (default; поставь `false` чтобы выключить семантический слой)
- Файл brain mirror существует на диске

Реализация: [scripts/brain_universality_semantic.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_universality_semantic.py). Pure stdlib; переиспользует FTS5 инфраструктуру [scripts/brain_search.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_search.py). Никогда не выбрасывает исключений, не блокирует. Пустой mirror → silent no-op. Точность синонимов растёт по мере промоутинга записей в brain.

## См. также

- [Shared Brain](shared-brain.md) — модель, синк, приватность.
- [Таксономия артефактов brain](brain-artifact-taxonomy.md) — draft/publish, `risk_blocked`.
- [Схема brain DB](brain-db-schema.md) — роль scrubbing.
- [CLI — Знания](cli.md#знания) — `memory add`, `memory link`, поиск.
