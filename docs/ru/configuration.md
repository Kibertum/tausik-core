[English](../en/configuration.md) | **Русский**

# Справочник конфигурации TAUSIK

<!-- doc-map: reader=user; zone=configuration -->

Все настройки в `.tausik/config.json` в корне проекта. Что не указано — берёт документированный дефолт. Override — добавь ключ в top-level объект (НЕ под `bootstrap` — там bootstrap управляет).

См. также: [environment.md](environment.md) — env-переменные, [permissions.md](../en/permissions.md) — режимы permissions.

## Сигналы сессии (SENAR Rule 9.2 — с 1.10 совет, а не ворота)

| Ключ | Дефолт | Назначение |
|---|---|---|
| `session_max_minutes` | `180` | Порог совета по АКТИВНЫМ минутам сессии: выше него `task start`, `status` и Stop-хук печатают совет; ничто не отказывает. `0` выключает. |
| `session_idle_threshold_minutes` | `10` | Промежуток (в минутах), после которого пауза считается AFK и исключается из active-time. |
| `session_warn_threshold_minutes` | `150` | Порог напоминания stop-хука в `session_cleanup_check.py`. Должен быть < `session_max_minutes`. |
| `session_capacity_calls` | `200` | Бюджет tool-calls на сессию. `call_budget` задачи выше остатка — строка совета в `task start`, не отказ. |
| `answer_budget_words` | `200` | Бюджет слов итогового ответа агента. На следующем запросе ответ сверх него (или без вердикта в первой строке) получает одну строку-совет с числами; ничего не блокируется. Замер — `tausik metrics answers`. |
| `checkpoint_calls` | `40` | Вызовы с последнего handoff до совета о чекпоинте (выводится из журнала). `0` выключает. |
| `journal_freshness_calls` | `40` | Вызовы с последней записи журнала активной задачи до совета. `0` выключает. |
| `audit_every_closures` | `17` | Закрытия задач с последней отметки аудита до просрочки аудита SENAR 9.5. |

## Языки поиска по коду (RAG)

| Ключ | По умолчанию | Смысл |
|------|--------------|-------|
| `rag.extra_extensions` | `{}` | Дополнительные типы файлов для индекса, `{".unity": "unity-scene"}`. Встроенное расширение не переопределяется. Godot (`.gd`, `.gdshader`, `.tscn`, `.tres`, `.godot`) встроен с 1.10. |
| `rag.boundaries` | `{}` | Где резать язык на чанки, `{"unity-scene": "^--- !u!"}` (многострочная регулярка). Кривая запись пропускается и называется в `rag_status` в `language_config.problems`. |

## Проверка обновления

| Ключ | По умолчанию | Смысл |
|------|--------------|-------|
| `updates.check` | `true` | Не чаще раза в сутки SessionStart отсоединённо запускает `tausik update-check`: один анонимный GET к `releases/latest` репозитория `Kibertum/tausik-core` на GitHub, без данных о проекте. `status` называет вышедшую версию. `false` выключает; состояние — в `tausik doctor`. |

## Кэш верификации (SENAR Rule 5)

| Ключ | Дефолт | Назначение |
|---|---|---|
| `verify_cache_ttl_seconds` | `600` | Сколько секунд зелёный verify-run переиспользуется до перезапуска gates. Уменьши для security-critical проектов. |

## Настройки из быстрого старта

Все ключи лежат в корне `.tausik/config.json`, если путь не говорит иного.

| Ключ | По умолчанию | Назначение |
|---|---|---|
| `context_tier` | `"standard"` | Размер порождаемого файла правил: `"minimal"` (короче), `"standard"`, `"full"` (расширенные указатели). Неизвестное значение bootstrap отклоняет; `tausik doctor` сверяет дрифт с сохранённым уровнем. |
| `output_mode` | `"off"` | `"caveman"` добавляет указание отвечать сжато, телеграфно. Код, команды, вывод инструментов, сообщения об ошибках, доказательства критериев и решения остаются целиком. Правила ответа (форма, исключения, проверка перед отправкой) поставляются в каждый файл правил независимо от ключа. Ошибочное значение откатывается к `"off"`. «~65% сокращения» — собственная цифра проекта caveman, здесь не измерена. |
| `model_profile` | не задан | Слаг профиля хоста (`a-z`, цифры, дефисы), например `claude`, `codex`. Bootstrap записывает его, когда задана `TAUSIK_MODEL_PROFILE`; неверное значение прерывает bootstrap. `python bootstrap/bootstrap.py --refresh` обновляет только конфигурацию. |
| `task_done.auto_verify` | `false` | `true` заставляет `task done` прогонять гейты внутри вызова и закрывать задачу **без подписанной квитанции**. Это не обход гейтов — они работают, — но квитанция теряется, поэтому проверка доверия конфигурации считает ключ ослаблением, и доверенный тир возвращает его назад (`scripts/config_trust.py`). Лучше `task done <slug> --ac-verified --verify`: один вызов и квитанция. |

