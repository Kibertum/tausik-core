# Stack: Go

## Testing
- **Framework**: built-in `testing` package + `go test`
- **Table-driven tests**: standard pattern — `tests := []struct{ ... }; for _, tt := range tests { ... }`
- **Subtests**: `t.Run(name, func(t *testing.T) { ... })` for test isolation
- **HTTP testing**: `httptest.NewServer`, `httptest.NewRecorder`
- **Mocking**: interfaces + manual mocks, or `testify/mock`
- **Assertions**: `testify/assert` or manual `if got != want { t.Errorf(...) }`
- **Run**: `go test ./... -v -race`
- **Coverage**: `go test ./... -coverprofile=cover.out && go tool cover -html=cover.out`

## Review Checklist
- [ ] Errors checked immediately: `if err != nil { return ..., fmt.Errorf("context: %w", err) }`
- [ ] No `panic()` in library code — return errors
- [ ] Error wrapping with `%w` for unwrappable errors, `%v` for opaque
- [ ] Goroutines: every goroutine has a way to exit (context, done channel)
- [ ] Channels: no goroutine leaks — buffered or with select/default
- [ ] `defer` for cleanup — but watch for loops (defer runs at function exit, not iteration)
- [ ] Interfaces accepted, structs returned: `func New(r io.Reader) *Parser`
- [ ] No exported global mutable state
- [ ] Context as first parameter: `func Foo(ctx context.Context, ...)`

## Conventions
- **Naming**: `PascalCase` for exported, `camelCase` for unexported, short names for local vars
- **Packages**: short, lowercase, no underscores — `package http`, not `package http_utils`
- **Interfaces**: small (1-3 methods), named with `-er` suffix: `Reader`, `Stringer`
- **Errors**: `var ErrNotFound = errors.New("not found")` — sentinel errors with `Err` prefix
- **Files**: `foo.go` + `foo_test.go` in same package, `_test` package for black-box tests
- **Formatting**: `gofmt` / `goimports` — non-negotiable, never override

## Common Pitfalls
- **Nil interface**: interface holding nil pointer is NOT nil — check concrete type
- **Slice gotcha**: `append` may or may not create new backing array — don't alias slices
- **Range variable capture**: `for _, v := range items { go func() { use(v) }() }` — v is shared (fixed in Go 1.22+)
- **Map concurrency**: maps are NOT goroutine-safe — use `sync.Map` or mutex
- **Init order**: `init()` functions run in import order — avoid side effects
- **Error shadowing**: `:=` in inner scope can shadow outer `err` variable
