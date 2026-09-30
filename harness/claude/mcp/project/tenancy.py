"""One process, possibly several projects: resolution per request and a service per project.

WHY THIS EXISTS AT ALL, and the measurement says "not yet". The spike counted the live
processes: seven `claude.exe` hosts, six `tausik-project` servers, six DISTINCT parents. The
host starts one stdio server per window and pins it with `--project`, so today every process
serves exactly one project and a cache keyed by project is a cache of size one. What changes
that is a transport where the process is not tied to a window — the 2026-07-28 spec removed
the initialize handshake and the session header, so any request may land in any instance. This
module is the seam that makes that arrival survivable, and it is written now because writing
it later means writing it inside the migration.

`--project` REMAINS AND STILL WINS. It is how the host launches the server today and how a
cron job says what it means; the pinned mode behaves exactly as it did, which is the point of
keeping it rather than a courtesy.

THE COST OF TENANCY ON A PROCESS-GLOBAL. Several handlers resolve paths against the working
directory (`handlers_skill._project_dir`, the config lookup in `handlers_cq`, the user override
in `handlers_stack`). A working directory is process-wide, so serving two projects in one
process means moving it per call — and moving it per call means calls cannot overlap. In
per-request mode the registry therefore SERIALISES tool calls behind one lock and says so here
rather than leaving a race for someone to find. Pinned mode keeps the startup `chdir` and takes
no lock, so the common path pays nothing for a capability it is not using.

A DEAD PROJECT DIRECTORY IS REFUSED, NOT ADOPTED. `SQLiteBackend` creates the database file it
is pointed at, so accepting an unresolvable or vanished directory would not fail — it would
quietly open an empty project next to nothing and answer questions about it. The registry
checks for `.tausik/` before it ever constructs a service.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Callable, Mapping

#: What the agent is told when no project can be found. It names both ways out, because the two
#: causes need different actions: a directory that is not a project yet, and a host that started
#: the server somewhere unrelated to the work.
NO_PROJECT_MESSAGE = (
    "No TAUSIK project resolved for this request.\n"
    "  * If this directory should be a project: run `tausik init` in it.\n"
    "  * If the project is elsewhere: open it in the editor, or start the server with "
    "`--project <path>`.\n"
    "Resolution order: the host's signal, then ~/.config/tausik/active-project.json, then a "
    "walk up from the working directory."
)


class ProjectUnresolved(RuntimeError):
    """No project for this request. Carries the chain's notes so the reason is visible."""

    def __init__(self, notes: tuple[str, ...] = ()) -> None:
        detail = "".join(f"\n  - {n}" for n in notes)
        super().__init__(NO_PROJECT_MESSAGE + (f"\nWhat was tried:{detail}" if detail else ""))
        self.notes = notes


class ServiceRegistry:
    """Resolves the project for a call and hands back its `ProjectService`, cached.

    ``pinned`` is the `--project` path, or None for per-request resolution. The factory is
    injected so a test can build a registry without importing the whole service stack.
    """

    def __init__(
        self,
        pinned: str | None,
        factory: Callable[[str], Any],
        resolver: Callable[..., Any] | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._pinned = os.path.abspath(pinned) if pinned else None
        self._factory = factory
        self._resolver = resolver
        self._env = env if env is not None else os.environ
        self._services: dict[str, Any] = {}
        self._lock = threading.RLock()

    @property
    def pinned(self) -> str | None:
        return self._pinned

    @property
    def multi_tenant(self) -> bool:
        """True when the project is decided per request, which is also when calls serialise."""
        return self._pinned is None

    def known_projects(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._services))

    def resolve(self, cwd: str | None = None, primary_signal: str | None = None) -> str:
        """The project directory for this call, or raise `ProjectUnresolved`.

        The primary signal is PASSED THROUGH, never chosen here: which mechanism carries it is
        the spike's answer and may change without this file changing. A roots value arrives the
        same way, as a `file://` URI, and needs no branch of its own.
        """
        if self._pinned is not None:
            return self._pinned
        resolver = self._resolver
        if resolver is None:
            from gmcp_project_resolver import resolve_project

            resolver = resolve_project
        answer = resolver(primary_signal, self._env, cwd or os.getcwd())
        if answer.project_dir is None:
            raise ProjectUnresolved(tuple(answer.notes))
        return str(answer.project_dir)

    def service(self, project_dir: str) -> Any:
        """The cached service for a project, built on first use.

        Checked for being a project BEFORE construction: the backend creates the database file
        it is given, so a dead path would not raise — it would succeed at serving an empty
        project, which is the failure that looks like success.
        """
        full = os.path.abspath(project_dir)
        if not os.path.isdir(os.path.join(full, ".tausik")):
            raise ProjectUnresolved((f"{full!r} has no .tausik/ — it is not a project",))
        with self._lock:
            svc = self._services.get(full)
            if svc is None:
                svc = self._factory(full)
                self._services[full] = svc
            return svc

    def for_call(self, cwd: str | None = None, primary_signal: str | None = None) -> Any:
        """Resolve and fetch in one step — what a tool dispatcher wants."""
        return self.service(self.resolve(cwd=cwd, primary_signal=primary_signal))

    def call_context(self, project_dir: str) -> "_CallContext":
        """Hold the process working directory at `project_dir` for the duration of a call.

        Only in per-request mode, and under the registry lock, because the working directory is
        process-wide: two overlapping calls for two projects would each see the other's. Pinned
        mode returns a context that does nothing at all — the startup `chdir` already put the
        process where it belongs, and a lock there would serialise a server that has nothing to
        serialise.
        """
        return _CallContext(self, project_dir if self.multi_tenant else None)

    def close(self) -> None:
        """Drop every cached service. Errors while closing one must not strand the rest."""
        with self._lock:
            for svc in self._services.values():
                closer = getattr(getattr(svc, "be", None), "close", None)
                if callable(closer):
                    try:
                        closer()
                    except Exception:  # noqa: BLE001,S110 - a failed close must not hide the others
                        pass  # nothing to log to: close() runs on shutdown, after stderr's reader
            self._services.clear()


class _CallContext:
    """The lock-and-chdir pair, as a context manager so the restore cannot be forgotten."""

    def __init__(self, registry: ServiceRegistry, project_dir: str | None) -> None:
        self._registry = registry
        self._project_dir = project_dir
        self._previous: str | None = None

    def __enter__(self) -> "_CallContext":
        if self._project_dir is None:
            return self
        self._registry._lock.acquire()
        try:
            self._previous = os.getcwd()
            os.chdir(self._project_dir)
        except Exception:
            self._registry._lock.release()
            raise
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._project_dir is None:
            return
        try:
            if self._previous is not None:
                os.chdir(self._previous)
        finally:
            self._registry._lock.release()
