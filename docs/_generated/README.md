# Generated documentation artifacts

Files here are produced by repository tooling so docs and CI can compare against live code.

| File | Generator |
|------|-----------|
| `constants.json` | `python scripts/gen_doc_constants.py` or `tausik doc constants` |

After changing `pyproject.toml` version or MCP `TOOLS` definitions, regenerate and commit, or CI will fail `gen_doc_constants.py --check`.
