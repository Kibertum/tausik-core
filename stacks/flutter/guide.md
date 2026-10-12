# Stack: Flutter

## Testing
- **Unit tests**: `flutter_test` (`test()`, `expect()`, `group()`)
- **Widget tests**: `testWidgets()`, `WidgetTester`, `find.byType()`, `tester.tap()`, `tester.pumpAndSettle()`
- **Integration tests**: `integration_test` package, `IntegrationTestWidgetsFlutterBinding`
- **Mocking**: `mockito` (`@GenerateMocks`), `mocktail` (no codegen)
- **Golden tests**: `matchesGoldenFile('snapshot.png')` for visual regression
- **Run**: `flutter test`, `flutter test --coverage`
- **Coverage**: `flutter test --coverage && genhtml coverage/lcov.info -o coverage/html`

## Review Checklist
- [ ] Widget tree not too deep — extract into separate widgets (not methods returning widgets)
- [ ] `const` constructors where possible (performance: skip rebuild)
- [ ] State management consistent: Provider/Riverpod/Bloc — pick one
- [ ] No business logic in widgets — separate into controllers/blocs/notifiers
- [ ] `dispose()` called for controllers, streams, animation controllers
- [ ] Keys used for list items in `ListView.builder` (stable unique keys)
- [ ] Null safety: no `!` operator — handle null explicitly
- [ ] Platform-specific code in `Platform.isAndroid`/`Platform.isIOS` guards

## Conventions
- **Naming**: `PascalCase` for classes/widgets, `camelCase` for variables/functions, `snake_case` for files
- **File structure**: one widget per file, `lib/` for source, `test/` mirrors `lib/`
- **State management**: `StatelessWidget` by default, `StatefulWidget` only when local state needed
- **Navigation**: GoRouter or Navigator 2.0 for declarative routing
- **Assets**: declare in `pubspec.yaml`, load with `AssetImage`/`rootBundle`
- **Formatting**: `dart format` — non-negotiable

## Common Pitfalls
- **setState() after dispose**: async operations completing after widget unmount — use `mounted` check
- **BuildContext across async gap**: don't use `context` after `await` — capture before
- **Hot reload vs restart**: stateful changes need hot restart, not just hot reload
- **Platform channels**: async only — can't call platform synchronously from Dart
- **Large widget builds**: avoid expensive computation in `build()` — cache results, use `Selector`/`select`
- **Nested Scaffolds**: each screen should have its own `Scaffold`, don't nest them
