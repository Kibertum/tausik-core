# Stack: JavaScript

Also see `stacks/typescript.md` — prefer TypeScript for new projects.

## Testing
- **Framework**: Jest or Vitest
- **Assertions**: `expect(x).toBe(y)`, `expect(fn).toThrow()`
- **Mocking**: `jest.mock()`, `jest.fn()`, `jest.spyOn()`
- **Async**: `async/await` in tests, `expect(promise).resolves.toBe()`
- **Run**: `npx jest --verbose` or `npx vitest run`
- **Coverage**: `npx jest --coverage`

## Review Checklist
- [ ] `const` by default, `let` only when reassignment needed, never `var`
- [ ] `===` strict equality, never `==` (avoids type coercion traps)
- [ ] No implicit type coercion: `'' + x` for string, `Number(x)` or `+x` for number — be explicit
- [ ] Optional chaining `?.` and nullish coalescing `??` instead of `&&`/`||` chains
- [ ] Destructuring for object/array access: `const { name, age } = user`
- [ ] Arrow functions for callbacks, regular functions for methods
- [ ] Promises: always handle rejections (`.catch()` or `try/catch` with `await`)
- [ ] No `console.log` in production — use a logging library

## Conventions
- **Naming**: `camelCase` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants
- **Modules**: ES modules (`import`/`export`) over CommonJS (`require`)
- **Async**: `async/await` over `.then()` chains
- **Iteration**: `for...of` for arrays, `Object.entries()` for objects, `.map()`/`.filter()` for transforms
- **Error handling**: custom error classes extending `Error`, structured error responses
- **Formatting**: Prettier + ESLint — automated, no debates

## Common Pitfalls
- **`this` binding**: arrow functions don't bind `this` — use for callbacks. Regular functions for object methods
- **Floating point**: `0.1 + 0.2 !== 0.3` — use integer math (cents not dollars) or `Number.EPSILON`
- **typeof null**: `typeof null === 'object'` — check with `x === null`
- **Array holes**: `[1,,3].map(x => x)` — sparse arrays behave unexpectedly
- **Event loop blocking**: CPU-heavy code blocks entire loop — use `Worker` threads or chunking
- **Prototype pollution**: `obj[key] = value` with user-controlled `key` — validate key names, use `Map`
