# Stack: Swift

## Testing
- **Framework**: XCTest (`XCTestCase`, `func testX()`, `XCTAssertEqual`)
- **Async**: `func testAsync() async throws { }` (Swift 5.5+)
- **UI testing**: XCUITest (`XCUIApplication`, `app.buttons["Login"].tap()`)
- **Mocking**: protocol-based manual mocks (no reflection), or Mockingbird/Cuckoo
- **Snapshot**: `swift-snapshot-testing` for UI regression tests
- **Run**: `cmd+U` in Xcode, `swift test` for SPM packages
- **Coverage**: Xcode → Product → Scheme → Code Coverage

## Review Checklist
- [ ] `let` over `var` — immutability by default
- [ ] `guard let` for early returns, `if let` for optional binding
- [ ] No force unwrap (`!`) except `IBOutlet`s and known-safe cases
- [ ] `struct` over `class` unless reference semantics needed (value types are default)
- [ ] Protocol-oriented design: composition over inheritance
- [ ] Proper `Sendable` conformance for concurrency safety
- [ ] `@MainActor` for UI-touching code
- [ ] Access control: `private` > `fileprivate` > `internal` > `public` > `open`

## Conventions
- **Naming**: `PascalCase` for types/protocols, `camelCase` for functions/properties, `kPrefix` convention is deprecated
- **Protocols**: `-able`/`-ible` suffix for capability protocols (`Codable`, `Identifiable`)
- **Closures**: trailing closure syntax, use `[weak self]` to avoid retain cycles
- **Error handling**: `throw`/`catch` for recoverable, `fatalError` only for programmer errors
- **SwiftUI**: `View` bodies should be small — extract subviews
- **Formatting**: swift-format or SwiftLint

## Common Pitfalls
- **Retain cycles**: `[weak self]` in closures capturing `self`, especially in `NotificationCenter`, delegates
- **Value type semantics**: `struct` arrays/dicts are copied on mutation (CoW optimized, but semantically independent)
- **Optional chaining depth**: `a?.b?.c?.d` is code smell — unwrap earlier
- **Actor reentrancy**: `actor` methods can be interleaved at `await` points — don't assume state unchanged
- **ABI stability**: only ship `@frozen` enums if you guarantee no new cases
- **MainActor deadlock**: calling `MainActor.assumeIsolated` from background thread crashes
