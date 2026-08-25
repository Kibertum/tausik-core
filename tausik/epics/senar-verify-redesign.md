---
slug: senar-verify-redesign
title: "SENAR-aligned verification: scoped per-task + recorded runs"
status: done
---

Разделить QG-2 на per-task scoped verify (по tier'у задачи, через relevant_files → test files) и periodic audit (Rule 9.5, отдельно). Записывать verify runs в БД, переиспользовать недавние зелёные. Stack-agnostic, без coupling к git/python.
