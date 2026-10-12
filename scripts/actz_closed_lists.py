"""The closed lists RENAR fixes for ACTZ -- the one place their values live.

Same split as ``adapt_closed_lists`` and for the same reason: these tuples are
DECLARATIONS the standard governs (RENAR Sec5A, ADR-011), kept apart from the
behaviour in ``service_actz``. Every value here is mirrored by a DB CHECK; the
LENGTH of a list is never written beside it in prose -- a hand-written count is
correct until the next amendment and then lies in each file separately
(tests/closed_list_counts.py, the guard already built for ADAPT's categories).
"""

from __future__ import annotations

# Contractual lifecycle, Sec5A: draft -> sent -> signed -> superseded. 'signed'
# is COMPUTED from the signature-role coverage below, never written as an
# independent fact -- see service_actz.actz_sign.
ACTZ_STATUSES: tuple[str, ...] = ("draft", "sent", "signed", "superseded")

# Sec5.5.3: an ACTZ exits the internal-product non-conformance declaration only
# when signed by TWO INDEPENDENT persons. Both roles are REQUIRED today -- there
# is no unilateral path (ADR-017 is `proposed`, decision #255: do not implement
# it now, but do not hardcode a shape that would need a migration to add it
# later either). The set below is what `actz_sign` currently requires to reach
# 'signed'; widening it to admit a unilateral mode is a future CHECK-widening
# migration, the same shape v50 already used for ADAPT_STATUSES.
SIGNATURE_ROLES: tuple[str, ...] = ("architect", "client")
REQUIRED_SIGNATURE_ROLES: tuple[str, ...] = ("architect", "client")

LINK_TARGETS: tuple[str, ...] = ("task", "spec")

ACTZ_BODY_SCHEMA = "renar-actz/v1"
