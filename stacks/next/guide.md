# Stack: Next.js

Also read `stacks/react.md` for base React conventions and `stacks/typescript.md` for TypeScript patterns.

## Testing
- **Framework**: Jest + React Testing Library, or Vitest
- **Server components**: test with `render()` but mock server-only APIs
- **API routes**: test with `node-mocks-http` or direct function calls
- **E2E**: Playwright or Cypress (`npx playwright test`)
- **Run**: `npx jest --verbose` or `npx vitest run`
- **Coverage**: `npx jest --coverage`

## Review Checklist
- [ ] App Router (`app/`) conventions: `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`
- [ ] Server vs Client components: `"use client"` only where needed (interactivity, hooks, browser APIs)
- [ ] Data fetching: Server Components fetch directly, Client uses `useEffect`/SWR/React Query
- [ ] Metadata: `export const metadata` or `generateMetadata()` for SEO
- [ ] Route handlers: `export async function GET(request)` in `route.ts`
- [ ] Images: `next/image` with `width`/`height` or `fill` — no raw `<img>`
- [ ] Links: `next/link` for client-side navigation — no `<a href>`
- [ ] Environment variables: `NEXT_PUBLIC_` prefix for client-side, no prefix for server-only

## Conventions
- **Routing**: file-system based in `app/` — `[slug]/page.tsx` for dynamic routes
- **Layouts**: `layout.tsx` wraps children, preserved across navigations — put shared UI here
- **Server Actions**: `"use server"` functions for form submissions and mutations
- **Caching**: `fetch()` with `{ cache: 'force-cache' | 'no-store' }` or `revalidate: N`
- **Middleware**: `middleware.ts` at root for auth checks, redirects, rewrites
- **Styling**: CSS Modules (`*.module.css`), Tailwind, or styled-components with `"use client"`

## Common Pitfalls
- **Hydration mismatch**: server HTML differs from client render — use `useEffect` for client-only content, not `typeof window`
- **Server Component in Client tree**: Server Components can't be children of Client Components unless passed as `children` prop
- **`"use client"` boundary**: everything imported into a `"use client"` file becomes client-side — keep the boundary high
- **Caching defaults**: Next.js 14+ aggressively caches — use `revalidateTag`/`revalidatePath` for mutations
- **Dynamic imports**: `next/dynamic` for code splitting, but adds loading state — don't overuse
- **Server Actions errors**: uncaught errors in server actions show generic error — always try/catch and return structured errors
