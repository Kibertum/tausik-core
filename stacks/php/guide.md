# Stack: PHP

## Testing
- **Framework**: PHPUnit or Pest
- **Run**: `./vendor/bin/phpunit` or `php artisan test`
- **Assertions**: `$this->assertEquals()`, `$this->assertCount()`, `$this->expectException()`
- **Mocking**: `$this->createMock()`, Mockery (`Mockery::mock()`)
- **Coverage**: `./vendor/bin/phpunit --coverage-text`

## Review Checklist
- [ ] Strict types: `declare(strict_types=1)` in every file
- [ ] Type hints on all parameters, return types, and properties
- [ ] No `@` error suppression — handle errors explicitly
- [ ] No `extract()` — explicit variable assignment
- [ ] No `eval()` or `$$variable` — dynamic variable names are a security risk
- [ ] `===` strict comparison, never `==` (PHP type juggling is dangerous)
- [ ] Array functions over loops: `array_map`, `array_filter`, `array_reduce`
- [ ] `null` checks: `??` (null coalescing), `?->` (nullsafe operator)
- [ ] No `die()`/`exit()` in library/app code — throw exceptions
- [ ] SQL: parameterized queries, never string concatenation

## Conventions
- **Style**: PSR-12 (Laravel Pint or PHP-CS-Fixer)
- **Naming**: `PascalCase` classes, `camelCase` methods, `snake_case` DB fields
- **Namespaces**: PSR-4 autoloading, one class per file
- **Exceptions**: custom exception classes extending `RuntimeException` or `LogicException`
- **Constants**: `UPPER_CASE`, prefer class constants over `define()`
- **Enums**: native PHP 8.1 enums over class constants for fixed sets

## Common Pitfalls
- **Type juggling**: `"0" == false` is true, `"" == 0` is true — always use `===`
- **Array key existence**: `isset()` returns false for `null` values — use `array_key_exists()`
- **String functions**: `str_contains()`, `str_starts_with()` (PHP 8.0+) over `strpos()`
- **DateTime mutability**: `DateTime::modify()` mutates — use `DateTimeImmutable`
- **Memory**: generators (`yield`) for large datasets, not loading all into memory
- **Encoding**: `mb_strlen()`, `mb_strtolower()` — never assume ASCII
