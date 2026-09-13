[English](../en/dev-doc-checks.md) | **Русский**

# Doc-проверки для разработчика (v14-doc-automation)

Инструменты, которые держат документацию в синхроне с кодом. Все
скрипты на stdlib, у каждого есть машиночитаемый вывод для CI.

## Что запускается в CI (GitHub Actions)

Workflow: `.github/workflows/tests.yml`. Шаг: `Doc-constants drift check`.

```bash
python scripts/gen_doc_constants.py --check
```

Матрица падает, если `docs/_generated/constants.json` больше не совпадает
с полем `version` в `pyproject.toml` или с количеством MCP-инструментов,
выводимым из `harness/{claude,cursor}/mcp/*/tools.py`.

## Запуск локально перед коммитом

Вручную:

```bash
python scripts/gen_doc_constants.py --check     # exit 1 при дрейфе
python scripts/gen_doc_constants.py --write      # починить всё, что флагует --check, затем перепроверить
python scripts/gen_doc_constants.py             # перегенерировать только constants.json
```

Или добавить в локальный `pre-commit` hook (в репо уже есть mypy hook;
добавьте сверху):

```bash
# .git/hooks/pre-commit
python scripts/hooks/check_docs.py || exit 1
```

`scripts/hooks/check_docs.py` — тонкий wrapper, который:

- Идёт вверх в поисках `pyproject.toml`. Если ничего не нашёл — **печатает
  дружелюбный skip и выходит 0** — хук не ломает коммиты в checkout без
  TAUSIK-генераторов.
- Запускает `gen_doc_constants.py --check` Python'ом проекта.
- Показывает drift в stderr с однострочной remediation-подсказкой.

## Прочие audit-скрипты (вручную)

| Скрипт | Что показывает | Запуск |
|--------|----------------|--------|
| `scripts/audit_orphan_files.py` | Python-файлы в `scripts/`, на которые никто не ссылается. | `python scripts/audit_orphan_files.py [--json] [--check]` |
| `scripts/audit_stale_docs.py` | Markdown-файлы в `docs/` без входящих ссылок. | `python scripts/audit_stale_docs.py [--json] [--check]` |
| `scripts/audit_unused_python.py` | Top-level `def` / `class` без референсов. | `python scripts/audit_unused_python.py [--json] [--check]` |
| `scripts/audit_pytest_dedupe.py` | Test-функции со структурно идентичным телом. | `python scripts/audit_pytest_dedupe.py [--json] [--check]` |

Все четыре в v1 — **review-only**: ничего не удаляют и не переписывают.
Подключать в CI можно после того, как их profile of false positives
станет понятен.

Первые три обходят **только отслеживаемые git-ом файлы**
(`scripts/audit_tracked_files.py` спрашивает `git ls-files`). Гитигнорированный
файл по определению ни из чего не ссылается, поэтому в отчёте он — вечный шум,
который нельзя починить; а имена внутренних исследований из
`docs/research/_internal/` не должно печатать в общие отчёты вовсе. Если git
недоступен (вне репозитория, git отсутствует, пустой вывод), аудиты печатают
предупреждение в `stderr` и деградируют до обхода файловой системы, а не падают.

## Negative-поведение

- **Нет `pyproject.toml` выше cwd** → хук печатает SKIP и exit 0.
  Тест: `tests/test_check_docs_hook.py`.
- **`gen_doc_constants.py` отсутствует** (legacy checkout) → SKIP, exit 0.
- **Drift найден** → exit 1 + stderr-подсказка:
  `[check_docs] doc-constants drift — run python scripts/gen_doc_constants.py --write and re-commit.`

## Что проверка смотрит на самом деле

Написанное выше описывало механизм, проверявший две вещи: версию из
`pyproject.toml` и счётчики инструментов MCP. Он вырос до семи сканов, и до
появления этого раздела **из семи его модулей был назван ровно один** — там,
куда смотрит читатель.

| Скан | Что стережёт | Где живёт |
|---|---|---|
| `scan_version_refs` | `vX.Y.Z`, написанный в прозе и разошедшийся с `pyproject.toml` | `doc_drift_scanners.py` |
| `scan_py_version_constants` | та же версия, повторённая питоновской константой | `doc_drift_scanners.py` |
| `scan_mcp_tool_counts` | `**N tools**`, `N project tools` и устаревшие суммы `brain = N` (сервер brain отставлен, любая такая сумма — дрейф) | `doc_drift_scanners.py` |
| `scan_closed_list_enums` | документированный перечень значений, который закрытый список кода уже перерос | `doc_drift_scanners.py` |
| `scan_test_counts` | «N тестов» в прозе против числа, которое pytest реально собирает | `doc_drift_scanners.py` |
| `scan_code_counts` | счётчики состояния репозитория — хуки, стеки, роли, агенты ревью, скиллы | `doc_drift_scanners.py` |
| `scan_table_count_columns` | числовые ЯЧЕЙКИ таблиц markdown, со своим реестром предметов | `doc_drift_tables.py` |

Модули за ними:

| Модуль | Назначение |
|---|---|
| `gen_doc_constants.py` | точка входа: `--check`, `--write` и перегенерация `constants.json` |
| `doc_drift_common.py` | общие таблицы регулярных выражений, цели сканов и текстовые помощники |
| `doc_drift_scanners.py` | шесть сканов выше, каждый возвращает список находок |
| `doc_drift_tables.py` | скан колонок и реестр того, что означает каждая колонка |
| `doc_drift_fixes.py` | автопочинщик, который запускает `--write` |
| `code_counts.py` | считает состояние самого репозитория — хуки, стеки, роли, скиллы |
| `mcp_tool_counts.py` | считает поверхность MCP, которую объявляет каждый сервер |

## Находить и чинить обязаны идти в ногу

`--write` чинит то, о чём сообщает `--check`. Это ОБЕЩАНИЕ, и оно было нарушено:
парная форма `N project + M brain` (отставлена вместе с сервером brain в 1.9)
сканировалась с ревью #208 и не чинилась никем. Замер смены #234: подъём числа инструментов MCP со 145
до 146 оставил **восемь таких ссылок в семи файлах**, `--write` завершился
красным со словами «drift remains after --write», и на одно изменённое целое
пришлось около пятнадцати ручных правок.

Хуже труда другое: скан, сообщающий о дрейфе, который он не умеет починить,
читается тем, кто запустил `--write`, как охват. Теперь
`tests/test_doc_drift_fixes_repair_what_they_detect.py` утверждает, что каждое
семейство счётчиков, известное сканеру, известно и починщику, — чтобы следующее
не приехало наполовину.

## Куда починка НЕ заходит

Починщик никогда не правит внутри огороженного блока кода и внутри динамической
секции CLAUDE.md — там же, где не смотрит сканер. Документация учит примерами, а
пример, тихо переписанный под сегодняшние числа, перестаёт быть тем, что
иллюстрировал.
