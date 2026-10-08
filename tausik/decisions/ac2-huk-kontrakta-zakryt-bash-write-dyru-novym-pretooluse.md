---
slug: ac2-huk-kontrakta-zakryt-bash-write-dyru-novym-pretooluse
task: l26-hook-contract-review
date: "2026-07-22"
edges: []
---

## Decision

AC2 хук-контракта: закрыть Bash-write дыру НОВЫМ PreToolUse-гейтом (matcher Bash + NotebookEdit), переиспользующим token-парсер bash_firewall (_scan_target/_split_subcommands/_mentions_interpreter), а не вторым парсером. Гейт детектирует write-векторы, резолвит целевой путь и применяет ту же QG-0 + scope-ACL логику, что Write-гейты. Остаточный риск обфускации (base64|sh, path-в-переменной, exec) документируется в agent-contract.md как явная граница принуждения.

## Rationale

Второй парсер разошёлся бы с реальным (conv #266: гейт судит копией, не производителем) и повторил бы quote-regression #128. Полное закрытие обфускации в shell недостижимо — AC2 прямо допускает «закрыть ИЛИ явно задокументировать границу»; молчание недопустимо, документированная граница — да. NotebookEdit добавлен в тот же гейт-набор (тоже был непокрыт).
