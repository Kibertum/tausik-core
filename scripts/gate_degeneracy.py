"""Degeneracy measure for OUR OWN blocking gates — what proves a gate can still go red.

BORROWED FROM ADR-021, NOT OWED TO IT. This is stated first and plainly so the
next shift does not mistake a voluntary practice for a binding obligation. The
verdict on ADR-021 (task `four-accepted-adrs-were-never-assessed`, session #191)
was **not applicable as a conformance norm**: its own line 27 puts the norm in
§13.9.4 — the procedure for amending the STANDARD — and §3.1 explicitly rejects
the form "for every mandatory control". We are not amending the standard, so we
owe it nothing, and reporting "we conform to ADR-021" would be false. What we do
here is TAKE THE IDEA because the practical debt is real.

THE DEBT IS MEASURED, NOT SUPPOSED. Three cases of one class inside a single
shift (#191):

  1. `bootstrap_drift` — severity `block`, and it stood `[OFF]`. A control
     declared blocking that does not execute at all.
  2. `claudemd_state_drift` — introduced in this very release as `block` and
     `[ON]`, with nothing named that would tell us it had degenerated into a
     tautology that answers "yes" to everything.
  3. The `commit`-trigger gates — executed by exactly one consumer, the git
     hook, while `core.hooksPath` on this tree pointed at a repository that does
     not exist (memory #439). Not degenerate: dead, and silently so.

Three of a kind in one shift is the signature of a missing practice, not a
coincidence.

THE RULE. Every blocking gate that is IN FORCE must name a test that hands it a
VIOLATION and requires red. Not "is covered by tests" — a gate's happy path is
usually well covered, and a gate that has forgotten how to fail passes all of
it. The proof is a specific test node, recorded in the committed
`tausik/gates.json` under `red_proofs`, and this module is what checks the
registry has not quietly drifted away from the gates it describes.

THE MEASURE MUST BE ABLE TO SAY NO. A check that answers "yes, every gate has a
measure" on every input would be the very defect it was opened against, so it
refuses on four independent grounds, and each names the gate:

  * DISABLED — a UNIVERSAL blocking gate that is switched off. Reported FIRST
    and separately, because it is WORSE than degeneracy: a degenerate gate at
    least executes, so it appears in the run, occupies a line in the receipt and
    can be caught the moment somebody reads what it actually asserted. A gate
    that is off produces no line at all. Nothing distinguishes it from a gate
    that ran and found nothing — which is precisely the reading its `[OFF]` row
    invites. A stack-scoped gate that is off because the project does not use
    that stack is NOT this case: that is scoping, not silence, and it is
    reported as dormant.
  * NO PROOF — an in-force blocking gate with no `red_proofs` entry.
  * UNRESOLVABLE PROOF — an entry whose test node is not in the tree. This is
    the teeth. Without it the registry would be a list of strings anybody could
    satisfy by typing one, and the audit of session #196 already counted the
    cost of trusting such strings: 19 rotted and 25 NEVER-EXISTENT test
    citations across 1258 closed tasks (memory #463).
  * STALE ENTRY — a `red_proofs` key naming a gate the registry no longer has,
    so a rename leaves evidence behind rather than silently orphaning it.

WHY AST RESOLUTION AND NOT PYTEST COLLECTION. Asking pytest to collect each node
would be the more thorough answer and the wrong tool here: it costs a
subprocess per entry, it fails for reasons unrelated to the citation (a missing
plugin, an import error elsewhere), and a check that goes red for ambient
breakage teaches people to ignore it. Parsing the test file's AST answers the
question actually being asked — does this name exist in the tree — cheaply and
for the same reason every time.
"""

from __future__ import annotations

import ast
import io
import json
import os
from dataclasses import dataclass, field

# A gate config carrying `stacks` is scoped to technologies the project may or
# may not use; one without it applies to every project, always.
_STACK_KEY = "stacks"

RED_PROOFS_SECTION = "red_proofs"


@dataclass(frozen=True)
class Debt:
    """One blocking gate whose ability to go red is not established."""

    gate: str
    kind: str  # DISABLED | NO_PROOF | UNRESOLVABLE_PROOF | STALE_ENTRY
    detail: str

    def describe(self) -> str:
        return f"{self.kind} {self.gate}: {self.detail}"


@dataclass
class Audit:
    """What the measure found. `debts` is ordered: DISABLED first (AC2)."""

    debts: list[Debt] = field(default_factory=list)
    proven: list[str] = field(default_factory=list)
    dormant: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.debts

    def report(self) -> str:
        if self.ok:
            return (
                f"{len(self.proven)} blocking gate(s) in force, each with a resolving "
                f"red-proof; {len(self.dormant)} dormant (stack not in use)"
            )
        return "\n".join(d.describe() for d in self.debts)


# --- The registry the gates are measured against ----------------------------


def committed_gates_config_path(start: str | None = None) -> str | None:
    """Reuse `gate_filesize`'s locator rather than growing a second one.

    Two walk-up formulas for the same committed file would be the copy of a rule
    that drifts (convention #266), and that locator already carries the guard
    against adopting an unrelated ancestor's file.
    """
    from gate_filesize import _committed_gates_config_path

    return _committed_gates_config_path(start)


