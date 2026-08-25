---
slug: ne-gonyat-bootstrap-parallelno-s-full-suite-pytest
title: "Не гонять bootstrap параллельно с full-suite pytest"
type: gotcha
tags:
  - "workflow,testing,bootstrap"
task: null
edges: []
---

Тесты test hygiene (test_check_docs_hook, test_bypass_telemetry и др.) в teardown проверяют, что .tausik/config.json не менялся во время теста. bootstrap.py --ide all перезаписывает config.json. Если запустить bootstrap ПАРАЛЛЕЛЬНО с фоновым full-suite прогоном, случайный тест ловит teardown ERROR 'Test mutated the live project config'. Это ЛОЖНОЕ срабатывание (гонка), тест зелёный изолированно. Правило: делать bootstrap ДО старта full-suite, либо дождаться его завершения. Наблюдалось дважды в сессии #144 (v43 + cross-cutting задачи).
