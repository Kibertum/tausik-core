**English** | [Русский](../ru/package-layout-2.0.md)

# TAUSIK 2.0 Package Layout

<!-- doc-map: reader=maintainer; zone=internal-spec -->

## Why this change exists

TAUSIK 1.11 ships 563 files under `scripts/`. Of those, 502 are at the root.
The backend alone uses 71 root modules. The migration chain has 34
`backend_migrations_v*.py` modules and 2,541 lines for schema versions through
v67.

This layout is a deployment contract, not a designed package boundary.
Bootstrap copies `scripts/` into each host profile, and several entry points add
that flat directory to `sys.path`. Moving files in 1.11 would therefore break
bootstrap, hooks, MCP imports, tests, and installed projects at the same time.

## Target tree

```text
src/tausik/
├── cli/                 # argparse definitions and terminal rendering
├── application/         # ProjectService use cases and quality gates
│   ├── tasks/
│   ├── knowledge/
│   ├── verification/
│   └── skills/
├── domain/              # types and rules without SQLite, CLI, or host imports
├── infrastructure/
│   ├── db/              # SQLite repositories and the current schema
│   │   └── migrations/  # 2.0 baseline and supported upgrade bridges
│   ├── providers/       # Codex, Kilo, and future usage adapters
│   └── supply_chain/    # signatures, receipts, publication boundaries
├── gates/               # gate registry, runners, and affected-test selection
├── hosts/               # thin host adapters; canonical behavior stays above
└── bootstrap/           # installation and profile generation
```

Dependency direction is one way:

```text
CLI / MCP / hooks -> application -> domain
                         |
                         v
                  infrastructure
```

The domain never imports CLI, MCP, bootstrap, a host adapter, or SQLite. CLI
and MCP remain thin wrappers over the same application service.

## Migration baseline

Do not squash the 1.11 chain in place. Existing databases may still need it.

1. Keep schema v67 and its historical chain intact for the 1.11.x support line.
2. Before 2.0 code moves, declare the minimum source version that 2.0 upgrades.
   The recommended boundary is every released 1.11.x schema, not every schema
   ever created.
3. Build fresh 2.0 databases from one canonical schema baseline. A fresh
   database must not replay historical migrations.
4. Add one tested bridge from each supported 1.11.x schema to the 2.0 baseline.
5. Remove v2-v67 modules from the normal 2.0 import path only after the support
   boundary is published and upgrade fixtures prove data, indexes, FTS tables,
   receipts, tasks, memory, and decisions survive.

If a pre-1.11 database must remain supported, keep the old chain in an explicit
compatibility command or package. Do not import it during an ordinary 2.0 start.

## Rollout

1. Freeze and publish the 1.11 schema/support policy.
2. Add `src/tausik` packaging and import-boundary checks.
3. Move one vertical slice at a time: backend, application services, gates,
   CLI, then hosts and bootstrap.
4. Keep temporary top-level entry points that import the package; delete each
   shim when all shipped consumers use the package path.
5. Switch profile generation from copying loose modules to installing/copying
   one package tree.
6. Remove flat-path `sys.path` injection and the compatibility shims.

At every step, source tests and generated host profiles must import the same
implementation. A copied second implementation is not a compatibility layer.

## Release boundary

TAUSIK 1.11 receives token-economy fixes and documentation. It does not move
runtime modules or delete upgrade history. The package move and migration
baseline are 2.0 work because they deliberately change import and support
contracts.
