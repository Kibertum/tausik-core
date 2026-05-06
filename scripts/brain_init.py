"""Brain init wizard — creates 4 Notion databases and writes .tausik/config.json.

Public API (pure + injectable):
  db_schema(category) -> dict          -- Notion property schema per category
  create_brain_databases(client, ppid) -- call databases_create ×4
  merge_brain_config(existing, updates)-- pure dict merger
  run_wizard(args, io, client_factory, config_ops) -> dict

All side-effectful inputs are injected: the CLI layer wires real impls,
tests inject fakes. Token is NEVER persisted — only env var name.

Schemas + DB ops live in brain_init_schemas.py. The two run_wizard branches
live in brain_init_join.py (--join-existing) and brain_init_create.py
(--force-create / clean workspace). brain_init.py keeps the dispatcher,
shared types, and the CLI-IO classes — extracted in v14b polish Phase B
(`v14b-followup-brain-init-filesize-debt`) to land under the 400-line
filesize gate.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Protocol

import brain_config
import brain_project_registry  # noqa: F401  re-export so tests can monkeypatch via brain_init.brain_project_registry
from brain_notion_client import NotionAuthError, NotionError

# Re-export schemas + DB ops so callers (tests, brain_cli_ops) can keep
# importing from brain_init.* unchanged.
from brain_init_schemas import (  # noqa: F401
    CATEGORIES,
    DB_TITLES,
    PartialCreateError,
    _decisions_schema,
    _gotchas_schema,
    _patterns_schema,
    _SCHEMAS,
    _web_cache_schema,
    create_brain_databases,
    db_schema,
    verify_brain_databases,
)

# Discovery (title-match + schema-fallback) lives in brain_discovery.py;
# re-exported here so callers and existing tests keep their imports.
from brain_discovery import (  # noqa: F401
    _extract_db_title,
    find_workspace_brain_databases,
    inspect_workspace_brain_databases,
)


class WizardIO(Protocol):
    is_tty: bool

    def prompt(self, msg: str) -> str: ...
    def print(self, msg: str) -> None: ...


class ConfigOps(Protocol):
    def load(self) -> dict: ...
    def save(self, cfg: dict) -> None: ...


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
            raise WizardError("Aborted: no input available (stdin closed/piped).") from e

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
            "Brain is already configured in .tausik/config.json. Re-run with --force to overwrite."
        )

    if interactive:
        io.print(
            "\n=== TAUSIK Shared Brain — onboarding wizard ===\n"
            "Cross-project knowledge in Notion (decisions, patterns, gotchas, web cache).\n"
            "\n"
            "Before continuing, make sure you have:\n"
            "  [1] A Notion workspace where you can create pages.\n"
            "  [2] An internal Notion integration with 'Insert content' + 'Read content'\n"
            "      capabilities. Create at https://www.notion.so/my-integrations\n"
            "  [3] The integration's secret token exported as an env var\n"
            "      (default name: NOTION_TOKEN; you can choose another).\n"
            "  [4] A parent page in Notion that you have shared with the integration\n"
            "      (open the page, '...' → 'Connections' → add your integration).\n"
            "      Copy its 32-character page ID from the URL.\n"
            "\n"
            "If something is missing, abort with Ctrl+C and re-run\n"
            "`.tausik/tausik brain init` once you're ready.\n"
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
            f"Environment variable {token_env!r} is not set.\n"
            "  How to fix:\n"
            "    1. Create an integration: https://www.notion.so/my-integrations\n"
            "    2. Copy the 'Internal Integration Token' (starts with `secret_` or `ntn_`).\n"
            f"    3. Export it: setx {token_env} <token>  (Windows / new terminal)\n"
            f"                  export {token_env}=<token>  (macOS/Linux)\n"
            "    4. Re-run `.tausik/tausik brain init` in a fresh shell that sees the var."
        )

    client = client_factory(token)

    # v1.4 pre-flight: probe users.me() to distinguish "token invalid" from
    # "integration not shared with BRAIN page" (dead-end #72). On 401 the
    # users.me() call raises NotionAuthError before any opaque search()
    # failure further down. Other transport/Notion errors surface as-is.
    explicit_join_ids = _collect_explicit_join_ids(args)
    have_all_explicit = all(c in explicit_join_ids for c in CATEGORIES)
    try:
        client.users_me()
    except NotionAuthError as e:
        raise WizardError(
            f"Notion token is invalid (401). Env var {token_env!r} is set but "
            f"the API rejected it. Probable causes:\n"
            "  - Token is expired or was revoked.\n"
            "  - Token is from a different workspace.\n"
            "  - Token was copied with leading/trailing whitespace.\n"
            "Fix:\n"
            "  1. Open https://www.notion.so/my-integrations and locate "
            "the integration.\n"
            "  2. Copy the 'Internal Integration Token' fresh (starts with "
            "`secret_` or `ntn_`).\n"
            f"  3. setx {token_env} <token>  (Windows / new terminal)\n"
            f"     export {token_env}=<token>  (macOS/Linux)\n"
            "  4. Re-run `.tausik/tausik brain init` in a fresh shell.\n"
            f"Underlying error: {e}"
        ) from e
    except NotionError as e:
        # Network / 5xx — keep going, the search() call below will produce
        # a more contextual error if it persists.
        io.print(
            f"⚠ Pre-flight users.me() failed ({type(e).__name__}: {e}); "
            "continuing — token may be valid but transport flaky."
        )

    # v1.3.3: pre-flight workspace search (skip for explicit --join-existing
    # with all 4 ids supplied, and for --force-create explicit override).
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
        from brain_init_join import run_join_branch

        return run_join_branch(
            io,
            config_ops,
            existing,
            client,
            explicit_join_ids,
            discovered,
            pre_flight_skipped,
            token_env,
            project_name,
            interactive,
        )

    # Branch B: full match discovered + no --force-create → refuse.
    if full_match and not force_create:
        ids_listing = "\n".join(f"  - {c}: {discovered[c]} ({DB_TITLES[c]})" for c in CATEGORIES)
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
        ids_listing = "\n".join(f"  - {c}: {discovered.get(c, '<missing>')}" for c in CATEGORIES)
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
    from brain_init_create import run_create_branch

    return run_create_branch(
        io,
        config_ops,
        existing,
        client,
        args,
        parent_page_id,
        project_name,
        discovered,
        force_create,
        interactive,
        token_env,
    )


# Re-export _finalize_join from brain_init_join for any external caller that
# still imports it from brain_init (no in-tree caller does today, but keep
# the contract stable across the split).
from brain_init_join import _finalize_join  # noqa: F401, E402
