---
slug: ed25519-dlya-evidence-attestation-realizuem-pure-python-po
task: v15-crypto-keymgmt
date: "2026-06-11"
edges: []
---

## Decision

ed25519 для evidence-attestation реализуем pure-python по RFC 8032 (hashlib.sha512 + bigint), без зависимости от cryptography/pynacl

## Rationale

Идентичность проекта: Python 3.11+ stdlib-only. Подпись receipts — низкочастотная операция, 30-60мс приемлемо. Не constant-time, но модель угроз локальная: атакующий с таймингом уже читает файл ключа. Optional fast-path через cryptography можно добавить позже без смены формата.
