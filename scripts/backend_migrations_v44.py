"""v44 migration SQL — explicit state handle on verification runs
(v2-verify-receipt-as-argument, decision #218 / SEP-2567).

Held in its own module to keep backend_migrations.py under the filesize gate.
``MIGRATION_V44`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[44]. Purely additive: three nullable
ALTER TABLE ADD COLUMNs, no rebuild.

All three are NULLABLE ON PURPOSE, unlike v40's `no_tests_declared INTEGER NOT
NULL DEFAULT 0`. There the default 0 was a TRUE statement about every historical
row ("this run did not declare no-tests"), so asserting it cost nothing. Here
there is no true default: a run recorded before v44 has no nonce, no expiry and
no redemption stamp, and NULL is precisely how that is spelled. Backfilling
`handle_expires_at` with any computed value would invent an expiry for a handle
that never existed, and the redemption predicate (`handle_redeemed_at IS NULL`)
would then read those rows as spendable — the replay hole this feature exists
to close. A pre-v44 row simply cannot be presented: `verify_handle_check`
refuses it at the nonce comparison, because NULL matches no nonce.

`handle_redeemed_at` is indexed together with the nonce because redemption is a
point lookup by id whose predicate reads the nonce and the stamp, and the audit
question this feature makes answerable ("which handles were minted and never
spent?") scans the stamp:
    SELECT id, task_slug, handle_expires_at FROM verification_runs
    WHERE handle_nonce IS NOT NULL AND handle_redeemed_at IS NULL;
"""

from __future__ import annotations

MIGRATION_V44: list[str] = [
    # 128-bit nonce, hex. NULL = this run was never handed out as a handle.
    "ALTER TABLE verification_runs ADD COLUMN handle_nonce TEXT",
    # ISO-8601 UTC. The receipt carries a SIGNED copy of the same instant; this
    # column is the cheap read for the refusal path, the receipt is the proof.
    "ALTER TABLE verification_runs ADD COLUMN handle_expires_at TEXT",
    # ISO-8601 UTC of the single spend. NULL = unspent; the redeem UPDATE's
    # `IS NULL` predicate is what makes redeem-once atomic.
    "ALTER TABLE verification_runs ADD COLUMN handle_redeemed_at TEXT",
    "CREATE INDEX IF NOT EXISTS idx_verify_handle "
    "ON verification_runs(handle_nonce, handle_redeemed_at)",
]
