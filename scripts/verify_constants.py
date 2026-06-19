"""Single source of truth for verify-cache constants.

Stdlib-only, ZERO project imports — this module sits at the bottom of the
verify dependency graph so that service_verification, verify_cache and
verify_recent_lookup can all import the TTL without forming an import cycle.
Do not add imports from sibling verify modules here.
"""

from __future__ import annotations

# Default freshness window (seconds) for cached verify runs (QG-2 Verify-First).
# After this many seconds since the recorded run the cache is treated as stale
# regardless of files_hash agreement. Aligned with SENAR Rule 9.3 checkpoint
# cadence (30-50 tool calls ~= 5-15 min) — the cache covers one coherent work
# session. Override per-project via config key `verify_cache_ttl_seconds`.
DEFAULT_CACHE_TTL_S = 600
