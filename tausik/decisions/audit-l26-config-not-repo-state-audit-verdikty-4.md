---
slug: audit-l26-config-not-repo-state-audit-verdikty-4
task: l26-config-not-repo-state-audit
date: "2026-07-21"
edges: []
---

## Decision

Аудит l26-config-not-repo-state-audit, вердикты 4 потребителей load_config: (3) check_claudemd_drift → FIX (load_project_config, scoped к project_dir). Provenance model_routing → FIX (config_source/raw_layers, честный источник). (1) resolve_gate_signature → NO-CHANGE обоснованно (предмет — эффективный набор гейтов, fail-safe). (2) _factor_gate_coverage → РЕАЛЬНЫЙ, но security-adjacent (подписанный рецепт/schema) → изолирован в follow-up risk-gate-coverage-configured-count-in-check.

## Rationale

Правило оракула (#266): потребитель, судящий «ожидаемое репо-состояние», обязан читать ТОТ ЖЕ вход, что и производитель. Bootstrap генерит CLAUDE.md из сырого .tausik/config.json (load_bootstrap_config→json.load), значит drift-чек обязан читать load_project_config, не merged — иначе managed-тир (output_mode) делает один коммит дрейфующим на одной машине и чистым на другой. Signature — контрпример: его предмет ЗАКОННО эффективный конфиг (что реально запускается), merged корректен, машинозависимость fail-safe и не разъезжается в одном flow. Дисциплина handoff: security-adjacent (подписанный рецепт/schema) не делать между делом → изоляция (2).
