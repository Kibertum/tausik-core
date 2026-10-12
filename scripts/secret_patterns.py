"""Canonical credential-pattern matching shared by hooks and safe persistence."""

from __future__ import annotations

import re

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"\baws_secret(?:_access)?_key\b\s*[:=]\s*[A-Za-z0-9/+]{40}")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[abp]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{24,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{32,}\b")),
    ("notion_secret", re.compile(r"\b(?:secret|ntn)_[A-Za-z0-9]{32,}\b")),
    (
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"\b(?:api_key|apikey|secret|token|password|passwd)\s*[:=]\s*['\"][A-Za-z0-9/+_=\-]{20,}['\"]",
            re.IGNORECASE,
        ),
    ),
]


def redact_secret_literals(text: str) -> tuple[str, list[str]]:
    """Redact every credential match without exposing its value."""
    redacted = str(text)
    names: list[str] = []
    for name, pattern in PATTERNS:
        if pattern.search(redacted):
            names.append(name)
            if name == "private_key_block":
                # The detector identifies the header, not a key grammar. Once
                # it fires, retaining any of the field risks persisting the
                # opaque key body or footer.
                return "[redacted]", names
            redacted = pattern.sub("[redacted]", redacted)
    return redacted, names


def secret_literal_names(text: str) -> list[str]:
    """Return detector names only; callers must never log matched literals."""
    return [name for name, pattern in PATTERNS if pattern.search(str(text))]
