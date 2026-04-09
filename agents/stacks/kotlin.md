# Stack: Kotlin

## Testing
- **Framework**: JUnit 5 + kotlin-test (`@Test`, `assertEquals`, `assertFailsWith`)
- **Assertions**: kotlin-test or Kotest matchers (`shouldBe`, `shouldThrow`)
- **Mocking**: MockK (`every { mock.method() } returns value`, `verify { }`)
- **Coroutines**: `runTest { }` from `kotlinx-coroutines-test`
- **Integration**: `@SpringBootTest` (Spring), Ktor `testApplication { }`
- **Run**: `gradle test` / `mvn test`
- **Coverage**: Kover (`gradle koverReport`)

## Review Checklist
- [ ] `val` over `var` — immutability by default
- [ ] Data classes for DTOs/value objects (auto `equals`, `hashCode`, `copy`)
- [ ] `sealed class`/`sealed interface` for restricted hierarchies + `when` exhaustive checks
- [ ] Null safety: no `!!` (non-null assertion) — use `?.`, `?:`, `let`, `require`
- [ ] Extension functions: don't overuse — if it needs internal state, it's a method
- [ ] Coroutines: structured concurrency, no `GlobalScope`, proper `Dispatchers`
- [ ] No Java-style getters/setters — use properties
- [ ] `object` for singletons, `companion object` only for factory methods/constants

## Conventions
- **Naming**: `PascalCase` for classes, `camelCase` for functions/properties, `UPPER_CASE` for constants
- **Files**: one class per file (or related sealed hierarchy), filename matches class name
- **Null handling**: `String?` for nullable, `String` for non-null — leverage type system
- **Collections**: `listOf`/`mapOf` (immutable) over `mutableListOf`/`mutableMapOf` by default
- **Scope functions**: `let` (null-check + transform), `apply` (configure), `also` (side-effect), `run` (scope + result)
- **Build**: Gradle with Kotlin DSL (`build.gradle.kts`)

## Common Pitfalls
- **Platform types**: Java interop returns `String!` (unknown nullability) — explicitly type as `String?`
- **Data class copy()**: shallow copy only — nested mutable objects are shared
- **Coroutine leaks**: always use structured concurrency (CoroutineScope), cancel on lifecycle end
- **Lazy initialization**: `by lazy` is thread-safe by default (`LazyThreadSafetyMode.SYNCHRONIZED`)
- **Companion object**: not static — it's a singleton instance. Use `@JvmStatic` for Java interop
- **Type erasure**: `List<String>` and `List<Int>` are same at runtime — use `inline reified` for type checks
