"""The offline receipt check is offline because a graph walk says so, not a README.

README promises a receipt can be verified offline. That promise used to rest on a
docstring: `docs/en/no-sdk-verify.md` described only an HTTP service and did not
contain the word "offline" at all, while the working path was there the whole time.
A promise nobody can check is the same shape as a gate nobody reads.

WHY A GRAPH AND NOT A GREP, which is the borrowed half of this: a dependency two hops
away opens a socket just as well as a direct one. The walk starts at the verifier and
follows every in-repo import, so a transport arriving through a helper breaks the
build instead of quietly widening the surface.

MEASURED at the time of writing: five modules in the graph — `receipt_export`,
`crypto_sign`, `crypto_keys`, `crypto_ed25519`, `crypto_receipt` — and not one
transport among them. ed25519 is implemented here on `hashlib` alone, so there is no
dependency to smuggle a socket in either.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

#: Where the walk starts: everything `tausik receipt verify` reaches.
ENTRY_POINTS = ("receipt_export", "crypto_sign", "crypto_keys", "crypto_ed25519")

#: Anything that can reach the network or hand the job to something that can.
#: `asyncio` and `webbrowser` are here not because they are transports themselves but
#: because arriving at either means the verifier stopped being a pure function.
TRANSPORT = frozenset(
    {
        "socket",
        "urllib",
        "http",
        "httplib",
        "ssl",
        "requests",
        "httpx",
        "urllib3",
        "aiohttp",
        "ftplib",
        "telnetlib",
        "smtplib",
        "poplib",
        "imaplib",
        "asyncio",
        "xmlrpc",
        "webbrowser",
        "socketserver",
    }
)


def _direct_imports(source: str) -> set[str]:
    """Top-level package names this source imports, wherever the statement sits.

    `ast.walk` rather than a scan of module level, because a function-local import is
    still an import: the project uses them deliberately for network-touching paths,
    which is exactly the kind this check must see.
    """
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            out.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module.split(".")[0])
    return out


def reachable(entries=ENTRY_POINTS, scripts: Path | None = None) -> tuple[set[str], dict[str, str]]:
    """(modules walked, {transport: the module that imported it}).

    Returns the walked set too, so a test can refuse a walk that found nothing — a
    graph check that silently visits one file proves nothing about the graph.
    """
    root = scripts or _SCRIPTS
    seen: set[str] = set()
    queue = list(entries)
    hits: dict[str, str] = {}
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        seen.add(module)
        path = root / f"{module}.py"
        if not path.is_file():
            continue
        for dep in _direct_imports(path.read_text(encoding="utf-8")):
            if dep in TRANSPORT:
                hits.setdefault(dep, module)
            if (root / f"{dep}.py").is_file():
                queue.append(dep)
    return seen, hits


class TestTheVerifierReachesNoTransport:
    def test_no_transport_in_the_graph(self):
        walked, hits = reachable()
        assert hits == {}, (
            "the offline receipt check reached a transport: "
            + "; ".join(f"{dep} via {via}" for dep, via in sorted(hits.items()))
            + ". README promises verification without a network; keep it true or change the promise."
        )

    def test_the_walk_actually_walked(self):
        """A guard that visits nothing passes forever.

        The graph must contain the signature primitive and the artifact reader, or the
        entry points have been renamed and this check is watching an empty set.
        """
        walked, _ = reachable()
        assert {"receipt_export", "crypto_sign", "crypto_ed25519"} <= walked
        assert len(walked) >= 4, walked

    def test_the_signature_primitive_is_stdlib_only(self):
        """No third-party crypto to smuggle a socket in behind.

        ed25519 lives in this repository on `hashlib`, which is why the claim above can
        be checked at all: a vendored dependency would move the question off the graph.
        """
        deps = _direct_imports((_SCRIPTS / "crypto_ed25519.py").read_text(encoding="utf-8"))
        assert deps <= {"__future__", "hashlib", "os", "typing"}, deps


class TestTheGuardFailsWhenItShould:
    """AC-5: proved by mutation, because a green check on an empty question is no check.

    The walk runs against a throwaway tree rather than against a real edit, so proving
    the guard has teeth costs nothing and leaves no cleanup to forget.
    """

    @staticmethod
    def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
        for name, body in files.items():
            (tmp_path / name).write_text(body, encoding="utf-8")
        return tmp_path

    def test_a_direct_transport_import_is_caught(self, tmp_path):
        root = self._tree(tmp_path, {"receipt_export.py": "import socket\n"})
        _walked, hits = reachable(("receipt_export",), root)
        assert hits == {"socket": "receipt_export"}

    def test_a_transport_two_hops_away_is_caught(self, tmp_path):
        """The reason this is a graph: the helper is where a socket actually arrives."""
        root = self._tree(
            tmp_path,
            {
                "receipt_export.py": "import crypto_sign\n",
                "crypto_sign.py": "import helper\n",
                "helper.py": "import urllib.request\n",
            },
        )
        _walked, hits = reachable(("receipt_export",), root)
        assert hits == {"urllib": "helper"}

    def test_a_function_local_import_is_caught(self, tmp_path):
        """The project imports network code inside functions on purpose elsewhere.

        A check that only read module level would miss exactly the style the codebase
        uses for anything that touches the network.
        """
        root = self._tree(
            tmp_path,
            {"receipt_export.py": "def verify():\n    import requests\n    return requests\n"},
        )
        _walked, hits = reachable(("receipt_export",), root)
        assert hits == {"requests": "receipt_export"}

    @pytest.mark.parametrize("transport", sorted(TRANSPORT))
    def test_every_listed_transport_is_recognised(self, tmp_path, transport):
        """Each name in the list does something, or the list is decoration."""
        root = self._tree(tmp_path, {"receipt_export.py": f"import {transport}\n"})
        _walked, hits = reachable(("receipt_export",), root)
        assert transport in hits

    def test_an_ordinary_stdlib_import_is_not_a_transport(self, tmp_path):
        """NEGATIVE: the guard must not fire on the modules the verifier needs."""
        root = self._tree(
            tmp_path, {"receipt_export.py": "import hashlib\nimport json\nimport os\nimport re\n"}
        )
        _walked, hits = reachable(("receipt_export",), root)
        assert hits == {}


class TestTheExitCodesAreTheGate:
    """Three answers, three exit codes — the part a pipeline actually reads.

    A message a human can read is not a gate. `tausik receipt verify r.json && deploy`
    is how this command gets used, so the exit code is the contract: integrity without
    origin must NOT be zero, or the pipeline deploys on a forgery while the warning
    scrolls past. Before this task it was zero.
    """

    @staticmethod
    def _forged(tmp_path):
        """A receipt for work nobody did, signed with a key made on the spot.

        Its own key is embedded, so it is internally perfect. That is the whole point:
        the only thing standing between it and a green verdict is the refusal to treat
        an embedded key as an anchor.
        """
        import json
        import os

        import crypto_ed25519 as ed
        import crypto_keys
        import crypto_sign
        import receipt_export

        receipt = {
            "task_slug": "billing-migration",
            "passed": True,
            "exit_code": 0,
            "ran_at": "2026-09-27T00:00:00Z",
            "scope": "standard",
            "summary": "pytest=PASS",
        }
        seed = os.urandom(32)
        public = ed.public_from_seed(seed)
        envelope = {
            "envelope": crypto_sign.ENVELOPE_SCHEMA,
            "receipt": receipt,
            "signature": {
                "algorithm": "ed25519",
                "key_fingerprint": crypto_keys.fingerprint(public),
                "value": ed.sign(seed, crypto_sign.canonical_bytes(receipt)).hex(),
            },
        }
        path = tmp_path / "forged.json"
        path.write_text(json.dumps(receipt_export.build_export(envelope, public)), encoding="utf-8")
        return path, public

    def _run(self, path, *extra):
        import subprocess

        return subprocess.run(
            [sys.executable, str(_SCRIPTS / "project.py"), "receipt", "verify", str(path), *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(_REPO),
        )

    def test_integrity_without_origin_does_not_exit_zero(self, tmp_path):
        path, _public = self._forged(tmp_path)
        proc = self._run(path)
        assert proc.returncode == 3, (proc.returncode, proc.stdout, proc.stderr)
        assert "INTEGRITY ONLY" in (proc.stdout + proc.stderr)

    def test_the_message_names_both_ways_to_get_a_verdict(self, tmp_path):
        """A refusal that does not say how to proceed gets worked around, not obeyed."""
        path, _public = self._forged(tmp_path)
        proc = self._run(path)
        out = proc.stdout + proc.stderr
        assert "--pub" in out
        assert "tausik key show" in out

    def test_the_supplied_key_decides_and_a_stranger_key_fails(self, tmp_path):
        """With `--pub` the question is answered — here, against the forger."""
        path, public = self._forged(tmp_path)
        good = self._run(path, "--pub", f"ed25519:{public.hex()}")
        assert good.returncode == 0, (good.stdout, good.stderr)
        assert "you supplied" in good.stdout
        import os

        import crypto_ed25519 as ed

        stranger = ed.public_from_seed(os.urandom(32))
        bad = self._run(path, "--pub", f"ed25519:{stranger.hex()}")
        assert bad.returncode == 1, (bad.stdout, bad.stderr)
        assert "INVALID" in bad.stderr

    def test_a_file_that_is_not_an_artifact_is_a_different_code(self, tmp_path):
        """Exit 2 keeps "you gave me garbage" apart from "the signature is wrong"."""
        path = tmp_path / "junk.json"
        path.write_text('{"export": "wrong/v9"}', encoding="utf-8")
        assert self._run(path).returncode == 2
