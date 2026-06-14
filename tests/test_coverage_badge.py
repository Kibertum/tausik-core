"""Regression: coverage badge in README + CI uploads the coverage artifact.

Guards the v15p-coverage-badge deliverable. Asserts the presence of the static
badge and the CI artifact-upload step (not a live %), so the test is stable
even when coverage.json is absent locally.
"""

from __future__ import annotations

import os

_REPO = os.path.join(os.path.dirname(__file__), "..")


def _read(rel: str) -> str:
    with open(os.path.join(_REPO, rel), encoding="utf-8") as f:
        return f.read()


class TestCoverageBadge:
    def test_readme_has_coverage_badge(self):
        readme = _read("README.md")
        assert "img.shields.io/badge/coverage-" in readme

    def test_baseline_documented(self):
        readme = _read("README.md").lower()
        assert "coverage" in readme and "refresh" in readme  # how-to-refresh noted

    def test_ci_uploads_coverage_artifact(self):
        wf = _read(".github/workflows/test-coverage.yml")
        assert "upload-artifact" in wf
        assert "coverage.json" in wf
        # Negative path: absent coverage.json must not fail the upload step.
        assert "if-no-files-found: ignore" in wf

    def test_coverage_json_gitignored(self):
        assert "coverage.json" in _read(".gitignore")
