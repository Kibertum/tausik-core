"""MCP transport for the bounded L3 review cohort workflow."""

from __future__ import annotations

import json
from typing import Any


def _handle_review_cohort(svc: Any, args: dict[str, Any]) -> str:
    from review_cohort import cohort_summary
    from review_cohort_request import execute_cohort_request

    try:
        out, json_output = execute_cohort_request(svc, args)
    except (KeyError, TypeError, ValueError) as exc:
        return f"Error: {exc}"
    return json.dumps(out, ensure_ascii=False, indent=2) if json_output else cohort_summary(out)
