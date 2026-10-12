# Карта документации после ухода Notion (решение #358)

Артефакт планирования задачи `kb-docs-map`, смена #246, 2026-09-12. Потребитель —
`kb-docs-swarm` (переписывание по зонам) и `kb-docs-consistency` (сквозная сверка).
Код уже удалён коммитом `77703c4a`, граница публикации добавлена `0dbfb49e`; здесь
только документация.

## 1. Инвентарь — сосчитан, а не оценён

Команда, которой считался список (повторить перед роем — число обязано сойтись
или уменьшиться):

```bash
grep -rilE 'notion|shared brain|tausik-brain|brain_' docs README.md README.ru.md \
  | grep -vE '_generated|/research/|whats-new-1\.8'
```

Результат на момент карты: **45 файлов**. Исключены намеренно:

- `docs/*/research/*` — исторические заметки, не претензии о текущем продукте;
- `docs/*/whats-new-1.8.md` — история релиза 1.8; факт «в 1.8 был Notion» верен;
- `docs/_generated/` — порождается генератором, уже пересобран.

`docs/*/whats-new-1.9.md` попадают в список только своим разделом «Транспорт Notion
удалён» — это уже правильный текст, править не надо (зона Z4, судьба «оставить»).

## 2. Зоны — один владелец на файл, ru и en вместе

Файл входит ровно в одну зону. Зеркало ru/en — всегда в той же зоне и у того же
владельца: `test_audit_translation_drift` сверяет заголовки, таблицы и блоки кода
пар, и два владельца на пару дадут дрейф.

### Z1 — «снять»: страницы удалённой подсистемы (8 файлов)

| Файл (ru + en) | Судьба | Почему |
|---|---|---|
| `shared-brain.md` | удалить | 281 строка о Notion-brain, зеркале и мастере; предмет отсутствует |
| `brain-db-schema.md` | удалить | схема четырёх Notion-баз |
| `brain-artifact-taxonomy.md` | удалить | draft/publish карточек — `brain draft/publish` удалены |
| `brain-search-ranking.md` | удалить | bm25-буст поиска по зеркалу — `brain_search` удалён |

Входящие ссылки, которые обязаны исчезнуть вместе с файлами (grep по `.md`
имени, проверено перед картой):

- `docs/README.md:63-71` и `:162-170` — четыре строки индекса в разделе «Memory &
  shared brain» / «Память и Shared Brain» (ru и en части одного файла — зона Z4);
- `docs/{en,ru}/knowledge-store.md:8` и `:206-208` — «третье хранилище» и ссылка в «См. также» (Z2);
- `docs/{en,ru}/memory-merge-guidelines.md:110-112` — три ссылки в «См. также» (Z2);
- `scripts/brain_scrubbing.py:18` — docstring `references/brain-db-schema.md` (код, не docs; поправить строку в той же задаче, что и Z2, чтобы `test_doc_gate_list_parity` не ссылался на несуществующий файл: см. §4).

### Z2 — «хранилища»: где живут знания (10 файлов)

| Файл (ru + en) | Судьба | Строки |
|---|---|---|
| `knowledge-store.md` | переписать разделы | 7, 134-153 (import-brain — оставить, это миграция), 173-183 («три хранилища» → два; строка `brain move --to-brain` из таблицы уходит), 206-208 |
| `memory-merge-guidelines.md` | переписать | 5, 7-8 (классификатор и scrubbing «перед записью в Notion» → граница публикации `--redacted`), 25, 29, 63 (`brain_draft_artifact` → `memory add --global`), 66, 83, 110-112 |
| `configuration.md` | вырезать | 40-43 таблица `brain.*`, 61 пример JSON; добавить `publication.project_names`, `publication.private_url_patterns` |
| `environment.md` | вырезать | 36/43 `TAUSIK_BRAIN_HOOK_DEBUG`, 49/54 `TAUSIK_BRAIN_REGISTRY`, раздел «Brain / Notion» 71-77/73-79 |
| `team-state-in-git.md` | поправить строку | 18 («Notion/сервер» — пример внешнего стора, оставить как пример), 51 (`brain_events`, `sync_state` — таблицы ещё есть в схеме; оставить) |

### Z3 — «поверхность»: команды, хуки, навыки, диагностика (22 файла)

| Файл (ru + en) | Судьба | Строки |
|---|---|---|
| `skills.md` | переписать шапку и таблицу | 7 (14 → 13, без «`/brain` условно»), 15, 33 (строка `/brain`) |
| `hooks.md` | удалить две строки | 21 `brain_search_proactive`, 31 `brain_post_webfetch` |
| `hooks-events.md` (только ru; en-зеркала нет и не было — `test_audit_stale_docs` это уже терпит) | удалить строку | 27 |
| `doctor.md` | удалить строки | 45 «Brain / Notion config», 84 `WARN Shared Brain`; 30 — список critical skills без `brain` уже верен |
| `mcp.md` | удалить строку | 12 «`tausik-brain` — 7 tools» (раздел уже вырезан в `77703c4a`) |
| `cli.md` | оставить | 482 — историческое упоминание внутри пояснения про `ILLUSTRATIVE`; предмет — не Notion |
| `architecture.md` | переписать | 74/75 строка таблицы модулей `brain_*.py`; 349/352 абзац про brain-хуки; диаграмма §«Архитектура» если содержит Notion (проверить) |
| `quickstart.md` | удалить блок | 119/118 «v1.4 — Shared Brain prompt» |
| `security.md` | переписать строку | 145/143: `brain_scrubbing` теперь редактор границы публикации при `knowledge export --redacted` |
| `skill-spec.md` | удалить строку | 57 «Core (conditional) brain» |
| `skill-supply-chain-threat-model.md` | оставить | 124/128 — ссылка на `_ZERO_WIDTH_RE` в `brain_scrubbing`, модуль жив |
| `troubleshooting.md` | вырезать раздел | en 46-56 «Shared Brain (Notion)»; ru 140-141 (две строки таблицы) — **асимметрия ru/en**, после правки парность восстановится |

