"""Which MCP handlers are a SECOND IMPLEMENTATION of a command, measured.

Two independent implementations of one command mean two possible verdicts, and
a receipt signed on one path says nothing about the other. That is not theory
here: `tausik_update_claudemd` was a second copy of the CLI command and lost the
memory injection, so sessions closed as complete while the promise went unkept.
Divergence between the two surfaces was caught BY EYE three times running.

A handler is allowed to be a transport: read `args`, call the shared
implementation, serialise the answer, wrap an error. It becomes a second
implementation the moment it BUILDS TEXT OUT OF THE RESULT — at that point the
same data is rendered in two places and the two renderings drift.

That distinction is what this module measures, and it is derived from the code,
never listed. Two coarser criteria were tried first and both are wrong; they are
recorded here because the wrong ones look reasonable:

* "more than one statement, or a branch" flags 69 of 105 tools — it catches
  argument parsing (`args.get(...) if ... else ...`), which a transport MUST do.
* "builds text at all" flags 56 — it catches `return f"Error: {e}"`, the error
  envelope every handler in handlers_spec/handlers_adapt carries. Serialising a
  failure is not a second implementation of the command.

What survives: text built from a name that FLOWS OUT OF a call involving `svc`.
The flow is propagated (`rows = svc.x()` then `for r in rows`), names bound by
`except ... as e` are excluded, and anything derived only from `args` is
excluded. Seventeen tools out of 105 flagged when this was written.

The reader is deliberately structural: it parses, never imports. A handler
module that imports the whole MCP server would make this measurement cost a
server start-up, and an unimportable module would read as "no second
implementations" — the silent pass this module exists to prevent.
"""

from __future__ import annotations

import ast
import os

#: Where the handlers live, relative to the repository root. The DEPLOYED copy
#: sits elsewhere (`.claude/mcp/project`), and that is on purpose: the source
#: tree is what a change is reviewed against, so the source tree is what is
#: measured. Deployment parity is a different control's subject.
HANDLER_REL_DIR = os.path.join("harness", "claude", "mcp", "project")

#: Dispatch tables are recognised by NAME, the convention handlers.py documents:
#: each domain module exports `<DOMAIN>_HANDLERS` and the dispatcher merges them.
_TABLE_SUFFIX = "HANDLERS"

#: Text-building we count as rendering. `%`-formatting is deliberately absent:
#: nothing in these modules uses it, and a criterion with no subject is a
#: criterion nobody maintains.
_RENDER_METHODS = ("join", "format")


class HandlersUnreadable(Exception):
    """The handler tree could not be read. NOT the same as "nothing found"."""


def handler_dir(root: str) -> str:
    path = os.path.join(root, HANDLER_REL_DIR)
    if not os.path.isdir(path):
        raise HandlersUnreadable(
            f"MCP handler directory not found at {path}; refusing to report "
            "zero second implementations from a tree that was never read"
        )
    return path


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _bind(targets: list[ast.expr], into: set[str]) -> bool:
    added = False
    for target in targets:
        for sub in ast.walk(target):
            if isinstance(sub, ast.Name) and sub.id not in into:
                into.add(sub.id)
                added = True
    return added


def result_names(fn: ast.FunctionDef) -> set[str]:
    """Names carrying data the service produced, propagated to a fixed point.

    Starts at any call that mentions `svc` and follows the value through
    assignments, subscripts, loops and comprehensions — `rows = svc.x()` makes
    `rows` a result, and `for r in rows` makes `r` one too. Without the
    propagation the loop variable looks locally innocent and the rendering
    inside the loop goes unseen, which is exactly where these handlers render.
    """
    # An earlier version subtracted the names bound by `except ... as e` here.
    # It was dead: an exception name is bound by an ExceptHandler, never by an
    # Assign, so it cannot enter `res` in the first place — a mutation deleting
    # the subtraction changed no answer, which is how it was found. Guarding
    # against something that cannot happen reads as a guard that is doing work.
    res: set[str] = set()
    changed = True
    while changed:
        changed = False
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                src = _names(n.value)
                flows = ("svc" in src) if isinstance(n.value, ast.Call) else False
                if flows or (src & res):
                    changed |= _bind(n.targets, res)
            elif isinstance(n, ast.For) and _names(n.iter) & res:
                changed |= _bind([n.target], res)
            elif isinstance(n, ast.comprehension) and _names(n.iter) & res:
                changed |= _bind([n.target], res)
    return res - {"args", "svc"}


