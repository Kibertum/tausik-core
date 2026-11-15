"""Canonical, privacy-safe public upgrade-scenario manifest."""

from __future__ import annotations

from datetime import datetime
import re
from typing import TypedDict, cast

from release_qualification_git import QualificationError

_GIT_OBJECT = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION_TAG = re.compile(r"^v\d+\.\d+\.\d+$")
_UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_GITHUB_REPOSITORY = re.compile(
    r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/"
    r"[A-Za-z0-9_.-]+\.git$"
)


class ScenarioPublication(TypedDict):
    observed_at: str
    anonymous_url: str


class ScenarioCurrent(TypedDict):
    boundary: str


class ScenarioPublished(TypedDict):
    tag: str
    commit: str
    tree: str
    boundary: str


class ScenarioManifest(TypedDict):
    schema: int
    publication: ScenarioPublication
    current: ScenarioCurrent
    published: list[ScenarioPublished]


def validate_scenario_manifest(document: object) -> ScenarioManifest:
    """Reject non-canonical or privacy-bearing public upgrade manifests."""

    if not isinstance(document, dict) or set(document) != {
        "schema",
        "publication",
        "current",
        "published",
    }:
        raise QualificationError("scenario manifest is not canonical v1")
    publication = document.get("publication")
    current = document.get("current")
    published = document.get("published")
    if (
        document.get("schema") != 1
        or current != {"boundary": "clean-current"}
        or not isinstance(published, list)
    ):
        raise QualificationError("scenario manifest is not canonical v1")
    if (
        not isinstance(publication, dict)
        or set(publication) != {"observed_at", "anonymous_url"}
        or not isinstance(publication.get("observed_at"), str)
        or not isinstance(publication.get("anonymous_url"), str)
        or not _UTC_TIMESTAMP.fullmatch(publication["observed_at"])
        or not _GITHUB_REPOSITORY.fullmatch(publication["anonymous_url"])
    ):
        raise QualificationError("scenario manifest is not canonical v1")
    try:
        observed_at = datetime.strptime(publication["observed_at"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise QualificationError("scenario manifest is not canonical v1") from exc
    if observed_at.strftime("%Y-%m-%dT%H:%M:%SZ") != publication["observed_at"]:
        raise QualificationError("scenario manifest is not canonical v1")
    for row in published:
        if not isinstance(row, dict) or set(row) != {"tag", "commit", "tree", "boundary"}:
            raise QualificationError("scenario manifest contains non-canonical public data")
        if not isinstance(row.get("boundary"), str) or not _SLUG.fullmatch(row["boundary"]):
            raise QualificationError("scenario manifest contains non-canonical public data")
        if not isinstance(row["tag"], str) or not _VERSION_TAG.fullmatch(row["tag"]):
            raise QualificationError("scenario manifest contains non-canonical public data")
        for object_key in ("commit", "tree"):
            if not isinstance(row[object_key], str) or not _GIT_OBJECT.fullmatch(row[object_key]):
                raise QualificationError("scenario manifest contains non-canonical public data")
    return cast(ScenarioManifest, document)
