---
slug: raboty-po-v1-7-0-podderzhka-opencode-vedem-pryamo-v-main
task: opencode-ide-support
date: "2026-07-14"
edges: []
---

## Decision

Работы по v1.7.0 (поддержка OpenCode) ведём прямо в main, без feature-ветки feat/opencode-support.

## Rationale

Явное решение пользователя (сессия #107). Изменения аддитивны и защищены гардами: dispatch-ветка opencode не влияет на другие IDE, а тест test_docs_no_fake_npm_packages.py держит инвариант «дока = SCAFFOLD_IDES» в обе стороны, поэтому промежуточное состояние main не может тихо заявить неподкреплённую поддержку. Порядок задач (генератор → плагин → включение) сам по себе гарантирует, что main не окажется в состоянии «объявили поддержку без принуждения».
