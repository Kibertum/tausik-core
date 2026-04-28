"""Brain init wizard — creates 4 Notion databases and writes .tausik/config.json.

Public API (pure + injectable):
  db_schema(category) -> dict          -- Notion property schema per category
  create_brain_databases(client, ppid) -- call databases_create ×4
  merge_brain_config(existing, updates)-- pure dict merger
  run_wizard(args, io, client_factory, config_ops) -> dict

All side-effectful inputs are injected: the CLI layer wires real impls,
tests inject fakes. Token is NEVER persisted — only env var name.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Protocol

import brain_config
import brain_project_registry
from brain_notion_client import NotionError, NotionNotFoundError


class WizardIO(Protocol):
    is_tty: bool

    def prompt(self, msg: str) -> str: ...
    def print(self, msg: str) -> None: ...


class ConfigOps(Protocol):
    def load(self) -> dict: ...
    def save(self, cfg: dict) -> None: ...


CATEGORIES = ("decisions", "web_cache", "patterns", "gotchas")

DB_TITLES: dict[str, str] = {
    "decisions": "Brain · Decisions",
    "web_cache": "Brain · Web Cache",
    "patterns": "Brain · Patterns",
    "gotchas": "Brain · Gotchas",
}


# --- Schemas (one function per category so test assertions target the shape) ---


def _decisions_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Context": {"rich_text": {}},
        "Decision": {"rich_text": {}},
        "Rationale": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Date": {"date": {}},
        "Source Project Hash": {"rich_text": {}},
        "Generalizable": {"checkbox": {}},
        "Superseded By": {"url": {}},
    }


def _web_cache_schema() -> dict:
    return {
        "Name": {"title": {}},
        "URL": {"url": {}},
        "Query": {"rich_text": {}},
        "Content": {"rich_text": {}},
        "Fetched At": {"date": {}},
        "TTL Days": {"number": {"format": "number"}},
        "Domain": {"select": {}},
        "Tags": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Content Hash": {"rich_text": {}},
    }


def _patterns_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Description": {"rich_text": {}},
        "When to Use": {"rich_text": {}},
        "Example": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Date": {"date": {}},
        "Confidence": {
            "select": {
                "options": [
                    {"name": "experimental"},
                    {"name": "tested"},
                    {"name": "proven"},
                ]
            }
        },
    }


def _gotchas_schema() -> dict:
    return {
        "Name": {"title": {}},
        "Description": {"rich_text": {}},
        "Wrong Way": {"rich_text": {}},
        "Right Way": {"rich_text": {}},
        "Tags": {"multi_select": {}},
        "Stack": {"multi_select": {}},
        "Source Project Hash": {"rich_text": {}},
        "Date": {"date": {}},
        "Severity": {
            "select": {
                "options": [
                    {"name": "low"},
                    {"name": "medium"},
                    {"name": "high"},
                ]
            }
        },
        "Evidence URL": {"url": {}},
    }


_SCHEMAS: dict[str, Callable[[], dict]] = {
    "decisions": _decisions_schema,
    "web_cache": _web_cache_schema,
    "patterns": _patterns_schema,
    "gotchas": _gotchas_schema,
}


def db_schema(category: str) -> dict:
    """Return Notion property schema for a brain category.

    Raises ValueError for unknown category.
    """
    if category not in _SCHEMAS:
        raise ValueError(f"Unknown brain category: {category!r}")
    return _SCHEMAS[category]()


# --- Notion database creation ---


class PartialCreateError(NotionError):
    """Raised when create_brain_databases fails mid-batch.

    Carries the `created_ids` dict of categories that DID land in Notion before
    the failure so callers can emit accurate orphan-cleanup guidance instead of
    `<missing>` placeholders.
    """

    def __init__(self, message: str, created_ids: dict[str, str]):
        super().__init__(message)
        self.created_ids = created_ids


def create_brain_databases(client: Any, parent_page_id: str) -> dict[str, str]:
    """Create 4 brain databases under parent_page_id. Returns {category: db_id}.

    Raises `PartialCreateError` (subclass of NotionError) when any category
    fails after at least one succeeded — carries `created_ids` for cleanup.
    On the very first call failure (zero successes), re-raises the original
    NotionError unchanged.
    """
    if not parent_page_id:
        raise ValueError("parent_page_id is required")
    ids: dict[str, str] = {}
    for category in CATEGORIES:
        try:
            resp = client.databases_create(
                parent_page_id=parent_page_id,
                title=DB_TITLES[category],
                properties=db_schema(category),
            )
        except NotionError as e:
            if ids:
                raise PartialCreateError(
                    f"databases_create failed mid-batch on '{category}': {e}",
                    ids,
                ) from e
            raise
        ids[category] = resp.get("id") or ""
    return ids


# --- Discovery / verification (anti-hallucination guards) ---


def _extract_db_title(db: dict) -> str:
    """Extract plain-text title from a Notion database object.

    Notion returns `title` as a list of rich-text fragments. For canonical
    BRAIN databases we created with a single text fragment, fragments[0].plain_text
    is the title. Defensive: tolerate missing/empty/malformed shapes.
    """
    fragments = db.get("title") or []
    pieces: list[str] = []
    for f in fragments:
        if not isinstance(f, dict):
            continue
        pt = f.get("plain_text")
        if isinstance(pt, str):
            pieces.append(pt)
            continue
        text = f.get("text")
        if isinstance(text, dict):
            content = text.get("content")
            if isinstance(content, str):
                pieces.append(content)
    return "".join(pieces).strip()


def find_workspace_brain_databases(client: Any) -> dict[str, str]:
    """Search Notion workspace for existing canonical-titled BRAIN databases.

    Returns {category: db_id} for each canonical title found. Empty dict when
    nothing exists. Categories with multiple matches keep the FIRST id —
    callers that detect duplicates should warn and ask the user to point
    explicitly at the canonical four with --join-existing IDs.

    Reads only — does not mutate Notion.
    """
    found: dict[str, str] = {}
    title_to_category = {v: k for k, v in DB_TITLES.items()}

    cursor: str | None = None
    while True:
        page = client.search(
            query="Brain",
            filter={"property": "object", "value": "database"},
            start_cursor=cursor,
            page_size=100,
        )
        for db in page.get("results", []) or []:
            if db.get("object") != "database":
                continue
            if db.get("archived"):
                continue
            title = _extract_db_title(db)
            cat = title_to_category.get(title)
            if cat and cat not in found:
                db_id = db.get("id") or ""
                if db_id:
                    found[cat] = db_id
        if not page.get("has_more"):
            break
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return found


def verify_brain_databases(client: Any, db_ids: dict[str, str]) -> dict[str, str]:
    """Verify each db_id resolves to a queryable Notion database.

    Returns {category: error_message} for IDs that fail verification.
    Empty dict means all four IDs are valid. Used by --join-existing to
    catch typos before writing config.json.
    """
    errors: dict[str, str] = {}
    for category in CATEGORIES:
        db_id = (db_ids.get(category) or "").strip()
        if not db_id:
            errors[category] = "missing id"
            continue
        try:
            client.databases_query(db_id, page_size=1)
        except NotionNotFoundError as e:
            errors[category] = f"not found: {e}"
        except NotionError as e:
            errors[category] = f"verify failed: {e}"
    return errors


# --- Config merging ---


def merge_brain_config(existing_cfg: dict | None, updates: dict) -> dict:
    """Merge brain-related `updates` into `existing_cfg`. Pure; returns new dict.

    database_ids is deep-merged (empty values skipped). Other keys overwrite.
    """
    new_cfg = dict(existing_cfg or {})
    existing_brain = dict(new_cfg.get("brain") or {})
    new_brain = dict(existing_brain)
    for key, value in (updates or {}).items():
        if key == "database_ids" and isinstance(value, dict):
            merged = dict(existing_brain.get("database_ids") or {})
            merged.update({k: v for k, v in value.items() if v})
            new_brain["database_ids"] = merged
        elif value is not None:
            new_brain[key] = value
    new_cfg["brain"] = new_brain
    return new_cfg


# --- Wizard ---


class WizardError(Exception):
    """Wizard-level failure — missing required args, user abort, API error."""


class CliIO:
    """Default WizardIO impl: stdin/stdout with EOF / Ctrl+C → WizardError.

    `input()` raises EOFError when stdin is piped/closed and KeyboardInterrupt
    on Ctrl+C — both should surface as a clean wizard abort rather than a
    Python traceback.
    """

    def __init__(self) -> None:
        import sys

        self.is_tty = sys.stdin.isatty()

    def prompt(self, msg: str) -> str:
        try:
            return input(msg)
        except KeyboardInterrupt as e:
            raise WizardError("Aborted by user (Ctrl+C).") from e
        except EOFError as e:
            raise WizardError(
                "Aborted: no input available (stdin closed/piped)."
            ) from e

    def print(self, msg: str) -> None:
        print(msg)


def _print_orphan_cleanup_guidance(
    io: "WizardIO", db_ids: dict[str, str], exc: BaseException
) -> None:
    """After databases_create succeeded but a post-create step failed, emit
    manual-cleanup guidance so the user can archive the orphan databases.
    """
    io.print(
        f"\n⚠ Post-create step failed: {type(exc).__name__}: {exc}\n"
        "The 4 Notion databases below were already created — "
        "config was NOT written, so they are orphaned.\n"
        "Archive each one manually (open page in Notion → … → Archive) "
        "before re-running `brain init`:"
    )
    for category in CATEGORIES:
        db_id = db_ids.get(category) or "<missing>"
        title = DB_TITLES.get(category, category)
        io.print(f"  - {category}: {db_id}  ({title})")


def _has_existing_brain(cfg: dict) -> bool:
    brain = cfg.get("brain") or {}
    if not brain.get("enabled"):
        return False
    db_ids = brain.get("database_ids") or {}
    return any(db_ids.get(c) for c in CATEGORIES)


_JOIN_ID_KEYS = {
    "decisions": "decisions_id",
    "web_cache": "web_cache_id",
    "patterns": "patterns_id",
    "gotchas": "gotchas_id",
}


def _collect_explicit_join_ids(args: dict) -> dict[str, str]:
    """Pull --decisions-id / --web-cache-id / --patterns-id / --gotchas-id off args."""
    out: dict[str, str] = {}
    for category, key in _JOIN_ID_KEYS.items():
        val = (args.get(key) or "").strip()
        if val:
            out[category] = val
    return out


def run_wizard(
    args: dict,
    io: WizardIO,
    client_factory: Callable[[str], Any],
    config_ops: ConfigOps,
) -> dict:
    """Orchestrate the init wizard.

    Inputs:
      args = {"parent_page_id", "token_env", "project_name", "force", "yes",
              "interactive",                # None → use io.is_tty
              "join_existing",              # v1.3.3: skip create, reuse workspace DBs
              "force_create",               # v1.3.3: create even if duplicates detected
              "decisions_id", "web_cache_id", "patterns_id", "gotchas_id"}
      io.prompt(msg) -> str; io.print(msg); io.is_tty -> bool
      client_factory(token) -> Notion-like client with databases_create() + search() + databases_query()
      config_ops.load() -> dict; config_ops.save(cfg)

    Returns: dict with parent_page_id, token_env, project_name, database_ids,
             mode ("create" | "join").
    Raises WizardError on user abort, missing args, or Notion failure.

    v1.3.3 anti-hallucination: before creating, search the workspace for
    existing canonical-titled BRAIN databases. If found, refuse to create
    duplicates and point at --join-existing. Architectural rule: ONE set
    of 4 BRAIN DBs per workspace, shared by ALL projects (privacy comes
    from per-project Source Project Hash, not separate DBs).
    """
    existing = config_ops.load() or {}
    interactive = args.get("interactive")
    if interactive is None:
        interactive = bool(getattr(io, "is_tty", False))
    force = bool(args.get("force"))
    join_existing = bool(args.get("join_existing"))
    force_create = bool(args.get("force_create"))

    if _has_existing_brain(existing) and not force:
        raise WizardError(
            "Brain is already configured in .tausik/config.json. "
            "Re-run with --force to overwrite."
        )

    token_env = (args.get("token_env") or "").strip() or str(
        brain_config.DEFAULT_BRAIN["notion_integration_token_env"]
    )
    project_name = (args.get("project_name") or "").strip()
    parent_page_id = (args.get("parent_page_id") or "").strip()

    if interactive and not args.get("token_env"):
        supplied = io.prompt(f"Env var name for Notion token [{token_env}]: ").strip()
        if supplied:
            token_env = supplied

    token = os.environ.get(token_env, "")
    if not token:
        raise WizardError(
            f"Environment variable {token_env!r} is not set. "
            "Export your Notion integration token and re-run."
        )

    client = client_factory(token)

    # v1.3.3: pre-flight workspace search (skip for explicit --join-existing
    # with all 4 ids supplied, and for --force-create explicit override).
    explicit_join_ids = _collect_explicit_join_ids(args)
    have_all_explicit = all(c in explicit_join_ids for c in CATEGORIES)
    pre_flight_skipped = (join_existing and have_all_explicit) or force_create

    discovered: dict[str, str] = {}
    if not pre_flight_skipped:
        try:
            discovered = find_workspace_brain_databases(client)
        except NotionError as e:
            io.print(
                f"⚠ Workspace search failed ({type(e).__name__}: {e}); "
                "skipping duplicate-DB pre-flight check."
            )
            discovered = {}

    full_match = all(c in discovered for c in CATEGORIES)

    # Branch A: --join-existing requested → resolve IDs (explicit > discovered).
    if join_existing:
        merged_ids: dict[str, str] = {}
        for c in CATEGORIES:
            if c in explicit_join_ids:
                merged_ids[c] = explicit_join_ids[c]
            elif c in discovered:
                merged_ids[c] = discovered[c]
        missing = [c for c in CATEGORIES if c not in merged_ids]
        if missing:
            raise WizardError(
                "--join-existing could not resolve all 4 database IDs. "
                f"Missing: {', '.join(missing)}. "
                "Either share existing canonical-titled BRAIN databases with "
                "the integration so search() finds them, or pass them "
                "explicitly with --decisions-id / --web-cache-id / "
                "--patterns-id / --gotchas-id."
            )
        verify_errors = verify_brain_databases(client, merged_ids)
        if verify_errors:
            details = "; ".join(f"{c}: {msg}" for c, msg in verify_errors.items())
            raise WizardError(
                f"--join-existing verification failed for some IDs: {details}. "
                "Fix the IDs (or share the databases with your integration) "
                "and re-run."
            )
        return _finalize_join(
            io, config_ops, existing, merged_ids, token_env, project_name, interactive
        )

    # Branch B: full match discovered + no --force-create → refuse.
    if full_match and not force_create:
        ids_listing = "\n".join(
            f"  - {c}: {discovered[c]} ({DB_TITLES[c]})" for c in CATEGORIES
        )
        raise WizardError(
            "Found existing BRAIN databases in this Notion workspace.\n"
            f"{ids_listing}\n\n"
            "TAUSIK Shared Brain uses ONE set of 4 BRAIN databases per "
            "workspace, shared by ALL projects (per-project privacy is "
            "enforced via the 'Source Project Hash' column, NOT by creating "
            "separate databases).\n\n"
            "Re-run with --join-existing to wire this project to the "
            "existing databases. If you really need a brand-new workspace "
            "(rare — usually a different Notion account/integration), use "
            "--force-create."
        )

    # Branch C: partial match (1-3 of 4 found) → refuse, ambiguous state.
    if discovered and not full_match:
        ids_listing = "\n".join(
            f"  - {c}: {discovered.get(c, '<missing>')}" for c in CATEGORIES
        )
        raise WizardError(
            "Found a partial set of canonical-titled BRAIN databases in "
            "this workspace (some categories present, some missing):\n"
            f"{ids_listing}\n\n"
            "Refusing to create duplicates. Either share/restore the "
            "missing databases and re-run with --join-existing, or pass "
            "all 4 IDs explicitly with "
            "--join-existing --decisions-id ... --web-cache-id ... "
            "--patterns-id ... --gotchas-id ..."
        )

    # Branch D: --force-create OR clean workspace → create 4 new DBs.
    if not parent_page_id:
        if not interactive:
            raise WizardError("--parent-page-id is required in non-interactive mode")
        parent_page_id = io.prompt("Notion parent page ID: ").strip()
        if not parent_page_id:
            raise WizardError("parent_page_id cannot be empty")

    if not project_name:
        default_name = os.path.basename(os.getcwd()) or "project"
        if interactive:
            entered = io.prompt(f"Project name [{default_name}]: ").strip()
            project_name = entered or default_name
        else:
            project_name = default_name

    if interactive and not args.get("yes"):
        if force_create and discovered:
            io.print(
                "\n⚠ --force-create: existing canonical BRAIN databases were "
                "detected in this workspace, but you asked to create new ones "
                "anyway. This will produce TWO independent brains in the same "
                "workspace — projects pointed at one will not see records "
                "from the other."
            )
        io.print(
            "\nAbout to create 4 Notion databases under the parent page and "
            "write .tausik/config.json. The token itself is NOT saved — only "
            "the env var name."
        )
        confirm = io.prompt("Proceed? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            raise WizardError("Aborted by user.")

    io.print(f"Creating 4 Notion databases under page {parent_page_id}…")
    try:
        db_ids = create_brain_databases(client, parent_page_id)
    except PartialCreateError as e:
        # Surface real created_ids so user can archive partial orphans
        _print_orphan_cleanup_guidance(io, e.created_ids, e)
        raise WizardError(
            f"Notion databases_create partially failed: {e}. "
            "See orphan cleanup guidance above."
        ) from e
    except NotionError as e:
        raise WizardError(f"Notion databases_create failed: {e}") from e

    try:
        registry_entry = brain_project_registry.register_project(
            project_name, os.getcwd()
        )
        resolved_name = registry_entry["name"]
        if resolved_name != project_name:
            io.print(
                f"Project name {project_name!r} collides in the brain registry; "
                f"using {resolved_name!r} instead."
            )

        existing_names = list((existing.get("brain") or {}).get("project_names") or [])
        union_names = list(existing_names)
        for n in brain_project_registry.all_project_names():
            if n not in union_names:
                union_names.append(n)

        updates = {
            "enabled": True,
            "notion_integration_token_env": token_env,
            "database_ids": db_ids,
            "project_names": union_names,
        }
        new_cfg = merge_brain_config(existing, updates)
        config_ops.save(new_cfg)
    except Exception as e:
        _print_orphan_cleanup_guidance(io, db_ids, e)
        raise WizardError(
            f"Post-create step failed ({type(e).__name__}): {e}. "
            f"The 4 Notion databases were created but config was NOT saved — "
            f"see the cleanup guidance above to archive them manually."
        ) from e

    io.print(
        "Brain configured. Next: run `.tausik/tausik brain sync` to pull existing data."
    )
    return {
        "parent_page_id": parent_page_id,
        "token_env": token_env,
        "project_name": resolved_name,
        "database_ids": db_ids,
        "mode": "create",
    }


def _finalize_join(
    io: WizardIO,
    config_ops: ConfigOps,
    existing: dict,
    db_ids: dict[str, str],
    token_env: str,
    project_name: str,
    interactive: bool,
) -> dict:
    """Write config for --join-existing flow (no databases_create call).

    Mirrors the post-create config-save block, but skips orphan-cleanup
    guidance (no DBs were created here, so nothing to orphan).
    """
    if not project_name:
        default_name = os.path.basename(os.getcwd()) or "project"
        if interactive:
            entered = io.prompt(f"Project name [{default_name}]: ").strip()
            project_name = entered or default_name
        else:
            project_name = default_name

    registry_entry = brain_project_registry.register_project(project_name, os.getcwd())
    resolved_name = registry_entry["name"]
    if resolved_name != project_name:
        io.print(
            f"Project name {project_name!r} collides in the brain registry; "
            f"using {resolved_name!r} instead."
        )

    existing_names = list((existing.get("brain") or {}).get("project_names") or [])
    union_names = list(existing_names)
    for n in brain_project_registry.all_project_names():
        if n not in union_names:
            union_names.append(n)

    updates = {
        "enabled": True,
        "notion_integration_token_env": token_env,
        "database_ids": db_ids,
        "project_names": union_names,
    }
    new_cfg = merge_brain_config(existing, updates)
    config_ops.save(new_cfg)

    io.print(
        "\nJoined existing BRAIN databases. This project now shares knowledge "
        "with every other project pointed at the same 4 databases. Per-project "
        "privacy is enforced via Source Project Hash on each row.\n"
        "Next: run `.tausik/tausik brain sync` to pull existing data."
    )
    return {
        "parent_page_id": "",
        "token_env": token_env,
        "project_name": resolved_name,
        "database_ids": db_ids,
        "mode": "join",
    }
