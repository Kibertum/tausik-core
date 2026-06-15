"""CLI handler for `tausik key` — project ed25519 key management."""

from __future__ import annotations

import os
import sys


def cmd_key(svc, args) -> None:
    import crypto_keys

    project_dir = os.getcwd()
    cmd = getattr(args, "key_cmd", None)
    if cmd == "init":
        try:
            info = crypto_keys.init_keys(project_dir, force=args.force)
        except crypto_keys.KeyError_ as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(
            f"Project key generated ({info['algorithm']}).\n"
            f"  public:      {info['public']}\n"
            f"  fingerprint: {info['fingerprint']}\n"
            f"  private:     {info['key_path']} (gitignored via .tausik/, keep it local)"
        )
    elif cmd == "show":
        try:
            info = crypto_keys.key_info(project_dir)
        except crypto_keys.KeyError_ as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(
            f"algorithm:   {info['algorithm']}\n"
            f"public:      {info['public']}\n"
            f"fingerprint: {info['fingerprint']}"
        )
    else:
        print("Usage: tausik key {init,show}", file=sys.stderr)
        sys.exit(2)
