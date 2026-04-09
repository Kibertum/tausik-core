# Stack: Nuxt

Also read `stacks/vue.md` for base Vue conventions and `stacks/typescript.md` for TypeScript patterns.

## Testing
- **Framework**: Vitest + `@nuxt/test-utils`
- **Unit**: `mountSuspended()` for component tests with Nuxt context (auto-imports, composables)
- **API routes**: `$fetch` in tests or direct handler function calls
- **E2E**: Playwright with `createPage()` from `@nuxt/test-utils/e2e`
- **Run**: `npx vitest run`
- **Coverage**: `npx vitest run --coverage`

## Review Checklist
- [ ] Auto-imports used correctly: composables from `composables/`, utils from `utils/`, components from `components/`
- [ ] `useFetch`/`useAsyncData` for data fetching — not raw `fetch` in `<script setup>`
- [ ] Server routes in `server/api/` with proper H3 event handlers
- [ ] `useState` for SSR-safe shared state (not plain `ref` at module level)
- [ ] `useRuntimeConfig()` for environment variables — not `process.env` in client
- [ ] SEO: `useHead()` or `useSeoMeta()` for meta tags
- [ ] Middleware: route middleware in `middleware/` — `defineNuxtRouteMiddleware`
- [ ] Error handling: `<NuxtErrorBoundary>`, `showError()`, `error.vue`

## Conventions
- **Routing**: file-system based in `pages/` — `[id].vue` for dynamic routes
- **Layouts**: `layouts/default.vue`, switch with `definePageMeta({ layout: 'admin' })`
- **Server**: `server/api/` for API routes, `server/middleware/` for server middleware
- **Plugins**: `plugins/` for app-level setup (auto-registered)
- **Composables**: `composables/` for shared logic (auto-imported)
- **State**: Pinia stores in `stores/` (recommended over raw `useState`)

## Common Pitfalls
- **SSR state pollution**: module-level `ref()` shares state across requests on server — use `useState()` or Pinia
- **Hydration mismatch**: client-only code must be in `<ClientOnly>` component or `onMounted`
- **Auto-import confusion**: implicitly available composables can be hard to trace — check `.nuxt/imports.d.ts`
- **useFetch in watch**: `useFetch` doesn't re-fetch on reactive param change by default — use `watch` option or `refresh()`
- **Payload size**: `useAsyncData` serializes return value to HTML — keep payloads small, don't return full DB objects
- **Plugin order**: plugins run in filesystem order — prefix with numbers (`01.auth.ts`) for explicit ordering
