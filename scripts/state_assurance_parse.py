"""Assurance validation at the git-state parse boundary."""

from __future__ import annotations

import json
from typing import Any

from assurance_policy import validate_impact, validate_profiles
from state_parse import ParseError


def validate_task_assurance_frontmatter(fm: dict[str, Any], rel: str) -> None:
    errors: list[str] = []
    if "assurance_profiles" in fm:
        errors.extend(validate_profiles(fm["assurance_profiles"]))
    if "assurance_impact" in fm:
        impact = fm["assurance_impact"]
        if isinstance(impact, str):
            try:
                impact = json.loads(impact)
            except ValueError:
                errors.append("assurance_impact must be valid JSON")
                impact = None
        errors.extend(validate_impact(impact))
    if errors:
        raise ParseError(f"{rel}: {'; '.join(errors)}")
