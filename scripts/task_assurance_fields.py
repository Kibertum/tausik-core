"""Validation and storage normalization for task assurance declarations."""

from __future__ import annotations

import json
from typing import Any

from assurance_policy import validate_impact, validate_profiles
from tausik_utils import ServiceError


def normalize(fields: dict[str, Any]) -> None:
    """Validate task assurance JSON before any task or budget write."""
    for name, validator in (
        ("assurance_profiles", validate_profiles),
        ("assurance_impact", validate_impact),
    ):
        if name not in fields:
            continue
        value = fields[name]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise ServiceError(f"{name} must be valid JSON") from exc
        errors = validator(value)
        if errors:
            raise ServiceError("; ".join(errors))
        fields[name] = json.dumps(value, ensure_ascii=False, sort_keys=True)
