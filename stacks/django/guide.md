# Stack: Django

Also read `stacks/python.md` for base Python conventions.

## Testing
- **Framework**: `django.test.TestCase` (wraps unittest with transactions), or pytest-django
- **Client**: `self.client.get()`, `self.client.post()` for view testing
- **Fixtures**: `fixtures = ["initial_data.json"]` or `factory_boy` / `model_bakery`
- **DB**: each test runs in a transaction that rolls back — fast and isolated
- **Run**: `python manage.py test` or `pytest --ds=project.settings`
- **Coverage**: `coverage run manage.py test && coverage report`

## Review Checklist
- [ ] No raw SQL in views — use ORM queries, `Q` objects, annotations
- [ ] `select_related()` / `prefetch_related()` to avoid N+1 queries
- [ ] Forms/Serializers validate input — never trust `request.POST` directly
- [ ] CSRF protection: `{% csrf_token %}` in forms, `@csrf_exempt` only when justified
- [ ] Migrations: no data in schema migrations — separate data migration
- [ ] Settings: secrets in environment variables, not `settings.py`
- [ ] Permissions: `@login_required`, `@permission_required`, or DRF permissions
- [ ] No business logic in views — extract to services/managers

## Conventions
- **Project structure**: `project/` (settings), `app/` (models, views, urls, tests)
- **Models**: fat models, thin views — business logic in model methods or service layer
- **URLs**: `path()` with named routes, `reverse()` for URL generation
- **Templates**: template inheritance (`{% extends %}`, `{% block %}`), no logic in templates
- **Admin**: register models with `@admin.register`, customize with `ModelAdmin`
- **Signals**: use sparingly — prefer explicit method calls

## Common Pitfalls
- **Lazy querysets**: QuerySets are lazy — evaluated only when iterated/sliced. `.count()` is cheaper than `len(qs)`
- **Circular imports**: models importing from views or vice versa — use string references for ForeignKey
- **Migration conflicts**: merge migrations (`python manage.py makemigrations --merge`) when branches diverge
- **Timezone awareness**: `USE_TZ = True`, use `timezone.now()` not `datetime.now()`
- **QuerySet caching**: `qs = Model.objects.all()` is re-evaluated each use — assign result to variable if reusing
- **Signals order**: `post_save` fires before M2M changes — use `m2m_changed` signal for M2M
