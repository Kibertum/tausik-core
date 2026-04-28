# Contributing to TAUSIK

Thank you for your interest in TAUSIK! This guide explains how to set up a development environment, run tests, and submit changes.

TAUSIK implements [SENAR v1.3 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open engineering methodology for AI-native development.

## Prerequisites

- **Python 3.11+** — download from [python.org](https://www.python.org/downloads/). On Windows you can also use `winget install Python.Python.3.13`
- Git
- Core scripts have no external dependencies (stdlib only). MCP servers require the `mcp` package — bootstrap installs it automatically into an isolated venv.

## Setup

```bash
# Clone the repo
git clone https://github.com/Kibertum/tausik-core
cd tausik-core

# Bootstrap creates .tausik/venv/, installs dependencies (mcp), and initializes the project
python bootstrap/bootstrap.py --init

# Activate the venv and install dev tools
source .tausik/venv/bin/activate   # Linux/Mac
.tausik\venv\Scripts\activate      # Windows
pip install pytest ruff
```

> Bootstrap automatically finds the best Python >= 3.11, creates `.tausik/venv/`, and installs dependencies from `requirements.txt`. Your system Python is not modified.

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_tausik_service.py -v

# SENAR compliance tests
pytest tests/test_senar.py -v
```

## Code Style

- Linter: **ruff** (configured in `pyproject.toml`)
- Max file size: 400 lines (enforced by filesize gate)
- No external dependencies in `scripts/` — stdlib only
- Type hints on public API functions
- Docstrings on classes and public methods

```bash
ruff check scripts/
ruff format scripts/
```

## Project Structure

```
scripts/          # Core framework (CLI → Service → Backend)
bootstrap/        # Installation and IDE setup
agents/skills/    # 13 core skills (always deployed) + 25+ official/vendor available via tausik skill install
agents/overrides/ # IDE-specific overrides
tests/            # pytest test suite (2270 tests)
docs/             # User-facing + technical documentation (was references/)
```

## Pull Request Workflow

1. Create a branch from `main`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Run linter: `ruff check scripts/`
5. Submit a PR with a clear description

### PR Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Linter clean (`ruff check scripts/`)
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] No secrets or credentials in code

## Architecture

Three-layer architecture: **CLI → Service → Backend**. See [architecture docs](docs/en/architecture.md) for details.

- **CLI** (`project_cli.py`) — argparse, formatting, user interaction
- **Service** (`project_service.py`) — business logic, quality gates
- **Backend** (`project_backend.py`) — SQLite + FTS5, CRUD

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

# Участие в разработке TAUSIK

Спасибо за интерес к TAUSIK! Это руководство описывает настройку среды, запуск тестов и отправку изменений.

## Требования

- **Python 3.11+** — скачайте с [python.org](https://www.python.org/downloads/). На Windows также: `winget install Python.Python.3.13`
- Git
- Скрипты ядра без внешних зависимостей (только stdlib). MCP-серверы используют пакет `mcp` — bootstrap устанавливает его автоматически в изолированный venv.

## Настройка

```bash
git clone https://github.com/Kibertum/tausik-core
cd tausik-core

# Bootstrap создаёт .tausik/venv/, устанавливает зависимости (mcp) и инициализирует проект
python bootstrap/bootstrap.py --init

# Активируйте venv и установите dev-инструменты
source .tausik/venv/bin/activate   # Linux/Mac
.tausik\venv\Scripts\activate      # Windows
pip install pytest ruff
```

> Bootstrap автоматически находит Python >= 3.11, создаёт `.tausik/venv/` и устанавливает зависимости из `requirements.txt`. Ваш системный Python не модифицируется.

## Запуск тестов

```bash
pytest tests/ -v              # все тесты
pytest tests/test_senar.py -v # SENAR compliance
```

## Стиль кода

- Линтер: **ruff** (настроен в `pyproject.toml`)
- Макс. 400 строк на файл
- Без внешних зависимостей в `scripts/`
- Type hints на публичных функциях

## Отправка изменений

1. Создайте ветку от `main`
2. Внесите изменения
3. Прогоните тесты и линтер
4. Отправьте PR с описанием

## Лицензия

Отправляя изменения, вы соглашаетесь с лицензированием под [Apache License 2.0](LICENSE).
