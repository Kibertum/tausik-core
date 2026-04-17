"""Test outbound webhook notifier (Slack / Discord / Telegram)."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from notifier import send_discord, send_notification, send_slack, send_telegram


class _FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestChannels:
    def test_slack_posts_text_field(self, monkeypatch):
        monkeypatch.setenv(
            "TAUSIK_SLACK_WEBHOOK", "https://hooks.slack.com/services/xxx"
        )
        captured = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["data"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert send_slack("hi") is True
        assert captured["data"] == {"text": "hi"}
        assert captured["url"].startswith("https://hooks.slack.com/")

    def test_discord_posts_content_field(self, monkeypatch):
        monkeypatch.setenv(
            "TAUSIK_DISCORD_WEBHOOK", "https://discord.com/api/webhooks/xxx"
        )
        captured = {}

        def fake_urlopen(req, timeout):
            captured["data"] = json.loads(req.data.decode("utf-8"))
            return _FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert send_discord("hi") is True
        assert captured["data"] == {"content": "hi"}

    def test_telegram_posts_text_field(self, monkeypatch):
        monkeypatch.setenv(
            "TAUSIK_TELEGRAM_WEBHOOK",
            "https://api.telegram.org/botTOKEN/sendMessage?chat_id=123",
        )
        with patch("urllib.request.urlopen", return_value=_FakeResponse()) as mock:
            assert send_telegram("hi") is True
        mock.assert_called_once()

    def test_missing_webhook_returns_false_without_network(self, monkeypatch):
        monkeypatch.delenv("TAUSIK_SLACK_WEBHOOK", raising=False)
        with patch("urllib.request.urlopen") as mock:
            assert send_slack("hi") is False
        mock.assert_not_called()

    def test_empty_webhook_env_returns_false(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_DISCORD_WEBHOOK", "   ")
        assert send_discord("hi") is False


class TestErrorHandling:
    def test_network_error_returns_false(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_SLACK_WEBHOOK", "https://hooks.slack.com/xxx")
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("unreachable"),
        ):
            assert send_slack("hi") is False

    def test_4xx_response_returns_false(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_SLACK_WEBHOOK", "https://hooks.slack.com/xxx")
        with patch("urllib.request.urlopen", return_value=_FakeResponse(status=403)):
            assert send_slack("hi") is False


class TestFanout:
    def test_send_notification_reports_per_channel(self, monkeypatch):
        monkeypatch.setenv("TAUSIK_SLACK_WEBHOOK", "https://hooks.slack.com/s")
        monkeypatch.delenv("TAUSIK_DISCORD_WEBHOOK", raising=False)
        monkeypatch.delenv("TAUSIK_TELEGRAM_WEBHOOK", raising=False)
        with patch("urllib.request.urlopen", return_value=_FakeResponse()):
            result = send_notification("hello")
        assert result["slack"] is True
        assert result["discord"] is False
        assert result["telegram"] is False

    def test_no_env_vars_all_false(self, monkeypatch):
        for v in (
            "TAUSIK_SLACK_WEBHOOK",
            "TAUSIK_DISCORD_WEBHOOK",
            "TAUSIK_TELEGRAM_WEBHOOK",
        ):
            monkeypatch.delenv(v, raising=False)
        with patch("urllib.request.urlopen") as mock:
            result = send_notification("hi")
        mock.assert_not_called()
        assert result == {"slack": False, "discord": False, "telegram": False}


class TestHookScript:
    def test_non_task_done_tool_exits_silently(self, tmp_path):
        import subprocess

        hook = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "hooks", "notify_on_done.py"
        )
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"}
        r = subprocess.run(
            [sys.executable, hook],
            input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "x"}}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert r.returncode == 0
        assert r.stderr == ""
