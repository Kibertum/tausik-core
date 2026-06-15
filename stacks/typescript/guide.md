# Stack: TypeScript

## Testing
- **Framework**: Jest (ts-jest) or Vitest
- **Config**: `tsconfig.json` for strict mode, `jest.config.ts` or `vitest.config.ts`
- **Type testing**: `expectTypeOf` (vitest), `tsd` package, or compile-time checks
- **Mocking**: typed mocks with `jest.Mocked<T>`, `vi.fn<T>()` in Vitest
- **Run**: `npx jest` / `npx vitest run`
- **Coverage**: `npx vitest run --coverage` / `npx jest --coverage`

## Review Checklist
- [ ] `strict: true` in `tsconfig.json` (includes `noImplicitAny`, `strictNullChecks`)
- [ ] No `any` — use `unknown` for truly unknown types, then narrow
- [ ] No `as` type assertions — use type guards or `satisfies` instead
- [ ] No `!` non-null assertions — handle the null case explicitly
- [ ] Discriminated unions over optional fields for state variants
- [ ] `readonly` on arrays/objects that shouldn't mutate
- [ ] Enums: prefer `const` objects with `as const` over `enum` keyword
- [ ] Generic constraints: `<T extends Base>` not just `<T>`
- [ ] Utility types: `Partial<T>`, `Pick<T, K>`, `Omit<T, K>` over manual retyping

## Conventions
- **Naming**: `PascalCase` for types/interfaces/classes, `camelCase` for variables/functions
- **Interfaces vs Types**: interfaces for objects with methods, types for unions/intersections/mapped
- **Exports**: named exports over default exports (better refactoring, auto-import)
- **Null handling**: `??` for nullish, `?.` for optional chaining — never `||` for defaults (falsy trap)
- **Imports**: `import type { Foo }` for type-only imports (tree-shaking)

## Common Pitfalls
- **Structural typing**: `{ name: string }` matches ANY object with `name: string` — use branded types for IDs
- **Excess property checks**: only work on object literals, not variables
- **Enum pitfalls**: numeric enums allow reverse mapping and arbitrary numbers — use string enums or const objects
- **Promise handling**: unhandled rejections — always `await` or `.catch()`
- **Type widening**: `let x = "hello"` → `string`, `const x = "hello"` → `"hello"` literal
- **Index signatures**: `Record<string, T>` allows undefined values — check before use
