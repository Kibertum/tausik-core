#!/usr/bin/env python3
"""TAUSIK CLI entry point -- parse args, dispatch to handlers."""

from __future__ import annotations

import os
import sys

# Add scripts dir to path for imports
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)


def main() -> None:
    from tausik_utils import fix_stdio_encoding

    fix_stdio_encoding()

    from project_cli import (
        cmd_decide,
        cmd_decisions,
        cmd_epic,
        cmd_init,
        cmd_roadmap,
        cmd_session,
        cmd_status,
        cmd_story,
        cmd_task,
        cmd_team,
    )
    from project_cli_extra import (
        cmd_fts,
        cmd_gates,
        cmd_memory,
        cmd_skill,
        cmd_update_claudemd,
    )
    from project_cli_ops import (
        cmd_audit,
        cmd_dead_end,
        cmd_events,
        cmd_explore,
        cmd_hud,
        cmd_metrics,
        cmd_run,
        cmd_search,
        cmd_suggest_model,
    )
    from project_config import get_service
    from project_parser import build_parser
    from tausik_utils import ServiceError

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "init": cmd_init,
        "status": cmd_status,
        "epic": cmd_epic,
        "story": cmd_story,
        "task": cmd_task,
        "session": cmd_session,
        "decide": cmd_decide,
        "decisions": cmd_decisions,
        "memory": cmd_memory,
        "gates": cmd_gates,
        "roadmap": cmd_roadmap,
        "search": cmd_search,
        "metrics": cmd_metrics,
        "hud": cmd_hud,
        "suggest-model": cmd_suggest_model,
        "team": cmd_team,
        "update-claudemd": cmd_update_claudemd,
        "events": cmd_events,
        "fts": cmd_fts,
        "skill": cmd_skill,
        "dead-end": cmd_dead_end,
        "explore": cmd_explore,
        "audit": cmd_audit,
        "run": cmd_run,
    }

    fn = dispatch.get(args.command)
    if not fn:
        # Suggest similar commands
        from difflib import get_close_matches

        matches = get_close_matches(args.command, dispatch.keys(), n=3, cutoff=0.5)
        if matches:
            print(
                f"Unknown command '{args.command}'. Did you mean: {', '.join(matches)}?",
                file=sys.stderr,
            )
        else:
            print(
                f"Unknown command '{args.command}'. Available: {', '.join(sorted(dispatch.keys()))}",
                file=sys.stderr,
            )
        sys.exit(1)

    svc = get_service()
    try:
        fn(svc, args)
    except ServiceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    finally:
        svc.be.close()


if __name__ == "__main__":
    main()
