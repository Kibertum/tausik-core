"""Roles CRUD — hybrid SQLite + markdown profile.

`roles` table (slug PK + metadata) is source-of-truth for which roles exist
and which tasks reference them. The markdown profile at agents/roles/<slug>.md
(in TAUSIK source) is bootstrap-copied to .claude/roles/. User-created roles
(via `tausik role create`) write their profile to a USER override location:
`.tausik/roles/<slug>.md`. Bootstrap NEVER touches `.tausik/`, so user
markdown survives re-bootstrap. The bootstrap source-tree path is read-only
to user-created profiles.

Free functions over a backend so SkillsMixin can stay slim.
"""

from __future__ import annotations

import os
from typing import Any

from tausik_utils import (
    ServiceError,
    safe_single_line,
    utcnow_iso,
    validate_length,
    validate_slug,
)

ROLES_DIR_REL = os.path.join("agents", "roles")
DEPLOYED_ROLES_DIR_REL = os.path.join(".claude", "roles")
USER_ROLES_DIR_REL = os.path.join(".tausik", "roles")


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def _profile_path_source(slug: str) -> str:
    """Read-only path to bootstrap-source profiles (built-in roles)."""
    return os.path.join(_repo_root(), ROLES_DIR_REL, f"{slug}.md")


def _profile_path_user(slug: str) -> str:
    """Writable path for user-created role profiles. Survives re-bootstrap."""
    return os.path.join(os.getcwd(), USER_ROLES_DIR_REL, f"{slug}.md")


def _profile_path_deployed(slug: str) -> str:
    """IDE-deployed copy of source profile (overwritten by bootstrap)."""
    return os.path.join(os.getcwd(), DEPLOYED_ROLES_DIR_REL, f"{slug}.md")


def _read_profile(slug: str) -> str | None:
    """Read profile: user override → source → deployed."""
    for path in (
        _profile_path_user(slug),
        _profile_path_source(slug),
        _profile_path_deployed(slug),
    ):
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                pass
    return None


def role_list(be: Any) -> list[dict[str, Any]]:
    """All roles ordered by slug, with task usage count."""
    rows: list[dict[str, Any]] = be._q(
        "SELECT r.slug, r.title, r.description, r.created_at, r.updated_at, "
        "(SELECT COUNT(*) FROM tasks WHERE role = r.slug) AS task_count "
        "FROM roles r ORDER BY r.slug ASC"
    )
    return rows


def role_show(be: Any, slug: str) -> dict[str, Any]:
    """Role row + markdown profile + linked task count. Raises if not found."""
    row: dict[str, Any] | None = be._q1("SELECT * FROM roles WHERE slug = ?", (slug,))
    if not row:
        raise ServiceError(f"Role '{slug}' not found.")
    cnt = be._q1("SELECT COUNT(*) AS n FROM tasks WHERE role = ?", (slug,))
    row["task_count"] = (cnt or {}).get("n", 0)
    row["profile"] = _read_profile(slug)
    row["profile_path_source"] = _profile_path_source(slug)
    return row


_safe_text = safe_single_line


def role_create(
    be: Any,
    slug: str,
    title: str,
    description: str | None = None,
    extends: str | None = None,
) -> dict[str, Any]:
    """Insert role row. Optionally clone profile from `extends` slug.

    Profile is written to .tausik/roles/<slug>.md (USER dir, NEVER overwritten
    by bootstrap). Bootstrap-source profiles in agents/roles/ are read-only.
    """
    import sqlite3 as _sqlite3

    validate_slug(slug)
    validate_length("title", title)
    title = _safe_text(title) or title
    description = _safe_text(description)
    if extends is not None:
        validate_slug(extends)
        if not _read_profile(extends):
            raise ServiceError(
                f"Cannot extend '{extends}' — role profile not found in user/source/deployed."
            )
    if be._q1("SELECT slug FROM roles WHERE slug = ?", (slug,)):
        raise ServiceError(f"Role '{slug}' already exists.")
    target = _profile_path_user(slug)
    profile_existed = os.path.isfile(target)
    if not profile_existed:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        body = _read_profile(extends) if extends else None
        tmp = target + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                if body is None:
                    safe_title = title.replace("\n", " ").replace("\r", " ").strip()
                    f.write(f"# Role: {safe_title}\n\nProfile for the {slug} role.\n")
                else:
                    f.write(body)
            os.replace(tmp, target)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    now = utcnow_iso()
    try:
        be._conn.execute(
            "INSERT INTO roles(slug, title, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (slug, title, description, now, now),
        )
        be._conn.commit()
    except _sqlite3.IntegrityError:
        if not profile_existed:
            try:
                os.unlink(target)
            except OSError:
                pass
        raise ServiceError(f"Role '{slug}' already exists.") from None
    return role_show(be, slug)


def _write_skeleton(path: str, slug: str, title: str) -> None:
    safe_title = title.replace("\n", " ").replace("\r", " ").strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Role: {safe_title}\n\nProfile for the {slug} role.\n")


