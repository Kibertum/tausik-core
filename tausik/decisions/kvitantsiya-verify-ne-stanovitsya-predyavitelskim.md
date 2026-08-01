---
slug: kvitantsiya-verify-ne-stanovitsya-predyavitelskim
task: v2-verify-receipt-as-argument
date: "2026-08-01"
edges: []
---

## Decision

Квитанция verify НЕ становится предъявительским документом. Принят приём SEP-2567 «explicit state handle»: verify возвращает ХЕНДЛ (run_id + 128-битный nonce), task done принимает его обычным аргументом, сервер валидирует точечным lookup. Уходит поиск по свежести и TTL, а не база. Подпись остаётся tamper-evidence против внешних правок БД, а не авторизацией.

## Rationale

Спец решает это нормативно и дважды. SEP-2567 (Final): сессии удалены, канон — «returning an identifier from a creation tool and accepting it as a parameter», то есть ИДЕНТИФИКАТОР, а не само состояние. SEP-2322 (Final): «servers MUST always validate that state, as the client is an untrusted intermediary». Самопроверяемая квитанция, чей ключ клиент может прочитать, — ровно тот случай, от которого спец предостерегает: seed лежит в .tausik/keys/project.key ВНУТРИ рабочего дерева, доступного агенту на чтение (docs/ru/receipts.md:217), а вынос отложен задачей l26-signing-key-boundary. Сегодня агент квитанции не получает вовсе (CLI печатает только «run #N», MCP её не возвращает) — это неявная, но действующая защита; отдать её предъявителем значит понизить гарантию, а не перенести. Замер: квитанция НЕ самодостаточна — в ней нет ни списка файлов, ни подписи команд гейтов, поэтому проверить то, что проверяет нынешний поиск, она физически не может.
