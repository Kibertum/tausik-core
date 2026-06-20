[English](/docs/dev-doc-checks) | **Русский**

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
python scripts/gen_doc_constants.py             # перегенерировать JSON
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

## Negative-поведение

- **Нет `pyproject.toml` выше cwd** → хук печатает SKIP и exit 0.
  Тест: `tests/test_check_docs_hook.py`.
- **`gen_doc_constants.py` отсутствует** (legacy checkout) → SKIP, exit 0.
- **Drift найден** → exit 1 + stderr-подсказка:
  `[check_docs] doc-constants drift — run python scripts/gen_doc_constants.py and re-commit.`