def role_update(
    be: Any,
    slug: str,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update title/description metadata. Markdown body is edited by hand."""
    if not be._q1("SELECT slug FROM roles WHERE slug = ?", (slug,)):
        raise ServiceError(f"Role '{slug}' not found.")
    fields: dict[str, str] = {}
    if title is not None:
        validate_length("title", title)
        fields["title"] = _safe_text(title) or title
    if description is not None:
        fields["description"] = _safe_text(description) or ""
    if not fields:
        return role_show(be, slug)
    fields["updated_at"] = utcnow_iso()
    cols = ", ".join(f"{k} = ?" for k in fields)
    be._conn.execute(
        f"UPDATE roles SET {cols} WHERE slug = ?", (*fields.values(), slug)
    )
    be._conn.commit()
    return role_show(be, slug)


def role_delete(be: Any, slug: str, force: bool = False) -> str:
    """Delete role. Refuses when tasks reference it unless force=True.

    Markdown profile is left in place — manual cleanup if desired.
    With force=True on referenced role: also NULLs out tasks.role to avoid
    orphan strings (DB has no FK).
    """
    if not be._q1("SELECT slug FROM roles WHERE slug = ?", (slug,)):
        raise ServiceError(f"Role '{slug}' not found.")
    cnt = be._q1("SELECT COUNT(*) AS n FROM tasks WHERE role = ?", (slug,))
    refs = (cnt or {}).get("n", 0)
    if refs and not force:
        raise ServiceError(
            f"Role '{slug}' is referenced by {refs} task(s). "
            f"Pass force=True to delete anyway."
        )
    be.begin_tx()
    try:
        if refs:
            be._conn.execute("UPDATE tasks SET role = NULL WHERE role = ?", (slug,))
        be._conn.execute("DELETE FROM roles WHERE slug = ?", (slug,))
        import sqlite3 as _sqlite3

        try:
            be.event_add(
                "role",
                slug,
                "force_delete" if (refs and force) else "delete",
                f'{{"refs_detached":{refs}}}',
            )
        except _sqlite3.Error as e:
            import logging

            logging.getLogger("tausik.roles").warning("audit failed: %s", e)
        be.commit_tx()
    except Exception:
        be.rollback_tx()
        raise
    profile_loc = _profile_path_user(slug)
    return (
        f"Role '{slug}' deleted "
        f"({refs} task(s) detached; profile retained at {profile_loc})."
    )


def seed_existing_roles(be: Any) -> dict[str, Any]:
    """Bootstrap: create roles from agents/roles/*.md + distinct task.role values.

    Idempotent — uses INSERT OR IGNORE semantics through `role_create` skip.
    Returns {scanned, inserted, skipped}.
    """
    out = {"scanned": 0, "inserted": 0, "skipped": 0, "from_files": 0, "from_tasks": 0}
    roles_src = os.path.join(_repo_root(), ROLES_DIR_REL)
    seen: set[str] = set()
    if os.path.isdir(roles_src):
        for entry in sorted(os.listdir(roles_src)):
            if not entry.endswith(".md") or entry.startswith("_"):
                continue
            slug = entry[:-3]
            out["scanned"] += 1
            if be._q1("SELECT slug FROM roles WHERE slug = ?", (slug,)):
                out["skipped"] += 1
                seen.add(slug)
                continue
            title = _extract_title(os.path.join(roles_src, entry)) or slug.title()
            try:
                _insert_minimal(be, slug, title)
                out["inserted"] += 1
                out["from_files"] += 1
                seen.add(slug)
            except ServiceError:
                out["skipped"] += 1
    rows = be._q(
        "SELECT DISTINCT role FROM tasks WHERE role IS NOT NULL AND role != ''"
    )
    for r in rows:
        slug = r.get("role") or ""
        if not slug or slug in seen:
            continue
        try:
            validate_slug(slug)
        except (ServiceError, ValueError):
            continue
        if be._q1("SELECT slug FROM roles WHERE slug = ?", (slug,)):
            continue
        try:
            _insert_minimal(be, slug, slug.title())
            out["inserted"] += 1
            out["from_tasks"] += 1
        except (ServiceError, ValueError):
            out["skipped"] += 1
        except Exception:
            import logging

            logging.getLogger("tausik.roles").warning(
                "seed: unexpected failure inserting %s", slug
            )
            out["skipped"] += 1
    return out


def _insert_minimal(be: Any, slug: str, title: str) -> None:
    now = utcnow_iso()
    be._conn.execute(
        "INSERT INTO roles(slug, title, description, created_at, updated_at) "
        "VALUES (?, ?, NULL, ?, ?)",
        (slug, title, now, now),
    )
    be._conn.commit()


def _extract_title(path: str) -> str | None:
    """Pull first '# Role: NAME' or '# NAME' from markdown."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# Role:"):
                    return line[len("# Role:") :].strip()
                if line.startswith("# "):
                    return line[2:].strip()
                if line and not line.startswith("#"):
                    return None
    except OSError:
        pass
    return None
