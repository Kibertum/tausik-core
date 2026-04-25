# Stack: Laravel

For Blade/Livewire frontend work, see also `stacks/blade.md`.

## Testing
- **Framework**: PHPUnit (built-in) or Pest
- **Config**: `phpunit.xml`
- **HTTP**: `$this->get('/url')->assertOk()->assertSee('text')`
- **Livewire**: `Livewire::test(Component::class)->set('prop', 'value')->call('method')->assertSee()`
- **Database**: `RefreshDatabase` trait, factories, seeders
- **Run**: `php artisan test --filter=TestName`
- **Coverage**: `php artisan test --coverage`

## Review Checklist
- [ ] Thin controllers — logic in Services/Actions, not controllers
- [ ] Form Requests for validation (`php artisan make:request`)
- [ ] Eager loading with `with()` — no N+1 queries
- [ ] Scopes for common filters (`scopePublished`, `scopeAvailable`)
- [ ] `$fillable` or `$guarded` on every model
- [ ] Mass assignment protection — never `Model::create($request->all())`
- [ ] Blade: `{{ }}` for escaped output, `{!! !!}` only for trusted HTML
- [ ] Route model binding over manual `find()` + 404 check
- [ ] Config/env values accessed via `config()`, never `env()` outside config files
- [ ] Queue jobs for heavy operations (emails, imports, AI calls)

## Conventions
- **Naming**: `PascalCase` models, `snake_case` DB columns, `camelCase` methods
- **Routes**: RESTful resource routes, named routes (`route('products.show', $id)`)
- **Views**: dot notation (`templates.product`), components (`<x-layout>`)
- **Services**: `app/Services/` for business logic, injected via constructor
- **Settings**: Spatie settings (`app/Settings/`) for runtime config
- **Facades**: use sparingly — prefer DI for testability
- **Migrations**: always include `down()` method
- **Code style**: Laravel Pint (PSR-12), run `./vendor/bin/pint`

## Common Pitfalls
- **N+1 queries**: use `$this->with()` in model or `->with()` in query — Laravel Debugbar helps
- **`env()` in cached config**: returns null — always wrap in `config()`
- **Middleware order**: matters — auth before role check, CORS before everything
- **Route caching**: incompatible with closure-based routes — use controllers
- **Session in API**: stateless by default in `api` middleware group
- **Carbon mutability**: `$date->addDay()` mutates! Use `$date->copy()->addDay()`
- **Livewire hydration**: complex objects don't survive — use scalar props + computed
