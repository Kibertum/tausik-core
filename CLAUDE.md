# CLAUDE.md

Инструкции для AI-агента в этом репозитории. Следуй им строго.

# TAUSIK — фреймворк AI-агентов

Реализует [SENAR v1.3](https://senar.tech). Задачи, сессии, качество, проектная память.

Stack: Python 3.11+ stdlib | CLI `.tausik/tausik` | DB SQLite+FTS5 | Tests pytest. Все данные в `.tausik/` (единственный .gitignore).

## Принципы

- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI — заведи баг-задачу.
- **Agent-first.** Перед закрытием: "поймёт ли свежий агент?"
- **Dogfooding.** Мы сами пользователь. Неудобно — баг.
- **SENAR.** Контекст важнее кода. Верификация важнее скорости. Знания важнее опыта.

## Ограничения (жёсткие)

- **Нет кода без задачи.** `task start <slug>` перед Write/Edit.
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria.
- **QG-2 Verify-First.** Heavy gates через `tausik verify --task <slug>` (cache 10 мин), затем `task done --ac-verified` читает кэш. Edge-cases — `docs/ru/agent-contract.md`.
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
- **Знания фреймворка остаются здесь.** Не сохраняй инструкции TAUSIK в auto-memory.

## Память

| Система | Когда |
|---|---|
| **TAUSIK memory** (`memory add`, `.tausik/tausik.db`) | Паттерны/dead ends/conventions ЭТОГО проекта — «здесь так принято» |
| **Общая база знаний** (`memory add --global`, `~/.tausik-knowledge/knowledge.db`) | Факт об инструменте, верный за пределами проекта — «так устроен инструмент»; без секретов и имён клиентов |
| **Claude auto-memory** (`~/.claude/`) | Кросс-проектные привычки пользователя — «так мне удобно работать» |

Типы: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.
CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Компакция

Через сжатие контекста переноси дословно: активную задачу и slug; scope и квитанцию verify; замеры сессии с числами; отменённые правила; запреты владельца; открытые развилки. Выбрасывай нарратив и вывод инструментов — не эти шесть.

## Команды

```bash
.tausik/tausik status                          # обзор + предупреждения SENAR
.tausik/tausik task start <slug>               # активировать (QG-0)
.tausik/tausik verify --task <slug>            # heavy gates, cache 10 мин
.tausik/tausik task done <slug> --ac-verified  # завершить (QG-2)
.tausik/tausik task log <slug> "message"       # журнал
```

Остальное (`dead-end`, `metrics`, `search`, `doctor`) — `docs/ru/cli.md`.

## Reference

Контракт (estimation, SENAR, roles, custom_stacks, QG-2): `docs/ru/agent-contract.md`. CLI: `docs/ru/cli.md`. Архитектура: `docs/ru/architecture.md`.

<!-- DYNAMIC:START -->
## Current State
Session: #258 (active) | Branch: v1-9-wave | TAUSIK: 1.9.0
Tasks: 1497/1651 done, 1 active, 1 blocked
Active: framework-version-stamp-reads-as-the-products-version
Blocked: v14b-rag-nudge-replay-benchmark

### Memory tail
Context (5):
- #697 Трекеры перед тегом 1.9 (смена #255): 14 GitLab + 2 GitHub + PR #5 — каждому тикету назначено состоя
- #691 Аудит SENAR 9.5 за смены #243-#250: улики закрытий, когерентность, полный прогон — три находки, ни о
- #684 Трекеры на момент остановки смены #241: 13 открытых в GitLab, 2 в GitHub
- #683 Большое ревью 1.9, смена #241: двенадцать осей проверено, мёртвого кода ноль, три оси дали находки
- #677 Сверка шести условий выпуска 1.9, смена #239: четыре держатся, одно починено, одно у владельца
Decisions (5):
- #370 Состав 1.9 расширен по указанию владельца в смене #258 историей release19-tracker-promises: GitLab #5 (штамп версии), #6
- #369 Состав 1.9 расширен по указанию владельца в смене #251 историей release19-clean-publication-and-onboarding (решение #368
- #368 МОДЕЛЬ ПУБЛИКАЦИИ 1.9 УТОЧНЕНА ВЛАДЕЛЬЦЕМ, смена #251. (1) Сайт tausik.tech живёт ТОЛЬКО в отдельном репозитории GitLab 
- #367 Состав релиза 1.9 пересказан ОДНОЙ строкой, потому что генератор ROADMAP.md читал дополняющее решение #363 как полный со
- #366 Владелец, смена #251, разбор трекеров перед тегом 1.9: тикеты GitLab #13 (запятая в --relevant-files принимается как оди
Conventions (5):
- #701 Owner forbids external artifacts (claude.ai Artifact pages): reports are answered in the terminal or
- #698 Текст отказа в документации для агента снимается с живого вызова и удерживается тестом по фразе из к
- #686 Хост, добавляемый в SCAFFOLD_IDES, проверяется ЗАМЕРОМ БИНАРЯ, а не документацией
- #682 Мёртвый код ищут по СИМВОЛАМ, а не по модулям, и повторяемо — потому что удаление обнажает следующий
- #673 Столбец с числом в документе обязан быть СОСЧИТАН чем-то, иначе он гниёт молча
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
