"""Infrastructure refusals: when the ENVIRONMENT failed, say so with its own code.

fail-closed-covers-policy-but-not-infrastructure (1.10, github#109). Verification
depends on infrastructure at four points, enumerated from the code:

* the verification_runs / gate_runs write — RECEIPT_PERSISTENCE_UNAVAILABLE;
* signing the receipt with the project key, and writing it back —
  SIGNER_UNAVAILABLE (a key exists but the signature could not be made: until
  1.10 this printed a WARNING and the run stayed green and closable);
* reading the gate configuration — POLICY_PROFILE_UNAVAILABLE.

Each refusal line starts with "INFRASTRUCTURE:" so a reader knows to fix the
environment, not the code — the same split refusal kinds made for evidence
(STALE / FAILED / NOT FOUND). Codes borrowed from HELM AI Kernel's inbox
refusals.
"""

from __future__ import annotations

RECEIPT_PERSISTENCE_UNAVAILABLE = "RECEIPT_PERSISTENCE_UNAVAILABLE"
SIGNER_UNAVAILABLE = "SIGNER_UNAVAILABLE"
POLICY_PROFILE_UNAVAILABLE = "POLICY_PROFILE_UNAVAILABLE"

_WHAT = {
    RECEIPT_PERSISTENCE_UNAVAILABLE: "the verification run could not be written to the database",
    SIGNER_UNAVAILABLE: "a project key is configured but the receipt could not be signed or stored",
    POLICY_PROFILE_UNAVAILABLE: "the gate configuration could not be read",
}


def line(code: str, detail: str = "") -> str:
    """One refusal line: code, what is unavailable, and that the fix is the environment."""
    tail = f" ({detail})" if detail else ""
    return (
        f"INFRASTRUCTURE: {code} — {_WHAT[code]}{tail}. This is not a gate verdict about "
        "the code: fix the environment, then re-run."
    )
