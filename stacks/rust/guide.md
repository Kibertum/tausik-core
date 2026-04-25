# Stack: Rust

## Testing
- **Framework**: built-in `#[test]`, `cargo test`
- **Organization**: tests in same file (`#[cfg(test)] mod tests`) or `tests/` dir for integration
- **Assertions**: `assert!`, `assert_eq!`, `assert_ne!`, `#[should_panic]`
- **Fixtures**: no built-in — use helper functions, `once_cell`, or test crates
- **Async**: `#[tokio::test]` for async tests
- **Mocking**: `mockall` crate, or trait-based manual mocks
- **Run**: `cargo test -- --nocapture` (show output)
- **Coverage**: `cargo tarpaulin` or `cargo llvm-cov`

## Review Checklist
- [ ] No `.unwrap()` or `.expect()` in library code — use `?` operator with proper error types
- [ ] Error types implement `std::error::Error` + `Display`
- [ ] Lifetimes explicit where needed, avoid `'static` unless required
- [ ] No unnecessary `clone()` — prefer borrowing
- [ ] `unsafe` blocks: minimal scope, documented invariants, tested
- [ ] Derive macros used: `Debug`, `Clone`, `PartialEq` where appropriate
- [ ] Public API has doc comments (`///`) with examples
- [ ] No `panic!` in library code — return `Result<T, E>`

## Conventions
- **Naming**: `snake_case` for functions/variables, `PascalCase` for types/traits, `SCREAMING_CASE` for constants
- **Error handling**: `thiserror` for library errors, `anyhow` for applications
- **Modules**: `mod.rs` or `module_name.rs` (2018 edition), re-export with `pub use`
- **Formatting**: `rustfmt` — non-negotiable, never override
- **Linting**: `clippy` — treat warnings as errors in CI

## Common Pitfalls
- **Borrow checker fights**: redesign ownership instead of adding lifetimes — often means wrong data structure
- **String types**: `&str` for borrowed, `String` for owned — don't `String::from()` everywhere
- **Iterator invalidation**: can't mutate collection while iterating — use `retain()`, `drain()`, or collect-then-mutate
- **Deadlocks with Mutex**: always lock in consistent order, prefer `RwLock` for read-heavy workloads
- **Async footguns**: `Send + Sync` bounds on futures, don't hold MutexGuard across `.await`
- **Feature flags**: additive only — features must not disable functionality
