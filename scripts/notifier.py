"""Outbound webhook notifications — Slack / Discord / Telegram.

All functions are best-effort and non-blocking. They respect these env vars:

- `TAUSIK_SLACK_WEBHOOK` — Slack Incoming Webhook URL
- `TAUSIK_DISCORD_WEBHOOK` — Discord Channel Webhook URL
- `TAUSIK_TELEGRAM_WEBHOOK` — Telegram Bot API URL template,
   e.g. `https://api.telegram.org/botTOKEN/sendMessage?chat_id=CHAT`

Network/4xx/5xx errors never raise — the caller gets a bool for observability
but missing delivery never breaks a task.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


_TIMEOUT = 4.0


def _post_json(url: str, payload: dict) -> bool:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return bool(200 <= resp.status < 300)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        OSError,
        TimeoutError,
    ) as exc:
        print(f"notifier: webhook POST failed ({exc})", file=sys.stderr)
        return False


def send_slack(text: str) -> bool:
    url = (os.environ.get("TAUSIK_SLACK_WEBHOOK") or "").strip()
    if not url:
        return False
    return _post_json(url, {"text": text})


def send_discord(text: str) -> bool:
    url = (os.environ.get("TAUSIK_DISCORD_WEBHOOK") or "").strip()
    if not url:
        return False
    return _post_json(url, {"content": text})


def send_telegram(text: str) -> bool:
    url = (os.environ.get("TAUSIK_TELEGRAM_WEBHOOK") or "").strip()
    if not url:
        return False
    return _post_json(url, {"text": text})


def send_notification(text: str) -> dict[str, bool]:
    """Fan-out to every webhook that has an env var set.

    Returns {channel: sent} so the caller can log partial failures.
    """
    return {
        "slack": send_slack(text),
        "discord": send_discord(text),
        "telegram": send_telegram(text),
    }
