# Stack: React

## Testing
- **Framework**: Jest + React Testing Library (RTL)
- **Config**: `jest.config.js` or `package.json[jest]`
- **Rendering**: `render()` from `@testing-library/react`, never `ReactDOM.render`
- **Queries**: prefer `getByRole` > `getByLabelText` > `getByText` > `getByTestId`
- **Events**: `@testing-library/user-event` (v14+) over `fireEvent`
- **Async**: `waitFor()`, `findBy*` queries — never manual `setTimeout`
- **Mocking**: MSW for API mocks, `jest.mock()` for modules
- **Run**: `npx jest --verbose` or `npm test`
- **Coverage**: `npx jest --coverage`

## Review Checklist
- [ ] Hooks follow Rules of Hooks (no conditionals, no loops)
- [ ] `useEffect` has correct dependency array (ESLint `exhaustive-deps`)
- [ ] `useEffect` cleanup for subscriptions, timers, AbortController
- [ ] `key` prop on list items — stable IDs, never array index (unless static list)
- [ ] No inline object/array/function creation in JSX props (causes re-renders)
- [ ] `useMemo`/`useCallback` only where measured perf benefit exists
- [ ] Error boundaries around async/fallible components
- [ ] Controlled components: form state in React, not DOM
- [ ] No direct DOM manipulation (`document.querySelector` etc.)

## Conventions
- **Naming**: `PascalCase` for components, `camelCase` for functions/hooks, `UPPER_CASE` for constants
- **Files**: one component per file, filename matches component name
- **Hooks**: custom hooks start with `use` prefix
- **Props**: destructure in function signature: `function Button({ label, onClick })`
- **State management**: local state first → context → external store (Zustand/Redux)
- **Styling**: CSS Modules, Tailwind, or styled-components — pick one and be consistent

## Common Pitfalls
- **Stale closures**: `useEffect`/`useCallback` capturing old state — add to deps array
- **Infinite re-renders**: setting state inside `useEffect` without proper deps
- **Prop drilling**: more than 3 levels → use Context or composition
- **Over-rendering**: parent re-renders → all children re-render. Use `React.memo` selectively
- **SSR hydration mismatch**: `useEffect` for client-only code, not conditional rendering
- **Memory leaks**: async operations completing after unmount — use AbortController