### Z4 — «корень и заметки» (5 файлов)

| Файл | Судьба | Строки |
|---|---|---|
| `README.md`, `README.ru.md` | поправить строку | 142/141 «cross-project shared brain (optional, Notion-mirrored)» → общее локальное хранилище `~/.tausik-knowledge` |
| `docs/README.md` | переписать раздел | 63-71 и 162-170: раздел «Memory & shared brain» → «Memory & shared store», четыре строки Z1 убрать, `knowledge-store.md` оставить первой |
| `whats-new-1.9.md` (ru+en) | оставить | раздел BREAKING §2 написан в `77703c4a` |

Итого: 8 + 10 + 22 + 5 = 45. Сумма обязана равняться числу из §1.

## 3. Сквозные утверждения — одна формулировка на всех страницах

| # | Утверждение | Каноническая формулировка | Где встречается |
|---|---|---|---|
| S1 | Где живут знания | **Два хранилища**: проект — `.tausik/tausik.db`; общее локальное — `~/.tausik-knowledge/knowledge.db` (`$TAUSIK_HOME`). Третьего нет. | knowledge-store, memory-merge-guidelines, README ru/en, docs/README.md, architecture |
| S2 | Нужен ли Notion | **Нет и невозможен**: транспорт удалён в 1.9 (решение #358); `knowledge import-brain` — разовая миграция из локального зеркала `~/.tausik-brain/brain.db`. | knowledge-store, quickstart, configuration, environment, troubleshooting, skills |
| S3 | Как настраивается общее хранилище | **Ничем**: `--global` у `decide` / `memory add` / `snippet extract --scope global`; путь — `$TAUSIK_HOME`. Ключей `brain.*` нет. | configuration, environment, knowledge-store, cli |
| S4 | Что может покинуть машину и git | `.tausik/` не в git; `knowledge export` — только локальные назначения, верная копия; `knowledge export --redacted` — копия в дорогу через `publication_boundary` (пути, e-mail, приватные URL, имена проектов → плейсхолдеры; манифест `redacted: true`). | knowledge-store, security, memory-merge-guidelines, team-state-in-git |
| S5 | Счётчики | хуков **22**, core-навыков **13**, MCP-инструментов **146** (+7 RAG = 153) — источник `docs/_generated/constants.json`, править руками нельзя | README ru/en, AGENTS.md, skills, hooks, mcp, architecture, docs/README.md |
| S6 | Скраббер | `brain_scrubbing` жив как редактор границы публикации; классификатора нет; «scrubbing перед записью в Notion» — устаревшая формулировка | memory-merge-guidelines, security, skill-supply-chain-threat-model |

## 4. Гейты, которые рой обязан пройти

| Гейт | Что проверяет | Как не упасть |
|---|---|---|
| `gen_doc_constants --check` / `test_check_docs_hook` | S5 в README, AGENTS, architecture, mcp, cli, senar-matrix, agent-contract; табличные ячейки | не вписывать числа руками — `python scripts/gen_doc_constants.py --write` после правок |
| `test_audit_translation_drift` | парность ru/en по заголовкам, таблицам, блокам кода | зеркало правит один владелец, одной правкой; удалять оба зеркала Z1 разом |
| `test_publication_lines` | пути с машины разработчика (`C:/Projects`) и прочие «остатки» не растут | примеры путей — `/home/me/...` |
| `test_release_notes_1_9` | каждая BREAKING-запись CHANGELOG названа в whats-new-1.9 | §2 уже есть; новых BREAKING в этой работе не будет |
| `test_cli_examples_parse` | примеры `tausik ...` в docs разбираются парсером | `tausik brain ...` в примерах недопустим — таких после `77703c4a` в cli.md нет; проверить quickstart/troubleshooting |
| `test_doc_gate_list_parity` | упоминает `brain-db-schema.md` как пример **generic**-формулировки (строка 77) | после удаления файла тест ссылается на несуществующее имя только в комментарии — поправить комментарий в той же задаче, что удаляет Z1 |
| `test_audit_stale_docs` | «одинокие» файлы без зеркала | не оставлять ru без en и наоборот (`hooks-events.md` уже одинок и терпим; `research/` исключён) |
| `docs/README.md` индекс + кросс-ссылки | битые ссылки на Z1 | §2 Z1 — список входящих ссылок |
| `test_publication_lines` «Unreleased 163 записи» в whats-new | не гейт, а гниющее число (конвенция #673) | пересчитать перед тегом, не в этой работе |

## 5. Порядок для роя

1. Z1 первым — удаление освобождает остальных от ссылок; в том же коммите
   `docs/README.md` (Z4, индекс) и комментарий в `test_doc_gate_list_parity.py`.
2. Z2 и Z3 параллельно (файлы не пересекаются).
3. Z4 README ru/en — последним, после `gen_doc_constants --write`.
4. `kb-docs-consistency` — grep из §1 обязан вернуть только `whats-new-1.9.md`
   (ru+en), `cli.md:482` и `skill-supply-chain-threat-model.md` (S6, модуль жив);
   затем полный прогон.
