# Stack: Vue

## Testing
- **Framework**: Vitest + Vue Test Utils (VTU)
- **Config**: `vitest.config.ts`, `@vue/test-utils`
- **Mounting**: `mount()` for full render, `shallowMount()` for isolated component tests
- **Finding**: `wrapper.find('.class')`, `wrapper.findComponent(Child)`, `wrapper.get('[data-test="id"]')`
- **Events**: `await wrapper.find('button').trigger('click')` + `await nextTick()`
- **Props**: `mount(Component, { props: { ... } })`
- **Pinia**: `createTestingPinia()` with `initialState` and `stubActions`
- **Run**: `npx vitest run --reporter=verbose`
- **Coverage**: `npx vitest run --coverage`

## Review Checklist
- [ ] Composition API (`<script setup>`) over Options API for new code
- [ ] Reactive state: `ref()` for primitives, `reactive()` for objects — never mix
- [ ] `computed` for derived state, not methods called in template
- [ ] `watch`/`watchEffect` cleanup: return cleanup function for async operations
- [ ] Props: typed with `defineProps<{ ... }>()`, required props marked explicitly
- [ ] Emits: declared with `defineEmits<{ ... }>()`, typed events
- [ ] `v-for` always has `:key` — stable unique ID, not index
- [ ] No direct prop mutation — emit event to parent
- [ ] Template refs typed: `const el = ref<HTMLInputElement | null>(null)`

## Conventions
- **Naming**: `PascalCase` for components, `camelCase` for composables (`useAuth`), `kebab-case` for events
- **Files**: SFC (`.vue`) with `<script setup lang="ts">`, one component per file
- **Composables**: extract reusable logic into `composables/useX.ts`
- **State management**: local refs → composables → Pinia stores (escalating complexity)
- **Routing**: `vue-router` with lazy loading: `() => import('./views/Page.vue')`

## Common Pitfalls
- **Reactivity loss**: destructuring `reactive()` loses reactivity — use `toRefs()` or `storeToRefs()`
- **Ref unwrapping**: refs auto-unwrap in templates but NOT in `<script>` — use `.value`
- **Watch timing**: `watch` is lazy by default, `watchEffect` runs immediately
- **Async setup**: `<script setup>` doesn't support top-level await without `<Suspense>`
- **Event naming**: `@update:modelValue` not `@update:model-value` for v-model
- **Memory leaks**: `onUnmounted` for cleanup — intervals, event listeners, subscriptions