**Файлы правил сохраняются после первой записи.** `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `QWEN.md` и файл правил OpenCode bootstrap не перезаписывает, если они уже есть, поэтому поздняя смена `context_tier` или `output_mode` до них не доходит. Bootstrap об этом говорит; удалите порождённый файл и запустите bootstrap заново или поправьте руками.

**MCP-закрытие возвращает структуру.** `tausik_task_done` отвечает полями `stage`, `gate_results` и `blocking_failures`, чтобы агент чинил упавшее, не разбирая прозу.

## Стеки

| Ключ | Дефолт | Назначение |
|---|---|---|
| `custom_stacks` | `[]` | Список custom stack slug'ов, принимаемых `task add --stack X`. |

## Gates

| Ключ | Дефолт | Назначение |
|---|---|---|
| `gates` | `{}` | Per-gate overrides: `{ "pytest": { "enabled": true }, "filesize": { "max_lines": 600 } }`. Мержится поверх `default_gates.py`. |

## Файлы инструкций агента (блок DYNAMIC)

`tausik update-claudemd` переписывает блок между `<!-- DYNAMIC:START -->` и
`<!-- DYNAMIC:END -->` в CLAUDE.md и, если он лежит рядом, в AGENTS.md.
AGENTS.md в большинстве проектов версионируется, поэтому его содержимое —
политика, а не случайность (GitLab #14):

| Ключ | Умолчание | Назначение |
|---|---|---|
| `claudemd.sibling_dynamic` | `true` | `true`: AGENTS.md обновляется блоком **без** «Shared knowledge — from other projects» — знания чужих проектов не попадают в историю этого репозитория, а хвост памяти, под которым ничего не осталось, опускается. `false`: AGENTS.md не пишется вовсе; CLAUDE.md обновляется как раньше. Выключает только JSON-булево `false` — строка `"false"` или `0` читаются как «включено». Ключ читается из `.tausik/` рядом с записываемым файлом. |

Гейт коммита `claudemd_state` судит каждый файл по тому же плану, которому
следует писатель: сиблинг, который политика не пишет, не судится, а сиблинг,
чьё единственное знание было бы чужим, хвоста не должен.

## Публикация (что скрывает вычищенный экспорт)

Общее хранилище (`~/.tausik-knowledge`) не требует настройки: `--global` у
`decide` / `memory add` пишет в него, `$TAUSIK_HOME` переносит. Эти ключи читает
только `knowledge export --redacted` (см. [knowledge-store.md](knowledge-store.md)).

| Ключ | Дефолт | Назначение |
|---|---|---|
| `publication.project_names` | `[]` | Имена проектов, заменяемые на `[REDACTED:project]`, в дополнение к имени каталога этого проекта. |
| `publication.private_url_patterns` | `[]` | Regex-строки; URL, подходящий под одну из них, становится `[REDACTED:url]`. |
| `brain.local_mirror_path` | `~/.tausik-brain/brain.db` | Читается только разовым `knowledge import-brain`: где отставленный транспорт Notion оставил локальное зеркало. |

## Пример

```json
{
  "session_max_minutes": 240,
  "session_idle_threshold_minutes": 15,
  "verify_cache_ttl_seconds": 1200,
  "custom_stacks": ["ruby", "elixir"],
  "gates": {
    "filesize": { "max_lines": 500 },
    "ruff": { "enabled": false }
  },
  "publication": {
    "project_names": ["acme"],
    "private_url_patterns": ["acme\\.internal"]
  },
  "claudemd": { "sibling_dynamic": false }
}
```

## Health check

`tausik doctor` (v1.3+) проверяет согласованность config + venv + DB + skills и выдаёт actionable next steps.
