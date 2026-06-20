"""v15-snippet-ast-detect: AST clone detection engine + CLI persistence.

Covers normalization equivalence (type-2 clones collapse), positive cluster
detection, false-positive guards (structurally distinct code does NOT cluster,
boilerplate/short blocks excluded), idempotent persistence, and syntax-error
skip (finding, not crash).
"""

from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import ast  # noqa: E402

from snippet_detect import (  # noqa: E402
    detect_clones,
    iter_python_files,
    signature,
)


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# --- normalization equivalence -------------------------------------------


def test_signature_equal_under_rename():
    """Two functions differing only in identifiers share a signature."""
    a = ast.parse("def foo(x):\n    y = x + 1\n    return y\n").body[0]
    b = ast.parse("def bar(z):\n    w = z + 1\n    return w\n").body[0]
    assert signature(a) == signature(b)


def test_signature_equal_under_literal_change():
    """Constants are normalized — different literals still match."""
    a = ast.parse("def f():\n    n = 1\n    return n + 2\n").body[0]
    b = ast.parse("def g():\n    n = 99\n    return n + 7\n").body[0]
    assert signature(a) == signature(b)


def test_signature_differs_on_structure():
    """Different control flow → different signature (no false collapse)."""
    a = ast.parse("def f(x):\n    return x + 1\n").body[0]
    b = ast.parse("def g(x):\n    if x:\n        return x\n    return 0\n").body[0]
    assert signature(a) != signature(b)


def test_signature_global_cardinality_preserved():
    """Regression: `global a` and `global x, y` must NOT share a signature.

    Global/Nonlocal `names` are list fields; collapsing the list to one token
    would lose cardinality and forge a false clone.
    """
    a = ast.parse("def f():\n    global a\n    a = 1\n").body[0]
    b = ast.parse("def g():\n    global x, y\n    x = 1\n").body[0]
    assert signature(a) != signature(b)


# --- positive cluster detection ------------------------------------------

_CLONE_A = """\
def alpha(items):
    total = 0
    for it in items:
        total += it
    return total
"""

_CLONE_B = """\
def beta(values):
    acc = 0
    for v in values:
        acc += v
    return acc
"""


def test_detects_rename_clone_across_files(tmp_path):
    _write(tmp_path, "a.py", _CLONE_A)
    _write(tmp_path, "b.py", _CLONE_B)
    res = detect_clones(str(tmp_path), min_lines=3, min_stmts=3)
    assert res.scanned == 2
    assert len(res.clusters) == 1
    cluster = res.clusters[0]
    assert len(cluster.members) == 2
    files = {os.path.basename(m[0]) for m in cluster.members}
    assert files == {"a.py", "b.py"}
    assert cluster.hash and len(cluster.hash) == 64
    assert float(len(cluster.members)) == 2.0


def test_clone_within_single_file(tmp_path):
    _write(tmp_path, "dup.py", _CLONE_A + "\n\n" + _CLONE_B)
    res = detect_clones(str(tmp_path), min_lines=3, min_stmts=3)
    assert len(res.clusters) == 1
    assert len(res.clusters[0].members) == 2


# --- false-positive guards (NEGATIVE) ------------------------------------


def test_distinct_code_does_not_cluster(tmp_path):
    _write(tmp_path, "a.py", _CLONE_A)
    _write(
        tmp_path,
        "c.py",
        "def gamma(x):\n    if x > 0:\n        return x * 2\n    return -x\n",
    )
    res = detect_clones(str(tmp_path), min_lines=3, min_stmts=3)
    assert res.clusters == []


def test_boilerplate_below_stmt_threshold_excluded(tmp_path):
    """Docstring/pass-only and tiny defs must not form a cluster."""
    stub = '''\
def stub_one():
    """Just a docstring."""
    pass


def stub_two():
    """Different docstring."""
    pass
'''
    _write(tmp_path, "stubs.py", stub)
    # Even though both stubs normalize identically, significant-stmt count is 0.
    res = detect_clones(str(tmp_path), min_lines=1, min_stmts=3)
    assert res.clusters == []


def test_short_block_below_line_threshold_excluded(tmp_path):
    twins = "def a(x):\n    return x\n\n\ndef b(y):\n    return y\n"
    _write(tmp_path, "short.py", twins)
    res = detect_clones(str(tmp_path), min_lines=10, min_stmts=1)
    assert res.clusters == []


def test_stub_method_class_not_clustered(tmp_path):
    """Regression: interface-shaped classes of pass-only methods must not cluster.

    Their bodies normalize identically, but every method is a stub, so the
    significant-statement count is 0 — the boilerplate guard must reject them.
    """
    iface = """\
class InterfaceA:
    def method_one(self):
        pass

    def method_two(self):
        pass

    def method_three(self):
        pass


class InterfaceB:
    def alpha(self):
        pass

    def beta(self):
        pass

    def gamma(self):
        pass
"""
    _write(tmp_path, "iface.py", iface)
    res = detect_clones(str(tmp_path), min_lines=1, min_stmts=3)
    assert res.clusters == []


