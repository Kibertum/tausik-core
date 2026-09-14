"""The scoped gates: everything `gate_runner.run_gates` can run over a scope.

Split out of `gate_registry` when every gate gained its §8.6(a) declaration of
the EFFECT it prevents and the module crossed the line cap. The seam is the same
one already drawn between `gate_spec` (what a gate record IS) and the registry
(which gates exist): this file is the scoped half of the data, and it is the
half that grows every time a gate is added.

Values are byte-identical to the literal they replace; tests/test_gate_registry
asserts that, because a "refactor" that quietly changes a severity or a trigger
is a behaviour change wearing a refactor's clothes.
"""

from __future__ import annotations

from gate_spec import PHASE_SCOPED, GateSpec

# --- Scoped gates: the former `default_gates.UNIVERSAL_GATES` ---------------
# Values are byte-identical to the literal they replace; tests/test_gate_registry
# asserts that, because a "refactor" that quietly changes a severity or a
# trigger is a behaviour change wearing a refactor's clothes.

_SCOPED: tuple[GateSpec, ...] = (
    GateSpec(
        name="ruff",
        prevents=(
            "A commit lands, or a verify signs a receipt, over code no linter has read. "
            "Measured, not supposed: an F541 introduced in session #183 survived the "
            "full suite, verify --task, task done with six gates and a signed receipt, "
            "because no closing gate ran a linter. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            # lint-error-shipped-because-ruff-is-not-a-closing-gate: `verify`
            # was ADDED here deliberately (release 1.9), and this is a
            # behaviour change, not a refactor. The gate was already enabled
            # and already `block`, but it only ran on `commit` — so a task
            # could be verified, closed and its receipt signed over a tree the
            # linter had never looked at. Measured, not supposed: an F541
            # introduced in session #183 survived the full suite (7386
            # passed), `verify --task`, `task done` with six gates, and a
            # signed receipt, because no closing gate runs a linter and the
            # defect changes no behaviour a test could observe.
            #
            # It runs at `verify` rather than `task-done` because that is where
            # evidence is produced, and it is scoped by `{files}` like the
            # pytest gate, so it costs a lint of the declared scope, not of the
            # tree.
            "trigger": ["commit", "verify"],
            "command": "ruff check {files}",
            "description": "Lint with ruff before commit and at verify",
            "file_extensions": [".py"],
        },
    ),
    GateSpec(
        name="mypy",
        prevents=(
            "NOTHING, and that is the honest answer: severity is warn and the gate is "
            "disabled by default, so a type error never stops a commit. Declared as an "
            "absence rather than dressed up — §8.6(a) asks which change does not "
            "happen, and for an advisory gate the answer is none. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["commit"],
            # NO {files} — DELIBERATE. `mypy {files}` handed mypy the CHANGED
            # files, while pyproject.toml declares its own source set
            # (files = ["scripts", "harness/claude/mcp/project"], exclude =
            # ["scripts/hooks/"]). Two sources of truth about WHAT is checked —
            # the same defect class this release fixed in CLAUDE.md (decision
            # #277: address from one source, content from another).
            #
            # A file passed explicitly is checked OUTSIDE the source set, so
            # imports that resolve in the normal run stop resolving: measured on
            # tests/conftest.py — three errors as an argument, zero in the
            # project run, because tests/ is not in the set at all. `exclude`
            # does not apply to explicit arguments either, so scripts/hooks/,
            # excluded on purpose, would be checked too.
            #
            # The project run also catches MORE: a change in one module that
            # breaks the types of another is invisible to a per-file run.
            # Measured cost of the whole project: 0.93 s.
            #
            # `file_extensions` still scopes WHEN the gate applies — a commit
            # touching no .py does not run it. That works without {files} since
            # mypy-gate-measures-differently-than-mypy-itself.
            "command": "mypy",
            "description": "Type-check the project's configured source set before commit",
            "file_extensions": [".py"],
        },
    ),
    GateSpec(
        name="filesize",
        prevents=(
            "A file longer than the cap is committed, or a task closes over one. What "
            "that prevents in turn is a module growing past the point where a reader "
            "can hold it, one edit at a time, with no single edit ever looking like the "
            "offender. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_filesize:run_filesize_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Warn if files exceed max_lines threshold",
            # Interim cap raised 400→500 (task l26-filesize-gate-revisit,
            # decision #190): the 400 cap deformed architecture (~30 wrapper
            # modules split only to pass; 5 core files written to exactly 400).
            # 500 absorbs every documented wrapper-merge with margin while a
            # genuinely 2× file still blocks. The real fix (measure post-MRO
            # public class surface, not raw lines) is a deferred follow-up.
            "max_lines": 500,
        },
    ),
    GateSpec(
        name="test_dedupe",
        prevents=(
            "The population of structurally indistinguishable tests grows through a "
            "commit or a close. Not the test count — copies of one argument are still "
            "one argument, and this gate never measures how many tests exist. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_test_dedupe:run_test_dedupe_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Block GROWTH in structurally indistinguishable tests",
            # The detector (`audit_pytest_dedupe`) shipped with a --check flag
            # and was documented as review-only, so nothing ran it and the
            # number grew unwatched: 294 groups / 683 tests in session #178,
            # 322 / 753 when this gate landed. Existing debt is baselined in the
            # committed tausik/gates.json and blocks nobody; only growth is red.
            # The subject is DISTINGUISHABILITY, not count — this gate never
            # measures how many tests exist, so it cannot be satisfied by
            # deleting them.
        },
    ),
    GateSpec(
        name="class_surface",
        prevents=(
            "A class whose composed public surface exceeds the cap is committed or "
            "closed over — the god-object the line cap structurally cannot see, because "
            "every mixin file stays under it while the class they compose does not. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_class_surface:run_class_surface_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Cap a class's composed public surface after inheritance",
            # Complements `filesize`, never replaces it (task filesize-mro-exempt-mcp).
            # The line gate counts raw lines per FILE, so a god-object assembled from
            # mixins is structurally invisible to it: every mixin sits under the cap
            # while the composed class exposes 129 public members. Worse, the line cap
            # CAUSED the split — module sizes pile up just under the old 400 boundary
            # (26 modules at 350-399 vs 22 at 300-349, then 6 above 400), so files were
            # cut to fit and the composed surface grew as each file looked healthier.
            # Cap + ratchet baseline live in the committed tausik/gates.json.
            "max_public_members": 60,
        },
    ),
    GateSpec(
        name="bandit",
        prevents=(
            "NOTHING today: the gate is disabled and its severity is warn, so a finding "
            "stops no commit and no close. Declared as an absence, not as protection "
            "the project does not have. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["review"],
            "command": "bandit -r {files} -q",
            "description": "Security scan with bandit",
        },
    ),
    GateSpec(
        name="tdd_order",
        prevents=(
            "NOTHING today: disabled and warn. When enabled it would stop a task "
            "closing with no test file touched — but a gate that is off prevents no "
            "change, and saying otherwise would be the claim this field exists to make "
            "checkable. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_tdd_order:run_tdd_order_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "Verify test files were modified (TDD enforcement)",
        },
    ),
    # Blocks task-done when a source edit did not reach the deployed profile that
    # actually runs (hooks/MCP load from .claude/ etc., tests import from
    # scripts/). BLOCK, not warn: an edit that did not take effect is not done.
    # Inert when no profile is installed (fresh clone / CI). See
    # gate_bootstrap_drift.py and memory #229.
    GateSpec(
        name="bootstrap_drift",
        prevents=(
            "A task closes while the deployed IDE profiles differ from scripts/ source "
            "— the state in which the CLI an agent actually runs is not the code that "
            "was reviewed. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_bootstrap_drift:run_bootstrap_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done"],
            "command": None,
            "description": "Fail if deployed IDE profiles drift from scripts/ source",
        },
    ),
    # Refuses a close/commit that routes project knowledge into another agent's
    # memory (~/.claude memory, .cursor/rules, copilot instructions, aider, …).
    # BLOCK: knowledge that lands there is not "somewhere else", it is gone for
    # every agent but one. Inert outside a git repository. See memory_sinks.py
    # for the deny-list and the three enforcement layers.
    GateSpec(
        name="memory_route",
        prevents=(
            "A task closes, or a commit lands, that routes this project's knowledge "
            "into a foreign agent's memory file — knowledge leaving the project store "
            "for a place no gate reads back. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_memory_route:run_memory_route_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Block writes that route project knowledge into a foreign agent's memory",
        },
    ),
    # One coverage gate in place of a hand-written test per kind of thing.
    # BLOCK: a name the framework ships and documents nowhere is a name nobody
    # can discover, and the release before this measured exactly what that costs
    # — a tool used twice against 226 greps. Ignores `files`; see the impl.
    GateSpec(
        name="doc_coverage",
        prevents=(
            "A command or check ships while the document a reader would go to never "
            "names it, so the only way to learn it exists is to read the parser. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_doc_coverage:run_doc_coverage_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Block a shipped name that no document mentions",
        },
    ),
    # RENAR §3.11 drift detectors (warning-mode). Read-only scans of the RENAR
    # artifact store; ignore `files`. Warn-only by design — see renar_drift.py.
    GateSpec(
        name="renar_drift_schema",
        prevents=(
            "Nothing is stopped: severity is warn. The finding is printed and the close "
            "proceeds, so what this gate prevents is an UNNOTICED schema-invalid "
            "SPEC/ADAPT, not an invalid one. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR drift-1: schema validation of SPEC/ADAPT artifacts",
        },
    ),
    GateSpec(
        name="renar_drift_provenance",
        prevents=(
            "Nothing is stopped: severity is warn. It prevents a stale "
            "TC-to-requirement link passing UNSEEN, not a task closing over one. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR drift-7: stale TC↔requirement (task↔SPEC) provenance",
        },
    ),
    # §10.11.1 (p.485) control point, under the name ADR-007 promised for it.
    # Read-only, warn-only, ignores `files` — same shape as the two above.
    GateSpec(
        name="check_adapt_supersession",
        prevents=(
            "Nothing is stopped: severity is warn. It prevents a delta-ADAPT hanging "
            "off a superseded parent going UNREPORTED at close, not the close itself. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR §10.11.1: delta-ADAPT hanging off a superseded parent",
        },
    ),
    # RENAR §8A property 2: an AT must be regenerated before every trial from
    # the CURRENT final-TZ edition. Read-only, warn-only — a stale AT is named,
    # never blocked; regenerating requires the isolated-agent procedure in
    # docs/en/at-generation-procedure.md, which this gate cannot invoke itself.
    GateSpec(
        name="at_freshness",
        prevents=(
            "Nothing is stopped: severity is warn. It prevents an AT that no longer "
            "matches the current final-TZ going UNNOTICED at close, not the close itself. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_at_freshness:run_at_freshness_gate",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR §8A.2: AT must be regenerated before trial from the current final-TZ",
        },
    ),
    # Fails a commit when the durable `tausik/` projection drifts from a fresh DB
    # export — the git-native state must equal its source of truth before it
    # enters a commit. COMMIT trigger, not task-done: a close mutates the DB (and
    # can auto-close its parent), so a task-done check would flag its own write.
    # Read-only; SKIPS (passes) when no `tausik/` tree exists (opt-in). See
    # gate_state_roundtrip.py and state-git-roundtrip-gate.
    GateSpec(
        name="state_roundtrip",
        prevents=(
            "A commit lands while the committed tausik/ projection no longer "
            "round-trips with the database — the state in which git says one thing "
            "about the project and the DB another, with nothing to say which is right. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_state_roundtrip:run_state_roundtrip_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["commit"],
            "command": None,
            "description": "Fail if the tausik/ git-native state drifts from the DB export",
        },
    ),
    # Refuses a close/commit whose CLAUDE.md DYNAMIC block was NOT rendered from
    # this database — the block with its memory tail wiped, i.e. the shape of an
    # empty/foreign project. BLOCK: the wipe reached twenty commits between v1.0.0
    # and 2026-08 while every suite stayed green, and a fresh agent reads that file
    # first and believes it. Unlike state_roundtrip this runs at task-done TOO: the
    # check is immune to staleness (it asks whether a tail exists, not whether the
    # counters are current), so a close cannot flag its own write. Read-only, and
    # inert without a DB / CLAUDE.md / markers — those are NOT_APPLICABLE and pass.
    # NOT fail-open: a fault that stops the check from running is COULD_NOT_RUN and
    # BLOCKS (claudemd-state-gate-reports-passed-when-it-could-not-run — it used to
    # be signed as PASSED). See gate_claudemd_state.py.
    GateSpec(
        name="claudemd_state_drift",
        prevents=(
            "A commit or a close over a CLAUDE.md whose dynamic block was not rendered "
            "from the live DB — the agent's first read of the project describing a "
            "state that no longer exists. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_claudemd_state:run_claudemd_state_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Fail if the CLAUDE.md dynamic block was not rendered from the live DB",
        },
    ),
    # Fails a close/commit when a changed SKILL.md breaks the agentskills.io canon
    # (name/dir + sizes). INERT unless a SKILL.md changed; hygiene, not trust.
    GateSpec(
        name="skill_spec_conformance",
        prevents=(
            "A commit or a close over a changed SKILL.md that violates the "
            "agentskills.io name/size canon — a skill that the host will silently "
            "refuse to load, discovered by nobody until an agent needs it. "
        ),
        phase=PHASE_SCOPED,
        impl="skill_spec_conformance:run_skill_conformance_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Fail if a changed SKILL.md violates the agentskills.io name/size canon",
            "file_extensions": [".md"],
        },
    ),
    GateSpec(
        name="cross_model_parity",
        prevents=(
            "A capability lands for one host and not another with nobody saying so — "
            "the second promise of 1.9 ('higher quality on ANY model') quietly "
            "becoming a promise about Claude. "
        ),
        phase=PHASE_SCOPED,
        impl="gate_cross_model_parity:run_cross_model_parity_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Differences between hosts sharing an extension point must be declared",
            # Scoped to the host layer on purpose. A gate that asks every task about
            # cross-host parity is a tax, and a tax gets switched off; this one only
            # has an opinion when bootstrap/ or scripts/hooks/ changed.
            #
            # It does NOT require sameness — Cursor has no extension point to be
            # equal to. It requires a difference to be NAMED, with a reason, and it
            # refuses a declaration that no longer matches anything live (decision
            # #335 both ways).
            #
            # NO `file_extensions` HERE, deliberately. That key is read by the
            # COMMAND runner; a built-in receives `files` unfiltered, so declaring
            # it on this gate would have been a scope that never applied — the
            # registry-of-intentions defect the gate itself exists against. The
            # scoping lives in the implementation, in HOST_LAYER_PREFIXES, where it
            # actually runs and is covered by a test.
        },
    ),
)
