# Stack: Flask

Also read `stacks/python.md` for base Python conventions.

## Testing
- **Framework**: pytest + Flask test client
- **Client**: `app.test_client()` — returns `FlaskClient` with `.get()`, `.post()` etc.
- **App factory**: `@pytest.fixture def app(): return create_app("testing")`
- **Context**: `with app.app_context():` for DB access outside requests
- **DB**: `flask-sqlalchemy` — use separate test DB, rollback per test
- **Run**: `pytest tests/ -v --tb=short`
- **Coverage**: `pytest --cov=app --cov-report=term-missing`

## Review Checklist
- [ ] App factory pattern (`create_app()`) — no global `app = Flask(__name__)` at module level
- [ ] Blueprints for route organization — one per domain
- [ ] Request data validated: `request.get_json()` + schema validation (marshmallow/pydantic)
- [ ] Error handlers registered: `@app.errorhandler(404)` with JSON responses for API
- [ ] No business logic in route handlers — extract to service functions
- [ ] Configuration via `app.config.from_object()` or environment variables
- [ ] Extensions initialized in `create_app()`: `db.init_app(app)`, `migrate.init_app(app)`
- [ ] CSRF protection: Flask-WTF for forms, exempt API routes explicitly

## Conventions
- **Project structure**: `app/` (factory, blueprints, models, services), `tests/`, `config.py`
- **Blueprints**: `bp = Blueprint("auth", __name__)`, register with `app.register_blueprint(bp, url_prefix="/auth")`
- **Config**: `DevelopmentConfig`, `TestingConfig`, `ProductionConfig` classes inheriting `BaseConfig`
- **DB**: Flask-SQLAlchemy + Flask-Migrate (Alembic), models in `models.py`
- **CLI**: `@app.cli.command()` for management commands
- **Templating**: Jinja2 (`render_template()`), but prefer API-only for modern apps

## Common Pitfalls
- **Application context**: accessing `db`, `current_app` outside request context raises `RuntimeError` — push context or use `with app.app_context()`
- **Circular imports**: `app.py` imports `models.py` which imports `db` from `app.py` — use factory pattern
- **Thread safety**: Flask dev server is single-threaded — production needs Gunicorn/uWSGI
- **Request globals**: `g`, `session`, `request` are thread-local proxies — don't pass between threads
- **Debug mode in production**: `FLASK_DEBUG=1` exposes debugger with code execution — never in prod
- **Large file uploads**: default limit is small — set `MAX_CONTENT_LENGTH` explicitly
