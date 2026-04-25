# Stack: Java

## Testing
- **Framework**: JUnit 5 (`@Test`, `@BeforeEach`, `@AfterEach`, `@ParameterizedTest`)
- **Assertions**: AssertJ (`assertThat(x).isEqualTo(y)`) or JUnit (`assertEquals`)
- **Mocking**: Mockito (`@Mock`, `@InjectMocks`, `when().thenReturn()`)
- **Integration**: `@SpringBootTest`, `@WebMvcTest`, `@DataJpaTest` (Spring)
- **Test containers**: Testcontainers for DB/Redis/Kafka integration tests
- **Run**: `mvn test` / `gradle test`
- **Coverage**: JaCoCo (`mvn jacoco:report`)

## Review Checklist
- [ ] No raw types — use generics (`List<String>` not `List`)
- [ ] Immutable objects where possible — `final` fields, no setters
- [ ] `Optional<T>` for nullable returns, never `null` for collections (use empty collection)
- [ ] Resources closed properly — try-with-resources for `AutoCloseable`
- [ ] No checked exceptions in public API unless caller can recover
- [ ] `equals()` and `hashCode()` overridden together (use `@EqualsAndHashCode` or records)
- [ ] Thread safety: `synchronized`, `ConcurrentHashMap`, or immutable objects
- [ ] Logging: SLF4J with parameterized messages (`log.info("User {}", id)`)

## Conventions
- **Naming**: `PascalCase` for classes, `camelCase` for methods/variables, `UPPER_CASE` for constants
- **Packages**: reverse domain (`com.company.project.module`)
- **Records**: use Java 16+ records for DTOs/value objects
- **Streams**: prefer streams over loops for transformations, but not for side effects
- **Build**: Maven (`pom.xml`) or Gradle (`build.gradle.kts`)
- **Formatting**: Google Java Format or project-specific `.editorconfig`

## Common Pitfalls
- **NullPointerException**: use `Optional`, `@NonNull`/`@Nullable` annotations, null-safe APIs
- **String comparison**: `.equals()` not `==` (reference vs value equality)
- **Date/Time**: use `java.time` API (LocalDate, Instant, ZonedDateTime), never `java.util.Date`
- **ConcurrentModificationException**: don't modify collection while iterating — use Iterator.remove() or copy
- **Memory leaks**: static collections, unclosed streams, inner class holding outer reference
- **Serialization**: avoid Java serialization — use JSON (Jackson/Gson)
