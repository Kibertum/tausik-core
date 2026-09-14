# CLAUDE.md

# TAUSIK — фреймворк AI-агентов

Реализует [SENAR v1.3](https://senar.tech). Задачи, сессии, качество, проектная память.

Stack: Python 3.11+ stdlib | CLI `.tausik/tausik` | DB SQLite+FTS5 | Tests pytest. Данные в `.tausik/`.

## Принципы

- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI — заведи баг-задачу.
- **Agent-first.** Перед закрытием: "поймёт ли свежий агент?"
- **Dogfooding.** Мы сами пользователь. Неудобно — баг.
- **SENAR.** Контекст важнее кода. Верификация важнее скорости. Знания важнее опыта.

## Ограничения (жёсткие)

- **Нет кода без задачи.** `task start <slug>` перед Write/Edit.
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria.
- **QG-2 Verify-First.** `tausik verify --task <slug>` (scoped, cache 10 мин) → `task done --ac-verified`. Edge-cases — `docs/ru/agent-contract.md`.
- **Проверка соразмерна правке.** Scoped verify; полная лента — в CI и один раз у тега. Тест — на поведение, не на число в документе и не на свежесть порождённого файла.
- **Нет коммита без gates.** Исправь blocking failures.
- **Нет прямого доступа к БД.** Только MCP/CLI.
- **Не угадывай аргументы CLI.** `tausik <cmd> --help` или `docs/ru/cli.md`.
- **Исходники в корне** (`scripts/`, `docs/`, `harness/`, `bootstrap/`). Не редактируй `.claude/` напрямую.
- **MCP-first.** MCP > CLI когда equivalent.
- **Git: спроси перед commit/push.**
- **Макс. 500 строк/файл.** Filesize gate (decision #190). Исключения: тесты, generated.
- **Непрерывное журналирование.** `task log <slug> "msg"` после каждого шага.
- **Документируй dead ends.** `tausik dead-end "approach" "reason"`.
- **Checkpoint каждые 30-50 tool calls.** `/checkpoint`, `/end`.
- **Лимит сессии 180 мин ACTIVE** (пауза ≥10 мин = AFK).

## Память

| Система | Когда |
|---|---|
| **TAUSIK memory** (`memory add`) | Паттерны/dead ends/conventions ЭТОГО проекта |
| **Общая база** (`memory add --global`) | Факт об инструменте, верный вне проекта; без секретов |
| **Claude auto-memory** (`~/.claude/`) | Привычки пользователя; НЕ знания и правила TAUSIK |

Типы: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.
CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Компакция

Через сжатие контекста переноси дословно: активную задачу и slug; scope и квитанцию verify; замеры сессии с числами; отменённые правила; запреты владельца; открытые развилки. Выбрасывай нарратив и вывод инструментов — не эти шесть.

## Команды

```bash
.tausik/tausik status                # обзор + предупреждения SENAR
.tausik/tausik task start <slug>     # QG-0
.tausik/tausik verify --task <slug>  # scoped, cache 10 мин
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "message"
```

Остальное (`dead-end`, `metrics`, `search`, `doctor`) — `docs/ru/cli.md`.

## Reference

Контракт (estimation, SENAR, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. CLI: `docs/ru/cli.md`. Архитектура: `docs/ru/architecture.md`.

<!-- DYNAMIC:START -->
## Current State
Session: #264 (active) | Branch: v1-9-wave | TAUSIK: 1.9.0
Tasks: 1510/1661 done, 1 active, 0 blocked
Active: release-1-9-0-cut-tag-snapshot

### Memory tail
Context (5):
- #712 Трекеры перед тегом 1.9, смена #264: ответы опубликованы в GitLab #5/#6/#14 и GitHub PR #5, ничего н
- #706 Парный replay rag-first подсказок, смены #261–#263: search_code = 0 в обоих условиях, экономии нет, 
- #697 Трекеры перед тегом 1.9 (смена #255): 14 GitLab + 2 GitHub + PR #5 — каждому тикету назначено состоя
- #691 Аудит SENAR 9.5 за смены #243-#250: улики закрытий, когерентность, полный прогон — три находки, ни о
- #684 Трекеры на момент остановки смены #241: 13 открытых в GitLab, 2 в GitHub
Decisions (5):
- #371 ПРОВЕРКА СОРАЗМЕРНА ПРАВКЕ. Владелец, смена #263, сказано не в первый раз и потому записано: «мы превращаем разработку в
- #370 Состав 1.9 расширен по указанию владельца в смене #258 историей release19-tracker-promises: GitLab #5 (штамп версии), #6
- #369 Состав 1.9 расширен по указанию владельца в смене #251 историей release19-clean-publication-and-onboarding (решение #368
- #368 МОДЕЛЬ ПУБЛИКАЦИИ 1.9 УТОЧНЕНА ВЛАДЕЛЬЦЕМ, смена #251. (1) Сайт tausik.tech живёт ТОЛЬКО в отдельном репозитории GitLab 
- #367 Состав релиза 1.9 пересказан ОДНОЙ строкой, потому что генератор ROADMAP.md читал дополняющее решение #363 как полный со
Conventions (5):
- #711 Проверка соразмерна правке: полная лента — CI и релизный гейт, тест — на поведение, порождённое поро
- #701 Owner forbids external artifacts (claude.ai Artifact pages): reports are answered in the terminal or
- #698 Текст отказа в документации для агента снимается с живого вызова и удерживается тестом по фразе из к
- #686 Хост, добавляемый в SCAFFOLD_IDES, проверяется ЗАМЕРОМ БИНАРЯ, а не документацией
- #682 Мёртвый код ищут по СИМВОЛАМ, а не по модулям, и повторяемо — потому что удаление обнажает следующий
Dead ends (3):
- #693 Verify review journal with tracked output documents as relevant files
- #692 Capture Codex PreToolUse JSON through a temporary generated command hook
- #689 Ограничить parent-tree претензии done-задач условием completed_at >= started_at верифицируемой задач

**Shared knowledge — from other projects (11):**
- [decision] v139-D (клиентский mux) НЕ делается в 1.3.9 как «фикс троттлинга». Предпосылка задачи неверна для на
- [decision] Дефект brain move, найденный внутри задачи о property-тесте проекции, заведён отдельной задачей, а н
- [decision] Коэффициент калибровки на окне n=10 непригоден для прогноза срока релиза: за одну сессию #153 он про
- [convention] Windows: команду с вложенными кавычками писать ФАЙЛОМ, а не однострочником
- [convention] TAUSIK 1.8: verify --task без --relevant-files не сертифицирует закрытие задачи
- [gotcha] iptables-persistent и Docker на одной машине конфликтуют
- [gotcha] Ansible copy кладёт файлы побайтово — CRLF ломает шебанг
- [gotcha] Ansible молча игнорирует ansible.cfg в world-writable каталоге
- [pattern] Проверять содержимое ответа, а не только HTTP-код
- [pattern] Мониторинг без heartbeat неотличим от мёртвого
- [pattern] TAUSIK 1.8: обёртка команды гейта обязана НАЗЫВАТЬСЯ именем инструмента
<!-- DYNAMIC:END -->
