---
slug: v16-plugin-arch-and-docs
title: "v1.6 — Stack Plugin Architecture + Documentation Overhaul"
status: done
---

Превратить TAUSIK из hardcoded-stack фреймворка в pluggable. Один стек = один self-contained модуль с stack.json + guide.md. User customization через layered registry (.tausik/stacks/) с deep-merge override semantics — bootstrap НИКОГДА не трогает user overrides. Параллельно — комплексное обновление всей документации (устранение drift, single canonical entry, honest multi-IDE matrix, customization + upgrade-safety guides).
