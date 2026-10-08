"""The declared MCP<->CLI surface map and the known-loss ledger.

ratchet-for-mcp-cli-surface-parity (github#122): the MCP/CLI divergence was
caught by eyes three times in a row, all one class -- the MCP copy of a render
lost fields the CLI copy still showed:

1. ``_handle_verify`` printed gate NAMES, so a skipped gate was indistinguishable
   from a passed one (fixed earlier; the code comment still says the handler was
   "the copy that extraction did not reach, and it is the copy the agent reads").
2. ``handle_update_claudemd`` erased the memory tail on every ``/start``
   (fixed in session #177).
3. ``_handle_task_show`` hid scope_paths and rollback_plan (fixed by
   mcp-task-show-hides-the-fields-the-agent-is-judged-by, github#121, which
   moved the field list into scripts/task_detail_fields.py).

So the pair map lives HERE, once, and the test drives both surfaces on a planted
project comparing FIELD LABELS, not bytes: a label the CLI prints and the MCP
tool does not is a loss; the MCP side being richer is fine -- its envelopes are
its own. Losses that exist on purpose are debt with a reason and a number, never
silence.
"""

from __future__ import annotations

import re

# --- The pair map: every MCP tool -> its CLI twin argv, or None + a reason ----
# Placeholders ("<slug>", "<query>", ...) are substituted by the test driver.
PARITY: dict[str, tuple[str, ...] | None] = {
    # health / self-description
    "tausik_health": None,
    "tausik_self_check": None,
    "tausik_tool_schema": None,
    "tausik_status": ("status",),
    # tasks
    "tausik_task_add": ("task", "add"),
    "tausik_task_block": ("task", "block"),
    "tausik_task_claim": ("task", "claim"),
    "tausik_task_delete": ("task", "delete"),
    "tausik_task_depends": ("task", "depends"),
    "tausik_task_done": ("task", "done"),
    "tausik_task_list": ("task", "list"),
    "tausik_task_log": ("task", "log"),
    "tausik_task_logs": ("task", "logs"),
    "tausik_task_move": ("task", "move"),
    "tausik_task_next": ("task", "next"),
    "tausik_task_plan": ("task", "plan"),
    "tausik_task_quick": ("task", "quick"),
    "tausik_task_replay": ("task", "replay"),
    "tausik_task_review": ("task", "review"),
    "tausik_task_show": ("task", "show", "<slug>"),
    "tausik_task_start": ("task", "start"),
    "tausik_task_step": ("task", "step"),
    "tausik_task_unblock": ("task", "unblock"),
    "tausik_task_unclaim": ("task", "unclaim"),
    "tausik_task_undepends": ("task", "undepends"),
    "tausik_task_update": ("task", "update"),
    "tausik_reason_step": ("task", "reason-step"),
    # hierarchy
    "tausik_epic_add": ("epic", "add"),
    "tausik_epic_delete": ("epic", "delete"),
    "tausik_epic_done": ("epic", "done"),
    "tausik_epic_list": ("epic", "list"),
    "tausik_epic_update": ("epic", "update"),
    "tausik_story_add": ("story", "add"),
    "tausik_story_delete": ("story", "delete"),
    "tausik_story_done": ("story", "done"),
    "tausik_story_list": ("story", "list"),
    "tausik_story_update": ("story", "update"),
    "tausik_roadmap": ("roadmap",),
    "tausik_team": ("team",),
    # sessions
    "tausik_session_current": ("session", "current"),
    "tausik_session_end": ("session", "end"),
    "tausik_session_extend": ("session", "extend"),
    "tausik_session_handoff": ("session", "handoff"),
    "tausik_session_last_handoff": None,
    "tausik_session_list": ("session", "list"),
    "tausik_session_open": None,
    "tausik_session_start": ("session", "start"),
    "tausik_usage_event_log": None,
    # verification
    "tausik_verify": ("verify",),
    # --tasks / --story / --epic select the cohort; same command as plain verify
    "tausik_verify_cohort": ("verify",),
    "tausik_verify_hierarchy": ("verify",),
    # knowledge
    "tausik_decide": ("decide",),
    "tausik_decisions_list": ("decisions",),
    "tausik_memory_add": ("memory", "add"),
    "tausik_memory_archive": ("memory", "archive"),
    "tausik_memory_block": ("memory", "block"),
    "tausik_memory_compact": ("memory", "compact"),
    "tausik_memory_dedupe": ("memory", "dedupe"),
    "tausik_memory_delete": ("memory", "delete"),
    "tausik_memory_graph": ("memory", "graph"),
    "tausik_memory_link": ("memory", "link"),
    "tausik_memory_lint": ("memory", "lint"),
    "tausik_memory_list": ("memory", "list"),
    "tausik_memory_related": ("memory", "related"),
    "tausik_memory_search": ("memory", "search"),
    "tausik_memory_show": ("memory", "show", "<id>"),
    "tausik_memory_unlink": ("memory", "unlink"),
    "tausik_search": ("search", "<query>"),
    "tausik_fts_optimize": ("fts", "optimize"),
    "tausik_snippet_search": None,
    "tausik_dead_end": ("dead-end",),
    "tausik_events": ("events",),
    "tausik_cq_publish": None,
    "tausik_cq_query": None,
    # stacks / roles / skills
    "tausik_stack_diff": ("stack", "diff"),
    "tausik_stack_export": ("stack", "export"),
    "tausik_stack_lint": ("stack", "lint"),
    "tausik_stack_list": ("stack", "list"),
    "tausik_stack_reset": ("stack", "reset"),
    "tausik_stack_scaffold": ("stack", "scaffold"),
    "tausik_stack_show": ("stack", "info"),
    "tausik_role_create": ("role", "create"),
    "tausik_role_delete": ("role", "delete"),
    "tausik_role_list": ("role", "list"),
    "tausik_role_seed": ("role", "seed"),
    "tausik_role_show": ("role", "show"),
    "tausik_role_update": ("role", "update"),
    "tausik_skill_activate": ("skill", "activate"),
    "tausik_skill_catalog": ("skill", "catalog"),
    "tausik_skill_deactivate": ("skill", "deactivate"),
    "tausik_skill_install": ("skill", "install"),
    "tausik_skill_list": ("skill", "list"),
    "tausik_skill_repo_add": ("skill", "repo", "add"),
    "tausik_skill_repo_list": ("skill", "repo", "list"),
    "tausik_skill_repo_remove": ("skill", "repo", "remove"),
    "tausik_skill_uninstall": ("skill", "uninstall"),
    # RENAR: SPEC
    "tausik_spec_add": ("spec", "add"),
    "tausik_spec_delete": ("spec", "delete"),
    "tausik_spec_link": ("spec", "link"),
    "tausik_spec_list": ("spec", "list"),
    "tausik_spec_search": ("spec", "search"),
    "tausik_spec_show": ("spec", "show"),
    "tausik_spec_unlink": ("spec", "unlink"),
    "tausik_spec_update": ("spec", "update"),
    # RENAR: ADAPT
    "tausik_adapt_create": ("adapt", "create"),
    "tausik_adapt_delta": ("adapt", "delta"),
    "tausik_adapt_finding": ("adapt", "finding"),
    "tausik_adapt_interpret": ("adapt", "interpret"),
    "tausik_adapt_link": ("adapt", "link"),
    "tausik_adapt_list": ("adapt", "list"),
    "tausik_adapt_search": ("adapt", "search"),
    "tausik_adapt_show": ("adapt", "show"),
    "tausik_adapt_sign": ("adapt", "sign"),
    # RENAR: ACTZ
    "tausik_actz_create": ("actz", "create"),
    "tausik_actz_decided_in": ("actz", "decided-in"),
    "tausik_actz_decided_in_remove": ("actz", "decided-in-remove"),
    "tausik_actz_delete": ("actz", "delete"),
    "tausik_actz_delta": ("actz", "delta"),
    "tausik_actz_final_tz": ("actz", "final-tz"),
    "tausik_actz_link": ("actz", "link"),
    "tausik_actz_list": ("actz", "list"),
    "tausik_actz_orphans": ("actz", "orphans"),
    "tausik_actz_point": ("actz", "point"),
    "tausik_actz_search": ("actz", "search"),
    "tausik_actz_show": ("actz", "show"),
    "tausik_actz_sign": ("actz", "sign"),
    "tausik_actz_unlink": ("actz", "unlink"),
    "tausik_actz_verify": ("actz", "verify"),
    # RENAR: AT
    "tausik_at_check_freshness": ("at", "check-freshness"),
    "tausik_at_create": ("at", "create"),
    "tausik_at_delete": ("at", "delete"),
    "tausik_at_diagnose": ("at", "diagnose"),
    "tausik_at_list": ("at", "list"),
    "tausik_at_record_result": ("at", "record-result"),
    "tausik_at_release_readiness": ("at", "release-readiness"),
    "tausik_at_search": ("at", "search"),
    "tausik_at_show": ("at", "show"),
    # governance / ops
    "tausik_audit_check": ("audit", "check"),
    "tausik_audit_mark": ("audit", "mark"),
    "tausik_doctor": ("doctor",),
    "tausik_explore_current": ("explore", "current"),
    "tausik_explore_end": ("explore", "end"),
    "tausik_explore_start": ("explore", "start"),
    "tausik_gates_disable": ("gates", "disable"),
    "tausik_gates_enable": ("gates", "enable"),
    "tausik_gates_status": ("gates", "status"),
    "tausik_graph": ("graph",),
    "tausik_metrics": ("metrics",),
    "tausik_update_claudemd": ("update-claudemd",),
}

