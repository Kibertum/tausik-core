"""SENAR verification cache: record + lookup verify runs to skip redundant gates.

Per SENAR Rule 5 (Verification Checklist tiers), per-task verification should
be scoped — not a full-suite re-run. To avoid wasted cycles, every successful
gate run is recorded with a stable hash of the relevant files. On subsequent
`task done` calls within the freshness window, if the same files have not
changed, the cached result is reused.

Stack-agnostic: the cache layer doesn't know about pytest/cargo/etc. — it
records `(command, exit_code)` and trusts the caller to recompute the right
hash for the file set being verified.
"""

from __future__ import annotations

# v1.3.4 git-diff cross-check lives in its own module for filesize compliance;
# re-export so existing callers keep working with `service_verification.X`.
from verify_git_diff import (  # noqa: F401
    changed_files_since,
    is_declared_consistent_with_git_diff,
)

# l26-verify-git-diff-wire: tri-state scope description + the narrow
# security-only block. Kept in its own module for filesize compliance.
from verify_scope_honesty import (  # noqa: F401
    STATUS_UNDER_DECLARED,
    describe_declared_scope,
    security_block_reason,
)

# Single source of truth for the verify-cache TTL; re-exported here so callers
# (e.g. service_gates) keep importing `service_verification.DEFAULT_CACHE_TTL_S`.
from verify_constants import DEFAULT_CACHE_TTL_S  # noqa: F401

# v14b-filesize-debt-paydown: security pattern definitions + is_security_sensitive
# moved to security_pattern.py for filesize compliance. Re-exported below so
# existing callers (service_gates, tests/*) keep working unchanged.
from security_pattern import (  # noqa: F401, E402
    _SEC_BASE,
    _SEC_EXT,
    _SECURITY_BASENAMES,
    _SECURITY_EXTENSIONS,
    _SECURITY_PATH_TOKENS,
    is_security_sensitive,
)


# v1.3.4: compute_files_hash extracted to verify_files_hash.py for filesize
# compliance. Re-exported so existing callers don't need to change.
from verify_files_hash import (  # noqa: F401, E402
    _FILES_HASH_CONTENT_SAMPLE_BYTES,
    compute_files_hash,
)
from verify_recent_lookup import lookup_recent_for_task  # noqa: F401, E402


# is_security_sensitive moved to security_pattern.py — re-exported above.


# l26-verify-git-diff-wire: record_run + _utcnow_iso extracted to
# verify_run_record.py for filesize compliance when the declared-scope
# columns were added. Re-exported so every existing caller keeps working.
#
# verify-record-failure-swallowed added the fail-closed vocabulary alongside
# them: `_record_verification` now raises `VerificationRecordError` rather than
# logging and returning None, and callers turn that into a blocking verdict
# with `record_failure_result` / `RECORD_FAILED_STATUS`.
from verify_run_record import (  # noqa: F401, E402
    RECORD_FAILED_STATUS,
    RECORD_GATE_NAME,
    VerificationRecordError,
    _utcnow_iso,
    record_failure_result,
    record_run,
)


# v14b-filesize-debt-paydown: cache helpers (is_cache_allowed,
# resolve_gate_signature, _build_cache_command, has_fresh_verify_run) moved to
# verify_cache.py. Re-exported here so all existing callers (service_gates,
# service_task, tests/*) continue importing them from service_verification.
from verify_cache import (  # noqa: F401, E402
    _build_cache_command,
    has_fresh_verify_run,
    is_cache_allowed,
    resolve_gate_signature,
)

# cli-verify-bypasses-cache-guards: the cache-aware run itself moved to
# verify_cached_run.py. Collapsing the CLI's duplicate write path into it —
# plus recording the two blocking verdicts that previously left no trace —
# pushed this file past the 400-line filesize gate. Same pattern as every
# earlier split: the logic lives in its own module, this one stays the facade,
# and `service_verification.run_gates_with_cache` keeps working for ~30 call
# sites and for the test that monkeypatches it by that name.
from verify_cached_run import (  # noqa: F401, E402
    DEFAULT_PIPELINE_TIMEOUT_S,
    GateEnvelopeTimeoutError,
    resolve_pipeline_timeout_s,
    run_gates_with_cache,
)
