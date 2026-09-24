**English** | [Русский](../ru/renar-11-deltas.md)

# RENAR 1.1: what TAUSIK did with each change

RENAR 1.1 (19 September 2026) lists its changes in one table, `guide/12-migration-v11.md` of the standard. A minor release triggers re-assessment of a conformance claim at once (§13.7.3). A change nobody mentions reads the same as one that was adopted, so every row below has exactly one status.

| Status | Meaning |
|--------|---------|
| `implemented` | A mechanism in this repository does it. The registry names it as `module:function`, and a test imports it. |
| `inapplicable` | The obligation has no subject here. The premise is read from the schema, and a test breaks the day a carrier appears. |
| `deferred` | Owed and not done. The release and the decision that moved it are named. |
| `no-action` | The guide itself says the row needs none. |

The registry is `scripts/renar_v11_deltas.py`. `tests/test_renar_v11_deltas.py` reads the row count from the standard's guide, so the table cannot fall behind it. `RENAR-CONFORMANCE.yaml` publishes the inapplicable and deferred rows in its `renar-11-deltas` block.

| Row | Change | Status | Why |
|-----|--------|--------|-----|
| 1 | Description set; BR/SR/SPEC/TC without status and version; `set-version N.M` | `deferred` | A schema rewrite; moved to 2.0 by decision #382 |
| 2 | QG-0/1/2 objects: set version, TC implementation, version on product | `deferred` | Depends on row 1; 2.0, decision #382 |
| 3 | §13.3.5 TC pair coverage at QG-0 of the set | `implemented` | The `tc-pos-neg-pairing` clause, per artifact until the set lands |
| 4 | Manifest `set-version` and `confirmation` | `deferred` | `set-version` in 2.0 (#382); first-party confirmation in 1.11 (#377) |
| 5 | SPEC-UC, the twelfth SPEC type | `implemented` | Schema v64 and the body check in `spec_uc` |
| 6 | MW, the manual walkthrough record | `inapplicable` | Every test case is automated and no manual pass is run |
| 7 | First-party confirmation §1.4.4 | `deferred` | 1.11, decision #377 |
| 8 | Reusable component with `uses[]` | `inapplicable` | TAUSIK is described as one system; no class holds a `uses[]` edge |
| 9 | `implements[]`, mandatory clause §13.3.8 | `implemented` | The `implements-edge-subsystem` clause |
| 10 | Screen registry and `screens[]` in SPEC-UI | `inapplicable` | The product has no screens (CLI, MCP, hooks); no SPEC-UI exists |
| 11 | Coverage completeness of the mandatory SPEC body | `deferred` | 2.0, decision #382 |
| 12 | SPEC-ARCH and SPEC-SEC mandatory at system level | `deferred` | Both exist; nothing enforces them yet. 2.0, decision #382 |
| 13 | Controlled form of an SR statement | `deferred` | A recommendation, not adopted |
| 14 | Description language, chapter 15 | `inapplicable` | Mandatory from RENAR-2; the manifest level is null (§1.5.4) |
| 15 | `automation.status`: automated or manual-pending | `deferred` | 2.0, decision #382 |
| 16 | AR records the primary agent's model; canonical ai-provenance | `inapplicable` | No class has the AR shape, so there is no AR to carry `primary.*`; ai-provenance is mandatory from RENAR-4 |
| 17 | Metric threshold calibration by data sufficiency | `deferred` | 2.0, decision #382 |
| 18 | Non-degeneracy measurer for a new mandatory control §13.9.4 | `implemented` | The measurer-caveats registry |
| 21 | Statement address `<id>#n` in TC and step references | `deferred` | Depends on the TC schema of row 1; 2.0, decision #382 |
| 20 | Norm and process | `no-action` | The guide says this row requires no action |

Decision #382 was taken by the agent inside the 1.10 charter and awaits the owner's confirmation. The 2.0 work is the task `renar-11-description-set-model`.
