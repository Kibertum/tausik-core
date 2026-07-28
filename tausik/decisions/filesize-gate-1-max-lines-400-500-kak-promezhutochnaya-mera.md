---
slug: filesize-gate-1-max-lines-400-500-kak-promezhutochnaya-mera
task: l26-filesize-gate-revisit
date: "2026-07-27"
edges: []
---

## Decision

Filesize-gate: (1) max_lines 400->500 как промежуточная мера; (2) exempt dirs/basenames читать из коммитного tausik/gates.json (переживает свежий клон), хардкод в gate_filesize.py = fallback; (3) смену единицы на MRO-public-surface + де-exempt mcp/ вынести в отдельную complex-задачу.

## Rationale

Аудит #129 подтверждён замером: ПЯТЬ файлов ровно на 400 строк (service_task_done, service_task, project_parser, project_cli_doctor, gate_registry, config_trust) + ~10 в полосе 390-399 — письмо под лимит, не под концепт; ~30 модулей-обёрток документируют себя как split ради гейта. «Поднять лимит» (один из трёх разрешённых AC1) выбран промежуточным: настоящая проблема — ЕДИНИЦА (гейт не видит god-объекты ProjectService=117/SQLiteBackend=129 методов из миксинов ≤400 и явно исключает handlers.py 1289), а её замена требует class-graph анализа и правки core — отдельная complex-задача. Cap=500 подобран по замеру: поглощает КАЖДОЕ документированное слияние обёрток (gate_runner 393+gate_filesize 97=485; service_knowledge 394+cq_row 48=437) с запасом, файл >500 по-прежнему блокируется — регрессия защиты сохранена. Config-driven exempts из tausik/gates.json устраняет правку исходника ради исключения и то, что .tausik/config.json (gitignored) не доезжает до свежего клона.
