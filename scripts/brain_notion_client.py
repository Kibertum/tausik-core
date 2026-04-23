"""Notion REST client on stdlib urllib.

Zero external deps (TAUSIK convention #19). Implements the subset of
Notion API needed for the shared brain:

  - pages.create / retrieve / update
  - databases.query (and auto-paginating iterator)
  - search

Features:
  - Bearer auth + Notion-Version header
  - Write-side throttle (default 350 ms between writes)
  - 429/5xx retry with Retry-After and exponential backoff + jitter
  - Typed error hierarchy for auth / not-found / rate-limit / server errors
  - Network (urlopen/clock/sleep) are injectable for tests

All methods return parsed JSON (Python dict). Design reference:
references/brain-db-schema.md §3 and §6.
"""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any, Callable, cast

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.notion.com/v1"
DEFAULT_VERSION = "2022-06-28"
DEFAULT_THROTTLE_MS = 350
DEFAULT_MAX_RETRIES = 5
DEFAULT_TIMEOUT = 30.0
DEFAULT_BACKOFF_CAP = 30.0


class NotionError(Exception):
    """Base class for all Notion client errors."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: dict | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.body = body or {}


class NotionAuthError(NotionError):
    """401 / 403 — integration lacks permission (or token invalid)."""


class NotionNotFoundError(NotionError):
    """404 — page / database id does not exist or is not shared."""


class NotionRateLimitError(NotionError):
    """429 retries exhausted."""


class NotionServerError(NotionError):
    """5xx retries exhausted."""


class NotionClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        version: str = DEFAULT_VERSION,
        throttle_ms: int = DEFAULT_THROTTLE_MS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        urlopen: Callable | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ):
        if not token or not isinstance(token, str):
            raise ValueError("Notion token is required")
        self._token = token
        self._base = base_url.rstrip("/")
        self._version = version
        self._throttle = throttle_ms / 1000.0
        self._max_retries = max_retries
        self._timeout = timeout
        self._urlopen = urlopen or urllib.request.urlopen
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._last_write_at: float = 0.0

    # --- Pages ---

    def pages_create(
        self,
        *,
        parent: dict,
        properties: dict,
        children: list | None = None,
    ) -> dict:
        body: dict[str, Any] = {"parent": parent, "properties": properties}
        if children:
            body["children"] = children
        return self._request("POST", "/pages", body=body, is_write=True)

    def pages_retrieve(self, page_id: str) -> dict:
        return self._request("GET", f"/pages/{page_id}")

    def pages_update(
        self,
        page_id: str,
        *,
        properties: dict | None = None,
        archived: bool | None = None,
    ) -> dict:
        body: dict[str, Any] = {}
        if properties is not None:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived
        return self._request("PATCH", f"/pages/{page_id}", body=body, is_write=True)

    # --- Databases ---

    def databases_query(
        self,
        database_id: str,
        *,
        filter: dict | None = None,  # noqa: A002 (matches Notion field name)
        sorts: list | None = None,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict:
        body: dict[str, Any] = {}
        if filter is not None:
            body["filter"] = filter
        if sorts is not None:
            body["sorts"] = sorts
        if start_cursor is not None:
            body["start_cursor"] = start_cursor
        if page_size is not None:
            body["page_size"] = page_size
        return self._request("POST", f"/databases/{database_id}/query", body=body)

    def iter_database_query(
        self,
        database_id: str,
        *,
        filter: dict | None = None,  # noqa: A002
        sorts: list | None = None,
        page_size: int | None = None,
    ) -> Iterator[dict]:
        cursor: str | None = None
        while True:
            page = self.databases_query(
                database_id,
                filter=filter,
                sorts=sorts,
                start_cursor=cursor,
                page_size=page_size,
            )
            for row in page.get("results", []):
                yield row
            if not page.get("has_more"):
                return
            cursor = page.get("next_cursor")
            if not cursor:
                return

    # --- Search ---

    def search(
        self,
        *,
        query: str | None = None,
        filter: dict | None = None,  # noqa: A002
        sort: dict | None = None,
        start_cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict:
        body: dict[str, Any] = {}
        if query is not None:
            body["query"] = query
        if filter is not None:
            body["filter"] = filter
        if sort is not None:
            body["sort"] = sort
        if start_cursor is not None:
            body["start_cursor"] = start_cursor
        if page_size is not None:
            body["page_size"] = page_size
        return self._request("POST", "/search", body=body)

    # --- Internals ---

    def _throttle_writes(self) -> None:
        now = self._clock()
        delta = now - self._last_write_at
        if self._last_write_at > 0 and delta < self._throttle:
            self._sleep(self._throttle - delta)
        self._last_write_at = self._clock()

    def _build_request(
        self, method: str, path: str, body: dict | None
    ) -> urllib.request.Request:
        url = f"{self._base}{path}"
        data = None
        if body is not None and method != "GET":
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Notion-Version", self._version)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        return req

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        is_write: bool = False,
    ) -> dict:
        if is_write:
            self._throttle_writes()
        attempt = 0
        while True:
            req = self._build_request(method, path, body)
            try:
                with self._urlopen(req, timeout=self._timeout) as resp:
                    raw = resp.read()
                if not raw:
                    return {}
                return cast(dict, json.loads(raw.decode("utf-8")))
            except urllib.error.HTTPError as e:
                status = e.code
                body_json = self._read_error_body(e)
                if status in (401, 403):
                    raise NotionAuthError(
                        f"Notion auth failed ({status})",
                        status=status,
                        body=body_json,
                    ) from e
                if status == 404:
                    raise NotionNotFoundError(
                        f"Notion resource not found: {path}",
                        status=status,
                        body=body_json,
                    ) from e
                if status == 429 or status >= 500:
                    if attempt >= self._max_retries:
                        err_cls = (
                            NotionRateLimitError if status == 429 else NotionServerError
                        )
                        raise err_cls(
                            f"Notion retries exhausted ({status})",
                            status=status,
                            body=body_json,
                        ) from e
                    delay = self._compute_backoff(attempt, e)
                    logger.warning(
                        "Notion %s %s -> %d; retry in %.2fs (%d/%d)",
                        method,
                        path,
                        status,
                        delay,
                        attempt + 1,
                        self._max_retries,
                    )
                    self._sleep(delay)
                    attempt += 1
                    continue
                raise NotionError(
                    f"Notion error ({status})",
                    status=status,
                    body=body_json,
                ) from e
            except urllib.error.URLError as e:
                if attempt >= self._max_retries:
                    raise NotionError(f"Notion network error: {e.reason}") from e
                delay = self._compute_backoff(attempt, None)
                logger.warning(
                    "Notion %s %s network error; retry in %.2fs",
                    method,
                    path,
                    delay,
                )
                self._sleep(delay)
                attempt += 1

    @staticmethod
    def _read_error_body(e: urllib.error.HTTPError) -> dict:
        try:
            raw = e.read()
        except Exception:  # noqa: BLE001
            return {}
        if not raw:
            return {}
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        try:
            return cast(dict, json.loads(text))
        except (json.JSONDecodeError, TypeError):
            return {"raw": text}

    def _compute_backoff(
        self,
        attempt: int,
        http_error: urllib.error.HTTPError | None,
    ) -> float:
        if http_error is not None and http_error.headers is not None:
            retry_after = http_error.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except (TypeError, ValueError):
                    pass
        base = min(2.0**attempt, DEFAULT_BACKOFF_CAP)
        jitter = base * 0.2 * (random.random() * 2 - 1)
        return max(0.1, base + jitter)