def renders_result(fn: ast.FunctionDef, local_functions: set[str] | None = None) -> str | None:
    """The result name this handler renders, or None if it only passes data on.

    `local_functions` names the functions defined alongside this one; it is what
    tells a shared renderer's output apart from a private helper's — see
    `_joins_a_foreign_call`. Omitting it treats every callee as foreign, which
    is the lenient reading and the right default for a caller asking about one
    function in isolation.
    """
    res = result_names(fn)
    if not res:
        return None
    local = local_functions or set()
    for node in ast.walk(fn):
        rendering: ast.AST | None = None
        if isinstance(node, ast.JoinedStr):
            rendering = node
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _RENDER_METHODS
        ):
            if _joins_a_foreign_call(node, local):
                continue
            rendering = node
        if rendering is None:
            continue
        hit = _names(rendering) & res
        if hit:
            return sorted(hit)[0]
    return None


def _joins_a_foreign_call(node: ast.Call, local_functions: set[str]) -> bool:
    """`"\\n".join(shared_renderer(...))` — stitching lines someone else built.

    That is transport, not rendering, and a handler forced to hold the service
    result in a variable (to wrap its errors in an envelope) was being flagged
    for the join alone.

    The exception is deliberately narrow: the callee must NOT be defined in the
    handler module. A local `_fmt(rows)` joined the same way is still a second
    implementation with one more indirection, and hiding rendering behind a
    private helper is exactly the move this would otherwise wave through.
    """
    if len(node.args) != 1:
        return False
    arg = node.args[0]
    if not isinstance(arg, ast.Call):
        return False
    callee = arg.func
    if isinstance(callee, ast.Name):
        return callee.id not in local_functions
    # `module.fn(...)` is never local to the handler module.
    return isinstance(callee, ast.Attribute)


def _dispatch_target(value: ast.expr) -> str | None:
    """The function a dispatch entry names, whether bare or wrapped in a lambda."""
    if isinstance(value, ast.Name):
        return value.id
    if (
        isinstance(value, ast.Lambda)
        and isinstance(value.body, ast.Call)
        and isinstance(value.body.func, ast.Name)
    ):
        return value.body.func.id
    return None


def _module_trees(path: str) -> dict[str, ast.Module]:
    trees: dict[str, ast.Module] = {}
    names = sorted(f for f in os.listdir(path) if f.startswith("handlers") and f.endswith(".py"))
    if not names:
        raise HandlersUnreadable(
            f"no handlers*.py under {path}; the dispatch tables cannot be located"
        )
    for name in names:
        with open(os.path.join(path, name), encoding="utf-8") as fh:
            try:
                trees[name] = ast.parse(fh.read())
            except SyntaxError as exc:
                raise HandlersUnreadable(f"{name} does not parse: {exc}") from exc
    return trees


def dispatch_entries(root: str) -> list[tuple[str, str, str | None]]:
    """(tool name, module, handler function) for every entry in every table."""
    path = handler_dir(root)
    entries: list[tuple[str, str, str | None]] = []
    for module, tree in _module_trees(path).items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
                continue
            target = node.targets[0]
            if not (isinstance(target, ast.Name) and target.id.endswith(_TABLE_SUFFIX)):
                continue
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    entries.append((key.value, module, _dispatch_target(value)))
    if not entries:
        raise HandlersUnreadable(
            f"no dispatch table entries found under {path}; the table convention "
            "changed and this measurement now reports on nothing"
        )
    return entries


def second_implementations(root: str) -> dict[str, str]:
    """Tool name -> `module:function` for every handler that renders the result."""
    path = handler_dir(root)
    trees = _module_trees(path)
    functions = {
        (module, node.name): node
        for module, tree in trees.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    local_by_module: dict[str, set[str]] = {}
    for module, name in functions:
        local_by_module.setdefault(module, set()).add(name)
    flagged: dict[str, str] = {}
    for tool, module, target in dispatch_entries(root):
        fn = functions.get((module, target)) if target else None
        if fn is None:
            continue
        if renders_result(fn, local_by_module.get(module, set())):
            flagged[tool] = f"{module}:{fn.name}"
    return flagged
