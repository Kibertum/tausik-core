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
from brain_notion_client import NotionError


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


def create_brain_databases(client: Any, parent_page_id: str) -> dict[str, str]:
    """Create 4 brain databases under parent_page_id. Returns {category: db_id}.

    Raises brain_notion_client.NotionError on any API failure.
    """
    if not parent_page_id:
        raise ValueError("parent_page_id is required")
    ids: dict[str, str] = {}
    for category in CATEGORIES:
        resp = client.databases_create(
            parent_page_id=parent_page_id,
            title=DB_TITLES[category],
            properties=db_schema(category),
        )
        ids[category] = resp.get("id") or ""
    return ids


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


def _has_existing_brain(cfg: dict) -> bool:
    brain = cfg.get("brain") or {}
    if not brain.get("enabled"):
        return False
    db_ids = brain.get("database_ids") or {}
    return any(db_ids.get(c) for c in CATEGORIES)


def run_wizard(
    args: dict,
    io: WizardIO,
    client_factory: Callable[[str], Any],
    config_ops: ConfigOps,
) -> dict:
    """Orchestrate the init wizard.

    Inputs:
      args = {"parent_page_id", "token_env", "project_name", "force", "yes",
              "interactive"}  # interactive=None → use io.is_tty
      io.prompt(msg) -> str; io.print(msg); io.is_tty -> bool
      client_factory(token) -> Notion-like client with databases_create()
      config_ops.load() -> dict; config_ops.save(cfg)

    Returns: dict with parent_page_id, token_env, project_name, database_ids.
    Raises WizardError on user abort, missing args, or Notion failure.
    """
    existing = config_ops.load() or {}
    interactive = args.get("interactive")
    if interactive is None:
        interactive = bool(getattr(io, "is_tty", False))
    force = bool(args.get("force"))

    if _has_existing_brain(existing) and not force:
        raise WizardError(
            "Brain is already configured in .tausik/config.json. "
            "Re-run with --force to overwrite."
        )

    parent_page_id = (args.get("parent_page_id") or "").strip()
    token_env = (args.get("token_env") or "").strip() or str(
        brain_config.DEFAULT_BRAIN["notion_integration_token_env"]
    )
    project_name = (args.get("project_name") or "").strip()

    if not parent_page_id:
        if not interactive:
            raise WizardError("--parent-page-id is required in non-interactive mode")
        parent_page_id = io.prompt("Notion parent page ID: ").strip()
        if not parent_page_id:
            raise WizardError("parent_page_id cannot be empty")

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

    if not project_name:
        default_name = os.path.basename(os.getcwd()) or "project"
        if interactive:
            entered = io.prompt(f"Project name [{default_name}]: ").strip()
            project_name = entered or default_name
        else:
            project_name = default_name

    if interactive and not args.get("yes"):
        io.print(
            "\nAbout to create 4 Notion databases under the parent page and "
            "write .tausik/config.json. The token itself is NOT saved — only "
            "the env var name."
        )
        confirm = io.prompt("Proceed? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            raise WizardError("Aborted by user.")

    io.print(f"Creating 4 Notion databases under page {parent_page_id}…")
    client = client_factory(token)
    try:
        db_ids = create_brain_databases(client, parent_page_id)
    except NotionError as e:
        raise WizardError(f"Notion databases_create failed: {e}") from e

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
        "Brain configured. Next: run `.tausik/tausik brain sync` to pull existing data."
    )
    return {
        "parent_page_id": parent_page_id,
        "token_env": token_env,
        "project_name": resolved_name,
        "database_ids": db_ids,
    }
