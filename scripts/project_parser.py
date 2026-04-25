"""TAUSIK argparse parser — CLI command tree."""

from __future__ import annotations

import argparse

from project_types import (
    VALID_COMPLEXITIES,
    VALID_EDGE_RELATIONS,
    VALID_MEMORY_TYPES,
    VALID_NODE_TYPES,
    VALID_STACKS,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tausik", description="TAUSIK")
    sub = p.add_subparsers(dest="command")

    # --- init ---
    init_p = sub.add_parser("init", help="Initialize project")
    init_p.add_argument(
        "--name", default=None, help="Project slug (default: directory name)"
    )

    # --- status ---
    sub.add_parser("status", help="Project overview")

    # --- epic ---
    epic_p = sub.add_parser("epic", help="Epic management")
    epic_sub = epic_p.add_subparsers(dest="epic_cmd")
    ea = epic_sub.add_parser(
        "add",
        epilog='Example: tausik epic add my-epic "Epic title"',
    )
    ea.add_argument("slug", help="Epic slug (lowercase, hyphens)")
    ea.add_argument("title", help="Epic title (in quotes)")
    ea.add_argument("--description", default=None)
    epic_sub.add_parser("list")
    ed = epic_sub.add_parser("done")
    ed.add_argument("slug")
    edel = epic_sub.add_parser("delete")
    edel.add_argument("slug")

    # --- story ---
    story_p = sub.add_parser("story", help="Story management")
    story_sub = story_p.add_subparsers(dest="story_cmd")
    sa = story_sub.add_parser(
        "add",
        epilog='Example: tausik story add my-epic my-story "Story title"',
    )
    sa.add_argument("epic_slug", help="Parent epic slug")
    sa.add_argument("slug", help="Story slug (lowercase, hyphens)")
    sa.add_argument("title", help="Story title (in quotes)")
    sa.add_argument("--description", default=None)
    sl = story_sub.add_parser("list")
    sl.add_argument("--epic", default=None)
    sd = story_sub.add_parser("done")
    sd.add_argument("slug")
    sdel = story_sub.add_parser("delete")
    sdel.add_argument("slug")

    # --- task ---
    task_p = sub.add_parser("task", help="Task management")
    task_sub = task_p.add_subparsers(dest="task_cmd")

    ta = task_sub.add_parser(
        "add",
        epilog='Example: tausik task add "Task title" --group my-story --slug my-task --complexity medium',
    )
    ta.add_argument("title", help="Task title (in quotes)")
    ta.add_argument(
        "--group", default=None, dest="story_slug", help="Parent story slug (optional)"
    )
    ta.add_argument(
        "--slug", default=None, help="Task slug (auto-generated from title if omitted)"
    )
    ta.add_argument("--stack", default=None)
    ta.add_argument("--complexity", default=None, choices=sorted(VALID_COMPLEXITIES))
    ta.add_argument("--goal", default=None)
    ta.add_argument("--role", default=None)
    ta.add_argument(
        "--defect-of", default=None, help="Parent task slug (marks this as a defect)"
    )

    tl = task_sub.add_parser("list")
    tl.add_argument("--status", default=None)
    tl.add_argument("--story", default=None)
    tl.add_argument("--epic", default=None)
    tl.add_argument("--role", default=None)
    tl.add_argument("--stack", default=None)
    tl.add_argument("--limit", type=int, default=None, help="Max tasks to return")

    ts = task_sub.add_parser("show")
    ts.add_argument("slug")

    tstart = task_sub.add_parser("start")
    tstart.add_argument("slug")

    tdone = task_sub.add_parser("done")
    tdone.add_argument("slug")
    tdone.add_argument(
        "--ac-verified",
        action="store_true",
        help="Confirm all acceptance criteria verified",
    )
    tdone.add_argument(
        "--no-knowledge",
        action="store_true",
        dest="no_knowledge",
        help="Confirm no knowledge to capture",
    )
    tdone.add_argument("--relevant-files", nargs="*", default=None)

    tblock = task_sub.add_parser("block")
    tblock.add_argument("slug")
    tblock.add_argument("--reason", default=None)

    tunblock = task_sub.add_parser("unblock")
    tunblock.add_argument("slug")

    treview = task_sub.add_parser("review")
    treview.add_argument("slug")

    tupdate = task_sub.add_parser("update")
    tupdate.add_argument("slug")
    tupdate.add_argument("--title", default=None)
    tupdate.add_argument("--goal", default=None)
    tupdate.add_argument("--notes", default=None)
    tupdate.add_argument("--acceptance-criteria", default=None, dest="ac")
    tupdate.add_argument(
        "--stack",
        default=None,
        choices=sorted(VALID_STACKS),
    )
    tupdate.add_argument(
        "--complexity", default=None, choices=sorted(VALID_COMPLEXITIES)
    )
    tupdate.add_argument("--role", default=None)
    tupdate.add_argument("--scope", default=None)
    tupdate.add_argument("--scope-exclude", default=None, dest="scope_exclude")

    tdel = task_sub.add_parser("delete")
    tdel.add_argument("slug")

    tplan = task_sub.add_parser("plan")
    tplan.add_argument("slug")
    tplan.add_argument("steps", nargs="+")

    tstep = task_sub.add_parser("step")
    tstep.add_argument("slug")
    tstep.add_argument("step_num", type=int)

    tquick = task_sub.add_parser("quick", help="Quick-create task (auto-slug)")
    tquick.add_argument("title", help="Task title")
    tquick.add_argument("--goal", default=None)
    tquick.add_argument("--role", default=None)
    tquick.add_argument("--stack", default=None)

    tnext = task_sub.add_parser("next", help="Pick next available task")
    tnext.add_argument("--agent", default=None, help="Agent ID to auto-claim")

    tlog = task_sub.add_parser(
        "log",
        epilog='Example: tausik task log my-task "Implemented auth middleware"',
    )
    tlog.add_argument("slug", help="Task slug")
    tlog.add_argument("message", help="Log message (appended to notes with timestamp)")

    tlogs = task_sub.add_parser(
        "logs",
        epilog="Example: tausik task logs my-task --phase review",
    )
    tlogs.add_argument("slug", help="Task slug")
    tlogs.add_argument(
        "--phase",
        help="Filter by phase (planning, implementation, review, testing, done)",
    )

    tmove = task_sub.add_parser("move")
    tmove.add_argument("slug")
    tmove.add_argument("new_story_slug")

    tclaim = task_sub.add_parser("claim")
    tclaim.add_argument("slug")
    tclaim.add_argument("agent_id")

    tunclaim = task_sub.add_parser("unclaim")
    tunclaim.add_argument("slug")

    # --- team ---
    sub.add_parser("team", help="Team status — tasks by agent")

    # --- session ---
    sess_p = sub.add_parser("session", help="Session management")
    sess_sub = sess_p.add_subparsers(dest="session_cmd")
    sess_sub.add_parser("start")
    se = sess_sub.add_parser("end")
    se.add_argument("--summary", default=None)
    sess_sub.add_parser("current")
    ssl = sess_sub.add_parser("list")
    ssl.add_argument("--limit", type=int, default=10)
    sh = sess_sub.add_parser("handoff")
    sh.add_argument("json_data", help="Handoff JSON string")
    sess_sub.add_parser("last-handoff")
    sext = sess_sub.add_parser("extend", help="Extend session duration by N minutes")
    sext.add_argument(
        "--minutes", type=int, default=60, help="Minutes to extend (default: 60)"
    )

    # --- decide ---
    dec_p = sub.add_parser("decide", help="Record a decision")
    dec_p.add_argument("text")
    dec_p.add_argument("--task", default=None)
    dec_p.add_argument("--rationale", default=None)

    # --- decisions ---
    decs_p = sub.add_parser("decisions", help="List decisions")
    decs_p.add_argument("--limit", type=int, default=20)

    # --- memory ---
    mem_p = sub.add_parser("memory", help="Project memory")
    mem_sub = mem_p.add_subparsers(dest="memory_cmd")
    ma = mem_sub.add_parser("add")
    ma.add_argument("mem_type", choices=sorted(VALID_MEMORY_TYPES))
    ma.add_argument("title")
    ma.add_argument("content")
    ma.add_argument("--tags", nargs="*", default=None)
    ma.add_argument("--task", default=None)
    ml = mem_sub.add_parser("list")
    ml.add_argument("--type", default=None, dest="mem_type")
    ml.add_argument("--limit", type=int, default=50)
    ms = mem_sub.add_parser("search")
    ms.add_argument("query")
    mshow = mem_sub.add_parser("show")
    mshow.add_argument("id", type=int)
    mdel = mem_sub.add_parser("delete")
    mdel.add_argument("id", type=int)
    # graph subcommands
    mlink = mem_sub.add_parser("link", help="Create edge between nodes")
    mlink.add_argument("source_type", choices=sorted(VALID_NODE_TYPES))
    mlink.add_argument("source_id", type=int)
    mlink.add_argument("target_type", choices=sorted(VALID_NODE_TYPES))
    mlink.add_argument("target_id", type=int)
    mlink.add_argument("relation", choices=sorted(VALID_EDGE_RELATIONS))
    mlink.add_argument("--confidence", type=float, default=1.0)
    mlink.add_argument("--created-by", default=None)
    munlink = mem_sub.add_parser(
        "unlink", help="Soft-invalidate an edge (never deletes)"
    )
    munlink.add_argument("edge_id", type=int)
    munlink.add_argument(
        "--replacement", type=int, default=None, help="Replacement edge ID"
    )
    mrelated = mem_sub.add_parser("related", help="Find related nodes via graph")
    mrelated.add_argument("node_type", choices=sorted(VALID_NODE_TYPES))
    mrelated.add_argument("node_id", type=int)
    mrelated.add_argument("--hops", type=int, default=2)
    mrelated.add_argument("--include-invalid", action="store_true")
    mgraph = mem_sub.add_parser("graph", help="List graph edges")
    mgraph.add_argument(
        "--type", default=None, dest="node_type", choices=sorted(VALID_NODE_TYPES)
    )
    mgraph.add_argument("--id", type=int, default=None, dest="node_id")
    mgraph.add_argument(
        "--relation",
        default=None,
        choices=sorted(VALID_EDGE_RELATIONS),
    )
    mgraph.add_argument("--include-invalid", action="store_true")
    mgraph.add_argument("--limit", type=int, default=50)
    mblock = mem_sub.add_parser(
        "block",
        help="Print compact memory block (decisions + conventions + dead ends) for re-injection",
    )
    mblock.add_argument("--max-decisions", type=int, default=5)
    mblock.add_argument("--max-conventions", type=int, default=10)
    mblock.add_argument("--max-deadends", type=int, default=5)
    mblock.add_argument("--max-lines", type=int, default=50)
    mcompact = mem_sub.add_parser(
        "compact",
        help="Aggregate recent task_logs into pattern summary (phases, top words, top files)",
    )
    mcompact.add_argument("--last", type=int, default=50, dest="last_n")

    # --- gates ---
    gates_p = sub.add_parser("gates", help="Quality gates status")
    gates_sub = gates_p.add_subparsers(dest="gates_cmd")
    gates_sub.add_parser("status", help="Show active gates and their config")
    gates_sub.add_parser("list", help="List all gates with enabled/disabled state")
    ge = gates_sub.add_parser("enable")
    ge.add_argument("name", help="Gate name to enable")
    gd = gates_sub.add_parser("disable")
    gd.add_argument("name", help="Gate name to disable")

    # --- verify (SENAR Rule 5: scoped per-task verification) ---
    vp = sub.add_parser(
        "verify",
        help="Run quality gates scoped to a task's relevant_files; record result",
    )
    vp.add_argument("--task", help="Task slug (uses its relevant_files for scope)")
    vp.add_argument(
        "--scope",
        choices=["lightweight", "standard", "high", "critical", "manual"],
        default="manual",
        help="Verification tier label recorded with the run (default: manual)",
    )

    # --- roadmap ---
    rm_p = sub.add_parser("roadmap", help="Project roadmap")
    rm_p.add_argument("--include-done", action="store_true")

    # --- update-claudemd ---
    uc_p = sub.add_parser("update-claudemd", help="Update CLAUDE.md dynamic section")
    uc_p.add_argument(
        "--claudemd", default=None, help="Path to CLAUDE.md (auto-detected if omitted)"
    )

    # --- metrics / hud / suggest-model ---
    sub.add_parser("metrics", help="Project metrics and velocity")
    sub.add_parser("hud", help="Live dashboard")
    sub.add_parser(
        "suggest-model", help="Suggest Claude model for complexity"
    ).add_argument("complexity", nargs="?", default=None)

    # --- search ---
    sr_p = sub.add_parser("search", help="Full-text search")
    sr_p.add_argument("query")
    sr_p.add_argument(
        "--scope", default="all", choices=["all", "tasks", "memory", "decisions"]
    )
    sr_p.add_argument("--limit", type=int, default=20, help="Max results per scope")

    # --- fts ---
    fts_p = sub.add_parser("fts", help="FTS5 index maintenance")
    fts_sub = fts_p.add_subparsers(dest="fts_cmd")
    fts_sub.add_parser("optimize", help="Optimize all FTS5 indexes")

    # --- skill ---
    sk_p = sub.add_parser("skill", help="External skill lifecycle management")
    sk_sub = sk_p.add_subparsers(dest="skill_cmd")
    sk_act = sk_sub.add_parser("activate", help="Copy vendor skill to .claude/skills/")
    sk_act.add_argument("name", help="Skill name from vendor catalog")
    sk_deact = sk_sub.add_parser("deactivate", help="Remove skill from .claude/skills/")
    sk_deact.add_argument("name", help="Skill name to deactivate")
    sk_sub.add_parser("list", help="List skills: active, vendored, available")
    sk_inst = sk_sub.add_parser(
        "install", help="Install skill from repo (clone + copy + deps)"
    )
    sk_inst.add_argument("name", help="Skill name to install")
    sk_uninst = sk_sub.add_parser("uninstall", help="Remove skill completely")
    sk_uninst.add_argument("name", help="Skill name to uninstall")

    # skill repo subcommands
    sk_repo = sk_sub.add_parser("repo", help="Manage skill repositories")
    sk_repo_sub = sk_repo.add_subparsers(dest="repo_cmd")
    sk_repo_add = sk_repo_sub.add_parser(
        "add", help="Add a TAUSIK-compatible skill repo"
    )
    sk_repo_add.add_argument("url", help="Git URL of skill repo")
    sk_repo_rm = sk_repo_sub.add_parser("remove", help="Remove a skill repo")
    sk_repo_rm.add_argument("name", help="Repo name to remove")
    sk_repo_sub.add_parser("list", help="List configured skill repos")

    # --- events ---
    ev_p = sub.add_parser("events", help="Audit event log")
    ev_p.add_argument(
        "--entity", default=None, help="Filter by entity type (task, epic, story)"
    )
    ev_p.add_argument(
        "--id", default=None, dest="entity_id", help="Filter by entity ID/slug"
    )
    ev_p.add_argument("--limit", type=int, default=50)

    # --- SENAR ops subparsers (dead-end, explore, audit, brain, run) ---
    from project_parser_ops import (
        add_audit,
        add_brain,
        add_dead_end,
        add_explore,
        add_run,
    )

    add_dead_end(sub)
    add_explore(sub)
    add_audit(sub)
    add_brain(sub)
    add_run(sub)

    return p