def declared_red_proofs(start: str | None = None) -> dict[str, dict]:
    """The `red_proofs` section of the committed `tausik/gates.json`.

    Missing or malformed degrades to `{}` — and note the DIRECTION: an empty
    registry makes the audit report every in-force gate as unproven, which is
    loud. Degrading toward "everything is fine" is the one thing a measure of
    this kind must never do.
    """
    path = committed_gates_config_path(start)
    if not path:
        return {}
    try:
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    section = data.get(RED_PROOFS_SECTION) if isinstance(data, dict) else None
    if not isinstance(section, dict):
        return {}
    return {k: v for k, v in section.items() if not k.startswith("_") and isinstance(v, dict)}


def blocking_gates(gates: dict[str, dict] | None = None) -> dict[str, dict]:
    """Every gate the LIVE registry resolves to severity `block`.

    Read from the resolved registry rather than a list kept here on purpose: a
    hardcoded list is the shape this measure exists to prevent — it would go on
    answering "all proven" for gates added after it was written.
    """
    if gates is None:
        from project_config import load_gates

        gates = load_gates()
    return {n: c for n, c in gates.items() if str(c.get("severity")) == "block"}


def is_universal(gate: dict) -> bool:
    """A gate that applies regardless of the project's technologies."""
    return _STACK_KEY not in gate


# --- Resolving a cited test node --------------------------------------------


def _strip_parametrisation(node: str) -> str:
    return node.split("[", 1)[0]


def node_resolves(node_id: str, repo_root: str) -> tuple[bool, str]:
    """Does `path::[Class::]function` name something that exists in the tree?

    Returns (resolved, reason-when-not). The reason is part of the contract: a
    refusal that does not say which half of the citation is wrong sends the
    reader to grep, and a refusal without a next action is a dead end wearing a
    better name (#182).
    """
    parts = _strip_parametrisation(node_id).split("::")
    if len(parts) < 2 or len(parts) > 3:
        return False, f"malformed node id {node_id!r} (want path::func or path::Class::func)"
    rel, names = parts[0], parts[1:]
    path = os.path.join(repo_root, rel.replace("/", os.sep))
    if not os.path.isfile(path):
        return False, f"no such test file: {rel}"
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except (OSError, SyntaxError, UnicodeDecodeError) as e:
        return False, f"{rel} is not parseable: {e}"

    scope: list = tree.body
    for depth, name in enumerate(names):
        want_class = depth < len(names) - 1
        found = None
        for stmt in scope:
            if want_class and isinstance(stmt, ast.ClassDef) and stmt.name == name:
                found = stmt.body
                break
            if (
                not want_class
                and isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
                and stmt.name == name
            ):
                found = []
                break
        if found is None:
            what = "class" if want_class else "function"
            return False, f"{rel} has no {what} named {name!r}"
        scope = found
    return True, ""


# --- The measure ------------------------------------------------------------


def audit(
    gates: dict[str, dict] | None = None,
    proofs: dict[str, dict] | None = None,
    repo_root: str | None = None,
) -> Audit:
    """Judge every blocking gate. Arguments are injectable so the negative
    scenario can deprive ONE gate of its measure and watch this go red."""
    blocking = blocking_gates(gates)
    if proofs is None:
        proofs = declared_red_proofs()
    if repo_root is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    result = Audit()

    # AC2 first and separately: declared blocking, and not running at all.
    for name in sorted(blocking):
        cfg = blocking[name]
        if cfg.get("enabled"):
            continue
        if is_universal(cfg):
            result.debts.append(
                Debt(
                    name,
                    "DISABLED",
                    "declared severity=block and switched OFF — it emits no row at all, "
                    "which reads exactly like a gate that ran and found nothing. Worse "
                    "than degeneracy: a degenerate gate is at least present in the run.",
                )
            )
        else:
            result.dormant.append(name)

    in_force = sorted(n for n, c in blocking.items() if c.get("enabled"))
    for name in in_force:
        entry = proofs.get(name)
        if not entry:
            result.debts.append(
                Debt(name, "NO_PROOF", "no red_proofs entry in the committed tausik/gates.json")
            )
            continue
        node = str(entry.get("test") or "")
        if not node:
            result.debts.append(Debt(name, "NO_PROOF", "red_proofs entry names no `test` node"))
            continue
        resolved, why = node_resolves(node, repo_root)
        if not resolved:
            result.debts.append(Debt(name, "UNRESOLVABLE_PROOF", f"{node} — {why}"))
            continue
        result.proven.append(name)

    for name in sorted(set(proofs) - set(blocking)):
        result.debts.append(
            Debt(
                name,
                "STALE_ENTRY",
                "red_proofs names a gate the live registry has no blocking entry for "
                "(renamed, downgraded to warn, or removed)",
            )
        )

    result.debts.sort(key=lambda d: (d.kind != "DISABLED", d.kind, d.gate))
    return result
