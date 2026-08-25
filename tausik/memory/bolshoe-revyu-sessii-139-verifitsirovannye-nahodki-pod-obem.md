---
slug: bolshoe-revyu-sessii-139-verifitsirovannye-nahodki-pod-obem
title: "Большое ревью сессии #139: верифицированные находки под объём 1.8 (widescope)"
type: context
tags: []
task: null
edges: []
---

Рой из 4 агентов (scope/архитектура/тесты/доки) под релиз 1.8. Scope-решение пользователя: 1.8 = группы I–XI+XV (70 задач, вкл. km/kb/brainh); 2.0 = только gmcp/v2/ext (18 задач). KB кросс-проектная (kb-global) двинута ВПЕРЁД — нужна пользователю лично.

ВЕРИФИЦИРОВАННЫЕ находки (feed конкретных задач):
- Model registry ТРИПЛИЦИРОВАН: cost_pricing.py:59-76 + model_profiles.py + model_routing_matrix.py держат один набор claude-* ID вручную. Плюс двойной источник цен (hardcode + config llm_pricing). → новая задача "model-registry-single-source" (must-fix-1.8).
- project_config.py: ровно 400 строк, get_service() в загрузчике конфига (:396-400) ПОДТВЕРЖДЁН — блокер standalone. Импортёров РЕАЛЬНО 41 (не 139). 9 ответственностей. Re-export фасад (:24-37) косметический — сплит не снизил связность. → project-config-god-module-split (#34): вынести get_service()+pricing СЕЙЧАС, полный сплит 2.0.
- mypy: 29 ошибок/18 файлов (24 owned), НЕ 16. state_export.py(4)+state_import.py(3) — НОВЫЙ долг 1.8, must-fix. → mypy-baseline-debt.
- 8 файлов в 3 строках от лимита 400 (project_cli_doctor, config_trust, service_task, project_parser, pwsh_cmd_parse, _common, renar_conformance) — гейт геймится. → l26-filesize-gate-revisit.
- gate_test_citation.py + gate_tdd_order.py БЕЗ поведенческих тестов (citation — fail-closed анти-фабрикация с 3 задокументированными байпасами без регресса). → gate-integrity-tests (#11).
- scoped-pytest СЛЕП к кросс-режущим: resolve_test_files_for_relevant = чистый basename-маппинг, задача закрывается зелёной ломая чужой тест. → scoped-pytest-blind-to-crosscutting-tests (#20).
- Доки СЛАБЕЕ кода: senar-compliance-matrix зовёт scope-энфорсмент Warning, а scope_write_gate.py хардблокит exit-2; hooks.md знает 21 хук, не знает scope_write_gate.py (реально 22+1). → docs-enforcement-drift-matrix (#30).
- status CLI↔MCP расходятся: CLI даёт risk+RENAR, MCP даёт exploration+audit, пересечения нет. → status-cli-mcp-divergence (#31).
- Суита: 0 warnings (чисто). Версия консистентна на 1.7.0 в живой цепочке; устаревшие снапшоты: senar матрицы v1.5.1, TODO.md v1.5.0, scripts/README 1.1.0 → version-coherence-1-8 (#7).</content>
<type>context</type>
<tags>release-1.8,review,architecture,mypy,tests,doc-drift</tags>
<task_slug>wave0-suite-green</task_slug>
</invoke>