# Reasons for the pairs above that are None. Every None MUST be here, and no
# tool with a twin may hide in this dict: the test checks both directions.
NO_TWIN_REASONS: dict[str, str] = {
    "tausik_health": (
        "MCP keepalive (version + DB alive). Its CLI-side information lives in "
        "`doctor`, which is paired with tausik_doctor; a minimal health command "
        "does not exist as a CLI entry."
    ),
    "tausik_self_check": (
        "Introspection of the long-lived MCP server process (module drift since "
        "startup, sibling servers). The CLI process is not long-lived, so the "
        "observation has no CLI side."
    ),
    "tausik_tool_schema": (
        "MCP self-documentation of tool schemas; the CLI's twin is `--help`, "
        "which is a parser flag, not a command the driver can compare."
    ),
    "tausik_session_last_handoff": (
        "CLI `session handoff` writes the live handoff; reading a specific past "
        "session's handoff is served by session_open and this tool only."
    ),
    "tausik_session_open": (
        "Compound /start RPC (session + status + handoff + tasks + self_check). "
        "The CLI-side twin is the /start skill procedure, not a single command."
    ),
    "tausik_usage_event_log": (
        "Logs host-usage events for MCP-driven sessions; CLI-side usage is "
        "measured by the host harness and never logged through a command."
    ),
    "tausik_cq_publish": (
        "Cross-project Shared Brain publish; the host-side /brain skill owns "
        "this surface, the project CLI has no command for it."
    ),
    "tausik_cq_query": (
        "Cross-project Shared Brain query; same owner as cq_publish -- the "
        "/brain skill, not a project CLI command."
    ),
    "tausik_snippet_search": (
        "CLI `snippet` exposes detect/extract over the working tree; the "
        "clone-cluster search behind tausik_snippet_search has no CLI command."
    ),
}

