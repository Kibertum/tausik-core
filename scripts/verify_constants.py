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

# Durability of a verify HANDLE (v2-verify-receipt-as-argument, SEP-2567).
# Deliberately longer than DEFAULT_CACHE_TTL_S, and that difference is the
# point of the feature rather than a loosening of it. The 600 s window above is
# a PROXY for "the tree probably has not moved"; a handle needs no proxy,
# because redemption re-hashes the declared files off disk and recomputes the
# gate signature from the live config — so a tree that moved is caught by the
# thing that actually changed instead of by a clock. What the clock is still
# for is bounding how long an unspent handle stays outstanding.
#
# This number is a PUBLISHED policy, not an internal constant: SEP-2567 —
# "Durability is documented in the tool description… A policy only in server
# documentation is not visible to the model". It is stated in the tausik_verify
# tool description, in `tausik verify` output, in the signed receipt's
# `expires_at` field, and in docs/ru/receipts.md.
# Override per-project via config key `verify_handle_ttl_seconds`.
DEFAULT_HANDLE_TTL_S = 3600
