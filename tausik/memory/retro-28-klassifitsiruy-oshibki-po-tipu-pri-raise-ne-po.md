---
slug: retro-28-klassifitsiruy-oshibki-po-tipu-pri-raise-ne-po
title: "Retro #28: классифицируй ошибки по типу при raise, не по string-match в catch"
type: pattern
tags:
  - api-client
  - brain
  - error-handling
task: null
edges: []
---

brain-fallback-offline переключил `NotionError + str(e).startswith(...)` на отдельные типы (`NotionNetworkError`, `NotionRateLimitError(retry_after)`) поднимаемые в клиенте. String-match в catch — fragile: любое изменение формулировки ошибки → silent misclassification. Правило для всех клиентов внешних API: один type = один сценарий восстановления; retry_after/category передавай полями исключения, не парсингом сообщения.
