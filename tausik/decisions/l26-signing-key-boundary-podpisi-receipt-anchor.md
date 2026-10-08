---
slug: l26-signing-key-boundary-podpisi-receipt-anchor
task: l26-signing-key-boundary
date: "2026-07-22"
edges: []
---

## Decision

l26-signing-key-boundary: подписи receipt/anchor документируются как tamper-evidence против ВНЕШНИХ правок tausik.db, но НЕ attestation против агента; вынос ключа из зоны записи агента (managed-путь/keychain/отдельный подписант) ОТЛОЖЕН как отдельный кросс-платформенный дизайн key-custody.

## Rationale

Вынос seed за пределы рабочего дерева требует самостоятельного кросс-платформенного дизайна (Windows не имеет POSIX-mode; keychain/отдельный процесс-подписант — эпик сам по себе). Немедленный выигрыш по целостности и юридической точности (EU AI Act, авг.2026) — честно НАЗВАТЬ границу того, что подпись доказывает, а не подразумевать attestation, который .tausik/keys/project.key в рабочем дереве дать не может. Плюс закрыта тихая деградация: сбой подписи теперь наблюдаем (Receipt: WARNING + событие receipt_sign_failed), а не молча равен 'нет ключа'. Migration-путь для проектов, которым нужна attestation: managed-конфиг/ключ вне дерева — будущая задача.
