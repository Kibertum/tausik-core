"""CLI dispatcher for `tausik config {set,show}` (skill profile overrides)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def cmd_config(svc: Any, args: Any) -> None:
    """Dispatch `tausik config set <key> <value>` and `tausik config show`."""
    sub = getattr(args, "config_cmd", None)
    if sub == "set":
        _cmd_config_set(args)
    elif sub == "show":
        _cmd_config_show()
    else:
        print("Usage: tausik config [set <key> <value> | show]")


def cmd_skill_rebuild(args: Any, project_dir: str, skills_dst: str) -> None:
    """Rebuild merged SKILL.md files using current ide+model from session/config/env.

    Lives here (not in project_cli_extra.py) so the latter stays under the
    400-line filesize gate. Wired from the `tausik skill rebuild` dispatcher
    in project_cli_extra.cmd_skill.
    """
    _SCRIPTS = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS not in sys.path:
        sys.path.insert(0, _SCRIPTS)
    from skill_profile_rebuild import rebuild_skills
    from skill_profile_session import (
        load_session_state,
        now_iso,
        resolve_profile,
        save_session_state,
    )

    cfg_path = _config_path(project_dir)
    cfg = _read_config(cfg_path)

    ide, model, source = resolve_profile(cfg)
    result = rebuild_skills(skills_dst, ide=ide, model=model, force=bool(args.force))

    tausik_dir = os.path.join(project_dir, ".tausik")
    state = load_session_state(tausik_dir)
    state.update({"ide": ide, "model": model, "source": source, "last_rebuild_at": now_iso()})
    save_session_state(tausik_dir, state)

    print(
        f"Rebuild: ide={ide or '-'} model={model or '-'} source={source} "
        f"rebuilt={len(result['rebuilt'])} skipped={len(result['skipped'])} "
        f"errors={len(result['errors'])}"
    )
    if result["rebuilt"]:
        print("  Rebuilt: " + ", ".join(result["rebuilt"]))
    errors = result["errors"]
    if isinstance(errors, dict) and errors:
        for slug, reason in errors.items():
            print(f"  ERROR {slug}: {reason}")


def _project_dir() -> str:
    return os.getcwd()


def _config_path(project_dir: str) -> str:
    from tausik_utils import tausik_config_path

    return tausik_config_path(project_dir)


def _read_config(path: str) -> dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARN: malformed config.json: {e} — treating as empty", file=sys.stderr)
        return {}


def _write_config(path: str, cfg: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _cmd_config_set(args: Any) -> None:
    """Persist `key = value` into .tausik/config.json."""
    _SCRIPTS = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS not in sys.path:
        sys.path.insert(0, _SCRIPTS)
    from skill_profile_detect import (
        VALID_IDES,
        VALID_MODELS,
        normalize_model_profile_slug,
    )

    key = args.key
    raw = args.value
    slug = normalize_model_profile_slug(raw)
    if not slug:
        print(f"ERROR: empty/invalid value '{raw}'")
        sys.exit(2)
    if key == "ide_profile" and slug not in VALID_IDES:
        print(f"ERROR: '{slug}' is not a known ide. Valid: {', '.join(sorted(VALID_IDES))}")
        sys.exit(2)
    if key == "model_profile" and slug not in VALID_MODELS:
        print(f"ERROR: '{slug}' is not a known model. Valid: {', '.join(sorted(VALID_MODELS))}")
        sys.exit(2)

    path = _config_path(_project_dir())
    cfg = _read_config(path)
    cfg[key] = slug
    _write_config(path, cfg)
    print(f"Saved {key} = {slug} to {path}")


def _cmd_config_show() -> None:
    """Print resolved (ide, model, source)."""
    _SCRIPTS = os.path.dirname(os.path.abspath(__file__))
    if _SCRIPTS not in sys.path:
        sys.path.insert(0, _SCRIPTS)
    from skill_profile_session import resolve_profile

    cfg = _read_config(_config_path(_project_dir()))
    ide, model, source = resolve_profile(cfg)
    print(f"ide:    {ide or '(none)'}")
    print(f"model:  {model or '(none)'}")
    print(f"source: {source}")
