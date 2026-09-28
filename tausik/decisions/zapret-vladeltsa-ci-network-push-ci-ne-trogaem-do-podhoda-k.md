---
slug: zapret-vladeltsa-ci-network-push-ci-ne-trogaem-do-podhoda-k
task: owner-constraints-are-read-at-the-point-of-action
date: "2026-09-28"
edges: []
---

## Decision

ЗАПРЕТ ВЛАДЕЛЬЦА [ci,network,push]: CI не трогаем до подхода к релизу — указание владельца, смена #277. Пуш на origin разрешён, но каждый пуш заводит пайплайн, поэтому до релиза коммиты остаются локальными.

## Rationale
