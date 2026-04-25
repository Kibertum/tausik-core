# Stack: FastAPI

Also read `stacks/python.md` for base Python conventions.

## Testing
- **Framework**: pytest + httpx (`AsyncClient`) or `TestClient` (sync, uses requests)
- **Client**: `from fastapi.testclient import TestClient; client = TestClient(app)`
- **Async**: `async with AsyncClient(app=app, base_url="http://test") as ac: resp = await ac.get("/")`
- **Dependency override**: `app.dependency_overrides[get_db] = mock_db` for DI mocking
- **DB**: use separate test database, rollback transactions per test
- **Run**: `pytest tests/ -v --tb=short`
- **Coverage**: `pytest --cov=app --cov-report=term-missing`

## Review Checklist
- [ ] Pydantic models for request/response — never use raw dicts
- [ ] Path/query params typed: `def get_user(user_id: int)` — auto-validated
- [ ] Dependency injection via `Depends()` — not global state
- [ ] Background tasks via `BackgroundTasks`, not spawning threads
- [ ] Error handling: `HTTPException` with proper status codes, or custom exception handlers
- [ ] Async endpoints for I/O-bound work, sync for CPU-bound (runs in threadpool)
- [ ] CORS configured explicitly: `CORSMiddleware` with specific origins
- [ ] Security: `OAuth2PasswordBearer`, `HTTPBearer`, or API key via `Security()`

## Conventions
- **Project structure**: `app/` (main, routers, models, schemas, deps), `tests/`
- **Routers**: `APIRouter()` per domain, include in main app with prefix
- **Schemas**: Pydantic v2 models — `BaseModel` for request, separate `Response` model
- **DB**: SQLAlchemy async sessions or Tortoise ORM, session per request via dependency
- **Settings**: `pydantic-settings` with `.env` file (`BaseSettings`)
- **Docs**: auto-generated OpenAPI — keep `summary`/`description` on endpoints

## Common Pitfalls
- **Sync in async**: calling sync DB/file operations in `async def` blocks the event loop — use `run_in_executor` or make endpoint `def` (sync)
- **Dependency lifecycle**: `Depends` with `yield` for setup/teardown — don't forget cleanup
- **Request body consumed once**: `await request.body()` can only be read once — use Pydantic model instead
- **Startup/shutdown**: use lifespan context manager, not deprecated `@app.on_event`
- **Type hints matter**: FastAPI relies on type hints for validation, docs, and serialization — wrong types = wrong behavior
- **Background task exceptions**: silently swallowed — add try/except with logging