# The number is part of the contract: an exception added without updating this
# literal (and the test that reads it) fails the ratchet.
NO_TWIN_COUNT = 9

# --- The loss ratchet: read-only pairs driven on a planted project -------------
# (mcp_tool, cli_argv, mcp_args). SLUG/QUERY substitutions happen in the test.
COMPARABLE: tuple[tuple[str, tuple[str, ...], dict], ...] = (
    ("tausik_status", ("status",), {}),
    ("tausik_roadmap", ("roadmap",), {}),
    ("tausik_epic_list", ("epic", "list"), {}),
    ("tausik_story_list", ("story", "list"), {}),
    ("tausik_task_list", ("task", "list"), {}),
    ("tausik_task_show", ("task", "show", "parity-task"), {"slug": "parity-task"}),
    ("tausik_task_logs", ("task", "logs", "parity-task"), {"slug": "parity-task"}),
    ("tausik_decisions_list", ("decisions",), {}),
    ("tausik_memory_list", ("memory", "list"), {}),
    ("tausik_memory_search", ("memory", "search", "needle"), {"query": "needle"}),
    ("tausik_session_list", ("session", "list"), {}),
    ("tausik_gates_status", ("gates", "status"), {}),
    ("tausik_team", ("team",), {}),
    ("tausik_search", ("search", "needle"), {"query": "needle"}),
    ("tausik_events", ("events",), {}),
)

# Pairs with a declared twin that the loss driver does NOT drive, each with the
# reason. Counted, like every exception.
NOT_DRIVEN_REASONS: dict[str, str] = {
    "tausik_doctor": (
        "doctor probes venv/MCP/skills live state; slow and environment-bound, "
        "not deterministic under the planted-project driver."
    ),
    "tausik_metrics": "metrics reads accumulated project history; a fresh planted project renders mostly empty sections.",
    "tausik_verify": "verify executes gates; it is a write-path command with its own receipt contract.",
    "tausik_verify_cohort": "cohort verify executes gates across tasks; write path with its own contract.",
    "tausik_verify_hierarchy": "hierarchy verify closes cohorts; write path with its own contract.",
    "tausik_graph": "graph renders the artifact graph; output is shape-stable tables covered by its own tests.",
}
NOT_DRIVEN_COUNT = 6

# The read surface, closed under the two sets above: every tool counted here is
# either driven by the loss ratchet or excused with a reason. Write paths are a
# different class (ack strings on both sides) and are not part of this claim.
READ_TOOLS = frozenset(m for m, _, _ in COMPARABLE) | frozenset(NOT_DRIVEN_REASONS)

# --- The known-loss ledger ------------------------------------------------------
# (mcp_tool, label) -> why the loss is tolerated, RIGHT NOW. The test fails on
# any undeclared loss AND on any declared loss that has healed: the ledger may
# only shrink. An entry without a reason string is refused by the test.
KNOWN_LOSSES: dict[tuple[str, str], str] = {}


_LABEL_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _/\-]{0,48}?):\s")
_NOISE = re.compile(r"\([^)]*\)")


def labels_from_text(text: str) -> set[str]:
    """Field labels a surface shows, normalised: 'Relevant memory (8):' -> 'relevant_memory'.

    Labels, not bytes: the CLI writes prose for a human, the MCP tool renders a
    payload for an agent, and demanding identical wording would freeze both.
    """
    out: set[str] = set()
    for line in text.splitlines():
        m = _LABEL_RE.match(line)
        if not m:
            continue
        label = _NOISE.sub("", m.group(1)).lower()
        label = re.sub(r"[^a-z0-9]+", "_", label).strip("_")
        if label:
            out.add(label)
    return out
