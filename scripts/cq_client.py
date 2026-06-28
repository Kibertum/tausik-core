"""Mozilla cq client -- cross-project knowledge sharing for AI agents.

Stdlib-only HTTP client for cq Team API. No external dependencies.
Graceful degradation: returns empty results if cq is not available.

Config in .tausik/config.json:
  "cq": {"endpoint": "http://localhost:8742", "api_key": "..."}
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("tausik.cq")

DEFAULT_ENDPOINT = "http://localhost:8742"
TIMEOUT = 5  # seconds


class CqClient:
    """Minimal cq Team API client (stdlib only)."""

    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, api_key: str = ""):
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Unsupported URL scheme '{parsed.scheme}'. Only http:// and https:// are allowed."
            )
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    def _request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        """Make HTTP request. Returns parsed JSON or None on failure."""
        url = f"{self.endpoint}{path}"
        if params:
            # Handle list params (domain=a&domain=b)
            parts = []
            for k, v in params.items():
                if isinstance(v, list):
                    for item in v:
                        parts.append(f"{k}={urllib.parse.quote(str(item))}")
                else:
                    parts.append(f"{k}={urllib.parse.quote(str(v))}")
            url += "?" + "&".join(parts)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode())
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            OSError,
            json.JSONDecodeError,
        ) as e:
            logger.debug("cq request failed: %s %s -> %s", method, path, e)
            return None

    def query(
        self,
        domains: list[str],
        language: str = "",
        framework: str = "",
        limit: int = 5,
    ) -> list[dict]:
        """Query cq for knowledge units matching domains."""
        params: dict[str, Any] = {"domain": domains, "limit": limit}
        if language:
            params["language"] = language
        if framework:
            params["framework"] = framework
        result = self._request("GET", "/query", params=params)
        return result if isinstance(result, list) else []

    def propose(
        self,
        domains: list[str],
        summary: str,
        detail: str = "",
        action: str = "",
        languages: list[str] | None = None,
        created_by: str = "tausik",
    ) -> dict[str, Any] | None:
        """Propose a knowledge unit to cq."""
        data = {
            "domain": domains,
            "insight": {
                "summary": summary,
                "detail": detail or summary,
                "action": action,
            },
            "context": {
                "languages": languages or [],
                "frameworks": [],
                "pattern": "",
            },
            "created_by": created_by,
        }
        result = self._request("POST", "/propose", data=data)
        return dict(result) if isinstance(result, dict) else None

    def confirm(self, unit_id: str) -> dict[str, Any] | None:
        """Confirm a knowledge unit (increases confidence)."""
        safe_id = urllib.parse.quote(str(unit_id), safe="")
        result = self._request("POST", f"/confirm/{safe_id}")
        return dict(result) if isinstance(result, dict) else None

    def health(self) -> bool:
        """Check if cq server is available."""
        result = self._request("GET", "/health")
        return result is not None


def get_cq_client(config: dict) -> CqClient | None:
    """Create CqClient from .tausik/config.json cq section. Returns None if not configured."""
    cq_config = config.get("cq", {})
    if not cq_config.get("endpoint"):
        return None
    return CqClient(
        endpoint=cq_config["endpoint"],
        api_key=cq_config.get("api_key", ""),
    )
