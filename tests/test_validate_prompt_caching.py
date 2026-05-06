"""Tests for scripts/validate_prompt_caching.py."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from validate_prompt_caching import classify, parse_caching  # noqa: E402


def _write_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestParseCaching:
    def test_extracts_both_cache_fields(self, tmp_path):
        p = tmp_path / "transcript.jsonl"
        _write_jsonl(
            p,
            [
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_input_tokens": 2000,
                            "cache_read_input_tokens": 0,
                        }
                    },
                },
                {
                    "type": "assistant",
                    "message": {
                        "usage": {
                            "input_tokens": 80,
                            "output_tokens": 40,
                            "cache_creation_input_tokens": 0,
                            "cache_read_input_tokens": 1800,
                        }
                    },
                },
            ],
        )
        stats = parse_caching(str(p))
        assert stats["cache_creation_input_tokens"] == 2000
        assert stats["cache_read_input_tokens"] == 1800
        assert stats["input_tokens"] == 180
        assert stats["output_tokens"] == 90
        assert stats["entries_with_cache_fields"] == 2
        assert stats["total_entries_with_usage"] == 2
        assert stats["cache_hit_rate_pct"] == round(1800 / 3800 * 100, 2)

    def test_handles_missing_cache_fields(self, tmp_path):
        p = tmp_path / "no_cache.jsonl"
        _write_jsonl(
            p,
            [
                {
                    "type": "assistant",
                    "message": {"usage": {"input_tokens": 100, "output_tokens": 50}},
                }
            ],
        )
        stats = parse_caching(str(p))
        assert stats["cache_creation_input_tokens"] == 0
        assert stats["cache_read_input_tokens"] == 0
        assert stats["entries_with_cache_fields"] == 0
        assert stats["total_entries_with_usage"] == 1
        assert stats["cache_hit_rate_pct"] == 0.0

    def test_handles_top_level_usage(self, tmp_path):
        p = tmp_path / "top.jsonl"
        _write_jsonl(
            p,
            [
                {
                    "usage": {
                        "input_tokens": 50,
                        "output_tokens": 25,
                        "cache_creation_input_tokens": 100,
                        "cache_read_input_tokens": 200,
                    }
                }
            ],
        )
        stats = parse_caching(str(p))
        assert stats["cache_creation_input_tokens"] == 100
        assert stats["cache_read_input_tokens"] == 200
        assert stats["entries_with_cache_fields"] == 1

    def test_skips_blank_lines_and_invalid_json(self, tmp_path):
        p = tmp_path / "noisy.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n")
            f.write("not json\n")
            f.write(
                json.dumps({"usage": {"input_tokens": 10, "cache_read_input_tokens": 5}}) + "\n"
            )
        stats = parse_caching(str(p))
        assert stats["input_tokens"] == 10
        assert stats["cache_read_input_tokens"] == 5

    def test_explicit_zero_cache_field_still_counted_as_present(self, tmp_path):
        """Even if cache_read_input_tokens == 0, presence of the field signals API supports caching."""
        p = tmp_path / "explicit_zero.jsonl"
        _write_jsonl(
            p,
            [{"usage": {"input_tokens": 10, "cache_read_input_tokens": 0}}],
        )
        stats = parse_caching(str(p))
        assert stats["entries_with_cache_fields"] == 1


class TestClassify:
    def test_no_cache_fields_returns_2(self):
        code, msg = classify({"entries_with_cache_fields": 0, "cache_read_input_tokens": 0})
        assert code == 2
        assert "not active" in msg.lower() or "no cache" in msg.lower()

    def test_cache_creation_but_zero_reads_returns_1(self):
        code, msg = classify({"entries_with_cache_fields": 3, "cache_read_input_tokens": 0})
        assert code == 1
        assert "miss" in msg.lower()

    def test_active_cache_returns_0(self):
        code, msg = classify({"entries_with_cache_fields": 3, "cache_read_input_tokens": 5000})
        assert code == 0
        assert "active" in msg.lower()


class TestCli:
    def test_main_missing_file_returns_64(self, tmp_path, capsys, monkeypatch):
        from validate_prompt_caching import main

        monkeypatch.setattr(
            sys, "argv", ["validate_prompt_caching.py", str(tmp_path / "nope.jsonl")]
        )
        assert main() == 64
        err = capsys.readouterr().err
        assert "not found" in err.lower()

    def test_main_no_args_returns_64(self, capsys, monkeypatch):
        from validate_prompt_caching import main

        monkeypatch.setattr(sys, "argv", ["validate_prompt_caching.py"])
        assert main() == 64

    def test_main_active_cache_returns_0(self, tmp_path, capsys, monkeypatch):
        from validate_prompt_caching import main

        p = tmp_path / "ok.jsonl"
        _write_jsonl(
            p,
            [
                {
                    "usage": {
                        "input_tokens": 10,
                        "cache_read_input_tokens": 100,
                        "cache_creation_input_tokens": 50,
                    }
                }
            ],
        )
        monkeypatch.setattr(sys, "argv", ["validate_prompt_caching.py", str(p)])
        assert main() == 0
        out = capsys.readouterr().out
        assert "cache_read_input_tokens" in out
        assert "OK" in out
