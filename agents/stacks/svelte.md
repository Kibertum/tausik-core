# Stack: Svelte

## Testing
- **Framework**: Vitest + `@testing-library/svelte`
- **Rendering**: `render(Component, { props: { ... } })`, `cleanup()` after each
- **Queries**: `screen.getByRole()`, `screen.getByText()`, `screen.getByTestId()`
- **Events**: `await fireEvent.click(element)` + `await tick()`
- **Stores**: test stores independently, mock via context in component tests
- **Run**: `npx vitest run --reporter=verbose`
- **Coverage**: `npx vitest run --coverage`

## Review Checklist
- [ ] Reactive declarations: `$:` for derived state, not manual updates
- [ ] Stores: `writable`/`readable`/`derived` — subscribe/unsubscribe handled by `$store` syntax
- [ ] No direct DOM manipulation — use actions (`use:action`) or bind
- [ ] `{#each}` blocks have unique `key` expressions: `{#each items as item (item.id)}`
- [ ] Component props typed with `export let prop: Type` (Svelte 4) or `$props()` (Svelte 5)
- [ ] Event forwarding: `on:click` without handler forwards to parent
- [ ] Transitions/animations: use built-in `transition:`, `in:`, `out:` directives
- [ ] Slots for composition: `<slot>` with fallback content

## Conventions
- **Naming**: `PascalCase` for components, `camelCase` for variables, `kebab-case` for events
- **Files**: `.svelte` SFC (template + script + style), one component per file
- **State**: Svelte 5 runes (`$state`, `$derived`, `$effect`) or Svelte 4 reactive (`$:`, stores)
- **Routing**: SvelteKit file-based routing (`+page.svelte`, `+layout.svelte`, `+server.ts`)
- **Styling**: scoped by default in `<style>`, `:global()` for escape hatch

## Common Pitfalls
- **Reactivity requires assignment**: `array.push(item)` doesn't trigger — use `array = [...array, item]`
- **Tick timing**: DOM updates are batched — use `await tick()` to read post-update DOM
- **Two-way binding**: `bind:value` is convenient but creates tight coupling — prefer events for components
- **Store memory leaks**: manual subscriptions need `unsubscribe()` — use `$store` auto-subscription instead
- **SSR hydration**: SvelteKit SSR — browser APIs (`window`, `localStorage`) only in `onMount` or `browser` check
- **Transition conflicts**: `in:` and `out:` directives conflict with conditional `{#if}` — use `transition:` for toggle
