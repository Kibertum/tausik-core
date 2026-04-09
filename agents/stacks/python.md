# Stack: Python

## Testing
- **Framework**: pytest
- **Config**: `pyproject.toml [tool.pytest]` or `pytest.ini`
- **Fixtures**: use `conftest.py` for shared fixtures, `tmp_path` for temp files, `monkeypatch` for env/attrs
- **Parametrize**: `@pytest.mark.parametrize("input,expected", [...])` for data-driven tests
- **Mocking**: `unittest.mock.patch` / `monkeypatch` — mock at the boundary, not internals
- **Async**: `pytest-asyncio` with `@pytest.mark.asyncio`
- **Run**: `pytest tests/ -v --tb=short`
- **Coverage**: `pytest --cov=src --cov-report=term-missing`

## Review Checklist
- [ ] Type hints on public functions (return type + params)
- [ ] No mutable default arguments (`def f(items=[])` — use `None` + guard)
- [ ] Context managers for resources (`with open(...)`, `with conn:`)
- [ ] No bare `except:` — always catch specific exceptions
- [ ] No `print()` in library code — use `logging`
- [ ] f-strings over `.format()` and `%` (Python 3.6+)
- [ ] `__all__` in public modules
- [ ] Imports sorted: stdlib → third-party → local (isort order)

## Conventions
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- **Style**: PEP 8, max line 120 chars (not 79 — modern screens)
- **Docstrings**: Google style (`Args:`, `Returns:`, `Raises:`)
- **Project structure**: flat modules or `src/` layout, `tests/` mirrors source
- **Packaging**: `pyproject.toml` (PEP 621), no `setup.py`

## Common Pitfalls
- **Late binding closures**: `lambda x=x: x` in loops, not `lambda: x`
- **Circular imports**: use `TYPE_CHECKING` guard or restructure
- **GIL**: CPU-bound work needs `multiprocessing`, not `threading`
- **SQLite in threads**: one connection per thread, or use WAL mode + check_same_thread=False
- **Mutable class attrs**: `class Foo: items = []` — shared across instances
- **datetime.now()**: use `datetime.now(timezone.utc)` or `datetime.utcnow()` — never naive local time