def test_non_leading_string_literal_counts(tmp_path):
    """Only the FIRST statement is the docstring; a later bare string counts.

    Two functions whose only non-docstring statement is a string-literal Expr
    have exactly 1 significant statement; below min_stmts=2 they must not
    cluster, proving the non-leading string was counted (else count would be 0
    and the test would pass for the wrong reason — so also assert it clusters
    at min_stmts=1).
    """
    src = '''\
def a():
    """doc."""
    "side effect string"


def b():
    """other."""
    "another string"
'''
    _write(tmp_path, "s.py", src)
    assert detect_clones(str(tmp_path), min_lines=1, min_stmts=2).clusters == []
    assert len(detect_clones(str(tmp_path), min_lines=1, min_stmts=1).clusters) == 1


# --- syntax-error skip (finding, not crash) ------------------------------


def test_syntax_error_file_skipped(tmp_path):
    _write(tmp_path, "ok_a.py", _CLONE_A)
    _write(tmp_path, "ok_b.py", _CLONE_B)
    _write(tmp_path, "broken.py", "def (((:\n    this is not python\n")
    res = detect_clones(str(tmp_path), min_lines=3, min_stmts=3)
    assert any(os.path.basename(p) == "broken.py" for p in res.skipped)
    assert res.scanned == 2
    assert len(res.clusters) == 1  # valid clone still detected despite the bad file


# --- file walking --------------------------------------------------------


def test_iter_skips_noise_dirs(tmp_path):
    _write(tmp_path, "real.py", "x = 1\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "junk.py").write_text("y = 2\n", encoding="utf-8")
    found = {os.path.basename(p) for p in iter_python_files(str(tmp_path))}
    assert "real.py" in found
    assert "junk.py" not in found


def test_iter_single_file(tmp_path):
    p = _write(tmp_path, "solo.py", "z = 3\n")
    assert list(iter_python_files(p)) == [p]


# --- idempotent persistence into the snippets store ----------------------


def _fresh_db():
    from backend_schema_snippets import SNIPPETS_SQL

    conn = sqlite3.connect(":memory:")
    conn.executescript(SNIPPETS_SQL)
    return conn


def test_persisted_clusters_dedup_on_rerun(tmp_path):
    from snippet_storage import add_snippet, count_snippets

    _write(tmp_path, "a.py", _CLONE_A)
    _write(tmp_path, "b.py", _CLONE_B)
    conn = _fresh_db()

    def _ingest():
        res = detect_clones(str(tmp_path), min_lines=3, min_stmts=3)
        for c in res.clusters:
            add_snippet(
                conn,
                code_hash=c.hash,
                language=c.language,
                code=c.code,
                source_file=c.members[0][0],
                source_lines="; ".join(f"{f}:{s}-{e}" for f, s, e in c.members),
                taxonomy_kind="clone",
                fts_rank=float(len(c.members)),
            )
        return len(res.clusters)

    n_first = _ingest()
    assert n_first == 1
    assert count_snippets(conn) == 1
    # Re-run over identical sources: hash matches → no new row.
    _ingest()
    assert count_snippets(conn) == 1


# --- CLI handler (cmd_snippet) -------------------------------------------


class _FakeBackend:
    def __init__(self, conn):
        self._conn = conn


class _FakeService:
    def __init__(self, conn):
        self.be = _FakeBackend(conn)


class _Args:
    def __init__(self, **kw):
        self.snippet_cmd = "detect"
        self.path = None
        self.threshold = None
        self.__dict__.update(kw)


def test_cmd_snippet_reports_honest_write_count(tmp_path, capsys):
    """The CLI must report ACTUAL new rows, not the cluster count, on a re-run."""
    from project_cli_snippet import cmd_snippet
    from snippet_storage import count_snippets

    _write(tmp_path, "a.py", _CLONE_A)
    _write(tmp_path, "b.py", _CLONE_B)
    conn = _fresh_db()
    svc = _FakeService(conn)

    cmd_snippet(svc, _Args(path=str(tmp_path), threshold=3))
    out1 = capsys.readouterr().out
    assert "wrote 1 new" in out1
    assert count_snippets(conn) == 1

    # Re-run: dedup → zero new rows, and the message must say so (no fiction).
    cmd_snippet(svc, _Args(path=str(tmp_path), threshold=3))
    out2 = capsys.readouterr().out
    assert "wrote 0 new" in out2
    assert count_snippets(conn) == 1


def test_cmd_snippet_no_clusters_message(tmp_path, capsys):
    from project_cli_snippet import cmd_snippet

    _write(tmp_path, "solo.py", _CLONE_A)
    svc = _FakeService(_fresh_db())
    cmd_snippet(svc, _Args(path=str(tmp_path), threshold=3))
    assert "No clone clusters found." in capsys.readouterr().out
