"""The closed lists RENAR fixes for ADAPT — the one place their values live.

Split out of ``service_adapts`` when that module crossed the filesize limit, and
the split is more than hygiene: these tuples are DECLARATIONS the standard
governs, while the module they came from is behaviour. Everything keeps
importing them from ``service_adapts``, which re-exports — two dozen call
sites, none of which should care where a constant is stored.

Every value here is mirrored by a DB CHECK, and the ones that may drift from it
are checked against the live schema by tests (``check_domain``). The LENGTH of a
list is never written beside it: a hand-written count is correct until the next
amendment and then lies in each file separately (tests/closed_list_counts.py).
"""

from __future__ import annotations

# RENAR backward-finding categories — the standard's CLOSED list §7.4.4.
FINDING_CATEGORIES: tuple[str, ...] = (
    "contradiction",
    "gap",
    "hidden-assumption",
    "feasibility",
    "regulatory",
    "terminology",
    "scope",
)

# §7.5 AS THE STANDARD NOW WRITES IT: the architect signs, and nobody else.
# ADR-011 withdrew the client signature under ADAPT and said why — the client
# was signing an engineering document they had not read and could not assess.
# The boundary runs by AUDIENCE, not by content: what is shown to the client
# and approved is an obligation and lives in ACTZ; what is not shown is
# interpretation and lives in ADAPT. Verified against the corpus text, not just
# the ADR: standard/07-adapt.md §7.5 is titled "Утверждение ADAPT — подпись
# архитектора" and carries a paragraph explaining the absence.
#
# THE ROLE `client` SURVIVES IN THE SCHEMA AND NOT HERE, on purpose. This tuple
# is what may be RECORDED from now on; a signature already written is an audit
# record, and V1 forbids erasing it. See backend_schema_adapts for the CHECK
# that still admits it and renar_drift for the finding that NAMES each survivor
# rather than deleting it.
SIGNATURE_ROLES: tuple[str, ...] = ("architect",)

# What the schema still accepts, so history stays readable. Never widen the
# tuple above to match this one: that would re-admit the withdrawn norm. A test
# pins this against the LIVE CHECK — a declaration about the substrate has to
# be read from the substrate, or the two drift apart in silence.
HISTORICAL_SIGNATURE_ROLES: tuple[str, ...] = ("client", "architect")

LINK_TARGETS: tuple[str, ...] = ("task", "spec")

# §7.8.1 закрывает перечень статусов ADAPT; значения и их порядок — как в
# стандарте. До v50 расхождение шло в ОБЕ стороны: лишний 'signed', которого в
# закрытом перечне стандарта нет, и отсутствующий 'approved', которого §13.3.3
# стр.77 ТРЕБУЕТ для ветви findings-present. Второе тяжелее первого: CHECK базы
# отклонял 'approved', то есть требуемое состояние было НЕДОСТИЖИМО, а не
# просто не достигнуто.
ADAPT_STATUSES: tuple[str, ...] = (
    "draft",
    "review",
    "asked",
    "answered",
    "approved",
    "frozen",
    "superseded",
)

ADAPT_BODY_SCHEMA = "renar-adapt/v1"
