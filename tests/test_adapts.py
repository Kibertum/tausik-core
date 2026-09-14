"""v16r-adapt: RENAR ADAPT artifacts (full §7, path A — no 'lite').

Covers the v36 migration, header/body CRUD, closed finding categories + 2
signature roles (CHECK + service validation), forward interpretation §7.4.3,
dual signature §7.5 (architect ed25519 over canonical body), delta workflow §7.6
+ §7.6.4 dangling-ref guard, task_show integration, FTS5 search, CLI parser
wiring and MCP dispatch.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_migrations import run_migrations  # noqa: E402
from backend_schema import SCHEMA_VERSION  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from closed_list_counts import ADAPT_FINDING_CATEGORY_LIST, scan_tree  # noqa: E402
from closed_list_counts import written_counts as _written_counts  # noqa: E402
from service_adapts import (  # noqa: E402
    FINDING_CATEGORIES,
    HISTORICAL_SIGNATURE_ROLES,
    LINK_TARGETS,
    SIGNATURE_ROLES,
)
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "adapt.db")))
    yield s
    s.be.close()


@pytest.fixture
def svc_keyed(tmp_path):
    """Service whose project_dir carries a FRESH ephemeral ed25519 keypair.

    Generated in-fixture (not copied from the repo) so the architect-signature
    tests are fully self-contained and pass on any clean clone / CI environment.
    """
    import crypto_keys

    crypto_keys.init_keys(str(tmp_path))
    s = ProjectService(SQLiteBackend(str(tmp_path / "adapt.db")))
    s._project_dir = str(tmp_path)  # convenience: tests pass this as project_dir
    yield s
    s.be.close()


def _seed_task(svc, slug: str = "t1") -> None:
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", slug, "Task 1", role="developer", goal="g")


def _full_adapt(svc, slug: str = "a1") -> None:
    svc.adapt_create(slug, "Auth ADAPT", "TZ-2026-001")
    svc.adapt_interpret(slug, "TZ-3.1", "User logs in", "OAuth2 PKCE", "login", "reset out")
    svc.adapt_finding(slug, "gap", "No MFA stated", tz_ref="TZ-3.1")


# === AC2: closed lists are exactly the RENAR closed sets ===


def test_finding_categories_closed_seven():
    assert FINDING_CATEGORIES == (
        "contradiction",
        "gap",
        "hidden-assumption",
        "feasibility",
        "regulatory",
        "terminology",
        "scope",
    )
    assert len(FINDING_CATEGORIES) == 7


def test_signature_roles_and_link_targets_closed():
    """§7.5 as the standard now writes it: the architect signs, and nobody else.

    This asserted `("client", "architect")` — the dual signature ADR-011
    withdrew, and the corpus §7.5 has carried a paragraph on its absence since.
    The role survives in `HISTORICAL_SIGNATURE_ROLES` because a signature
    already recorded is an audit record; it is not a role anything may write.
    """
    assert SIGNATURE_ROLES == ("architect",)
    assert HISTORICAL_SIGNATURE_ROLES == ("client", "architect")
    assert "client" not in SIGNATURE_ROLES, "the withdrawn norm must not be writable"
    assert LINK_TARGETS == ("task", "spec")


# === AC1: migration v36 + fresh-DB schema ===


def test_schema_version_at_least_36():
    assert SCHEMA_VERSION >= 36


def test_migration_v36_creates_tables_clean(tmp_path):
    path = str(tmp_path / "v35.db")
    conn = sqlite3.connect(path)
    conn.isolation_level = None
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO meta VALUES('schema_version', '35')")
    conn.execute(
        "CREATE TABLE tasks(slug TEXT PRIMARY KEY, defect_of TEXT)"
    )  # defect_of: v10 column, indexed by v62
    # ALTER target for v38 — run_migrations walks every version up to current,
    # not just the one under test here.
    conn.execute("CREATE TABLE verification_runs(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    # ALTER + backfill targets for v42 (slug identity): the chain reaches them too.
    conn.execute("CREATE TABLE decisions(id INTEGER PRIMARY KEY AUTOINCREMENT)")
    conn.execute("CREATE TABLE memory(id INTEGER PRIMARY KEY AUTOINCREMENT)")

    new_ver = run_migrations(conn, 35)
    assert new_ver >= 36

    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "adapts",
        "adapt_interpretations",
        "adapt_findings",
        "adapt_signatures",
        "adapt_links",
        "fts_adapts",
    } <= tables
    trigs = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert {"adapts_ai", "adapts_ad", "adapts_au"} <= trigs
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()


def test_fresh_backend_has_adapt_tables(svc):
    rows = svc.be._q(
        "SELECT name FROM sqlite_master WHERE type IN ('table','trigger') AND name LIKE '%adapt%'"
    )
    names = {r["name"] for r in rows}
    assert {"adapts", "adapt_interpretations", "adapt_findings", "adapt_signatures"} <= names
    assert {"adapts_ai", "adapts_ad", "adapts_au"} <= names


# === AC1/AC2: header + body CRUD ===


def test_create_and_show(svc):
    msg = svc.adapt_create("a1", "Auth", "TZ-2026-001")
    assert "a1" in msg and "draft" in msg
    a = svc.adapt_show("a1")
    assert a["tz_ref"] == "TZ-2026-001"
    assert a["status"] == "draft"
    assert a["interpretations"] == [] and a["findings"] == []


def test_interpret_and_finding_recorded(svc):
    _full_adapt(svc)
    a = svc.adapt_show("a1")
    assert a["interpretations"][0]["engineering_interpretation"] == "OAuth2 PKCE"
    assert a["findings"][0]["category"] == "gap"


def test_delete_cascades_body(svc):
    _full_adapt(svc)
    svc.adapt_delete("a1")
    assert svc.adapt_list() == []


# === AC2 NEGATIVE: closed lists enforced at both layers ===


def test_invalid_category_rejected_at_service(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid finding category"):
        svc.adapt_finding("a1", "bogus", "x")


def test_invalid_category_rejected_at_db(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.finding_add("a1", "bogus", "x")


def test_invalid_role_rejected_at_db(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(sqlite3.IntegrityError):
        svc.be.signature_set("a1", "reviewer", "X", "2026-01-01T00:00:00Z")


def test_mandatory_interpretation_fields(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="mandatory"):
        svc.adapt_interpret("a1", "TZ-3.1", "", "interp", "in", "out")


def test_duplicate_slug_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="already exists"):
        svc.adapt_create("a1", "T2", "TZ-2")


def test_missing_tz_ref_rejected(svc):
    with pytest.raises(ServiceError, match="tz_ref"):
        svc.adapt_create("a1", "T", "")


# === AC4: dual signature §7.5 ===


def test_the_architect_signature_alone_completes_and_verifies(svc_keyed):
    """One signature approves, because §7.5 names one signer.

    Was `test_dual_signature_completes_and_verifies`, which signed as the
    client first and asserted the ADAPT stayed in draft until a second
    signature arrived — the withdrawn norm, pinned by a test.
    """
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    assert svc_keyed.be.adapt_get("a1")["status"] == "approved"
    res = svc_keyed.adapt_verify("a1", pd)
    assert res["signed"] and res["valid"]


def test_a_client_signature_is_refused_and_the_refusal_says_why(svc_keyed):
    """NEGATIVE SCENARIO: the withdrawn role is not merely absent from a list.

    A caller that asks for it gets a refusal naming ADR-011 and pointing at
    ACTZ — this project advertised the role in `adapt sign --help` for a
    release, so silence would leave the old habit working.
    """
    _full_adapt(svc_keyed)
    with pytest.raises(ServiceError, match="ADR-011"):
        svc_keyed.adapt_sign("a1", "client", "Acme", svc_keyed._project_dir)
    assert svc_keyed.be.adapt_get("a1")["status"] == "draft", "nothing was recorded"
    assert svc_keyed.be.signatures_for_adapt("a1") == [], "and no row was written"


def test_architect_signature_without_key_is_service_error(svc, tmp_path):
    """NEGATIVE: architect sign without a project key is a friendly error, not a traceback."""
    _full_adapt(svc)
    with pytest.raises(ServiceError, match="project key"):
        svc.adapt_sign("a1", "architect", "X", str(tmp_path / "nokey"))


def test_body_frozen_after_sign(svc_keyed):
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    with pytest.raises(ServiceError, match="frozen"):
        svc_keyed.adapt_finding("a1", "scope", "late finding")


def test_verify_unsigned_reports_not_signed(svc):
    _full_adapt(svc)
    res = svc.adapt_verify("a1")
    assert res["signed"] is False and res["valid"] is False


def test_resign_after_signed_is_rejected(svc_keyed):
    """NEGATIVE: a signed ADAPT is sealed — re-signing would silently
    overwrite the record; the caller must create a delta instead (§7.6)."""
    _full_adapt(svc_keyed)
    pd = svc_keyed._project_dir
    svc_keyed.adapt_sign("a1", "architect", "Claude", pd)
    with pytest.raises(ServiceError, match="already approved"):
        svc_keyed.adapt_sign("a1", "architect", "Mallory", pd)


# === AC5: delta workflow §7.6 + §7.6.4 dangling-ref guard ===


def test_delta_supersedes_parent(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "TZ§4 rewritten")
    assert svc.be.adapt_get("a1")["status"] == "superseded"
    d = svc.adapt_show("a1-d1")
    assert d["parent_adapt"] == "a1" and d["delta_n"] == 1


def test_link_to_superseded_is_fatal(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "TZ§4 rewritten")
    with pytest.raises(ServiceError, match="FATAL"):
        svc.adapt_link("a1", "task", "t1")
    # the live delta links fine
    assert "linked" in svc.adapt_link("a1-d1", "task", "t1")


def test_sign_superseded_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "TZ§4 rewritten")
    with pytest.raises(ServiceError, match="superseded"):
        svc.adapt_sign("a1", "architect", "X")


# === AC3 NEGATIVE: linking integrity ===


def test_link_to_missing_task_errors(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Task 'ghost' not found"):
        svc.adapt_link("a1", "task", "ghost")


def test_link_to_missing_spec_errors(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="SPEC 'ghost' not found"):
        svc.adapt_link("a1", "spec", "ghost")


def test_duplicate_link_rejected(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_link("a1", "task", "t1")
    with pytest.raises(ServiceError, match="already links"):
        svc.adapt_link("a1", "task", "t1")


def test_invalid_target_type_rejected(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid target_type"):
        svc.adapt_link("a1", "epic", "e1")


# === AC6: task_show integration ===


def test_task_show_includes_linked_adapts(svc):
    _seed_task(svc)
    svc.adapt_create("a1", "Auth", "TZ-1")
    svc.adapt_link("a1", "task", "t1")
    task = svc.task_show("t1")
    assert "adapts" in task
    assert task["adapts"][0]["slug"] == "a1"


def test_adapt_links_to_spec(svc):
    svc.spec_add("auth-spec", "ARCH", "Auth spec", "v1")
    svc.adapt_create("a1", "Auth", "TZ-1")
    svc.adapt_link("a1", "spec", "auth-spec")
    assert svc.adapts_for_target("spec", "auth-spec")[0]["slug"] == "a1"


# === FTS5 search ===


def test_fts_search_finds_adapt(svc):
    svc.adapt_create("payments-adapt", "Payment gateway reconciliation", "TZ-9")
    assert any(h["slug"] == "payments-adapt" for h in svc.adapt_search("gateway"))


def test_fts_delete_trigger_removes_entry(svc):
    svc.adapt_create("ghost", "Ephemeral interpretation", "TZ-9")
    assert svc.adapt_search("Ephemeral")
    svc.adapt_delete("ghost")
    assert svc.adapt_search("Ephemeral") == []


def test_malformed_fts_query_is_friendly_error(svc):
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="Invalid search query"):
        svc.adapt_search('"unbalanced')


# === CLI parser wiring ===


def test_cli_parser_accepts_adapt_create():
    from project_parser import build_parser

    parser = build_parser()
    ns = parser.parse_args(["adapt", "create", "a1", "Title", "--tz-ref", "TZ-1"])
    assert ns.tz_ref == "TZ-1"


def test_cli_parser_rejects_bad_finding_category():
    from project_parser import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["adapt", "finding", "a1", "bogus", "desc"])


# === MCP dispatch ===


def test_mcp_dispatch_registers_adapt_tools():
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    expected = {
        "tausik_adapt_create",
        "tausik_adapt_interpret",
        "tausik_adapt_finding",
        "tausik_adapt_sign",
        "tausik_adapt_show",
        "tausik_adapt_list",
        "tausik_adapt_delta",
        "tausik_adapt_link",
        "tausik_adapt_search",
    }
    assert expected <= set(handlers_adapt.ADAPT_HANDLERS)


def test_mcp_handler_create_and_show(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    out = handlers_adapt.handle_adapt_create(svc, {"slug": "a1", "title": "T", "tz_ref": "TZ-1"})
    assert "created" in out
    shown = handlers_adapt.handle_adapt_show(svc, {"slug": "a1"})
    assert '"tz_ref": "TZ-1"' in shown


def test_mcp_handler_invalid_category_returns_error(svc):
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    )
    import handlers_adapt

    handlers_adapt.handle_adapt_create(svc, {"slug": "a1", "title": "T", "tz_ref": "TZ-1"})
    out = handlers_adapt.handle_adapt_finding(
        svc, {"adapt_slug": "a1", "category": "bogus", "description": "x"}
    )
    assert out.startswith("Error:")


# === AC: the count of finding categories is derived, never written ===========
#
# §7.4.4 closes the categories at seven and we carry seven, so nothing is
# observably wrong today. That is exactly the state the SPEC type list was in
# before ADR-013 widened it: every written copy was correct until the day it was
# not, and then each one lied separately, in its own file. A correct literal is
# the same defect, deferred to the next amendment of a standard we do not
# control.
#
# The matcher is SHARED with the SPEC guard (tests/closed_list_counts.py) and
# parameterised by subject. Writing a second matcher here would have been this
# very defect one level up — a second copy, free to drift from the first.

# Where a written count of THIS list is legitimate, and why. Two classes only
# (memory #478 — declare the exception, never baseline the gap).
ALLOWED_ADAPT_COUNTS = {
    "scripts/backend_migrations_v36.py": (
        "the v36 record: it built the CHECK with seven categories and must say "
        "so — a migration that stops describing what it built is not a journal"
    ),
    "scripts/backend_migrations_v50.py": (
        "the v50 record: it built the CHECK with the standard's seven ADAPT "
        "STATUSES and must say so, for the same reason v36 must. The count it "
        "writes is of the STATUS list, not of the finding categories — the "
        "subject pattern is broad enough to catch either, and narrowing it to "
        "tell them apart would trade a precise exception for a weaker net"
    ),
    "tests/closed_list_counts.py": "the matcher's own worked examples",
    "tests/test_adapts.py": "this file: the fixtures below",
}

# This test walks the source tree, so no import edge selects it from the change
# that would reintroduce a written count. Declared, not opted out of.
CROSSCUTTING_SCOPE = ["scripts/", "harness/", "tests/"]


def written_counts(text):
    """The shared matcher, bound to the ADAPT finding categories."""
    return _written_counts(text, ADAPT_FINDING_CATEGORY_LIST)


# Where a literal list of the seven categories is legitimate, and why. The two
# classes are the same ones the SPEC-type guard admits: the SOURCE itself, and a
# record of what a migration built. Nothing else — a mirror "pinned by a test"
# is still a second literal somebody must remember to edit, which is what this
# guard exists to prevent.
ALLOWED_CATEGORY_LISTS = {
    "scripts/adapt_closed_lists.py": (
        "the single source itself — the declarations moved here when "
        "service_adapts crossed the filesize limit; it re-exports them"
    ),
    "scripts/backend_schema_adapts.py": (
        "the canonical DDL for a fresh database — SQL, not Python, so it cannot "
        "interpolate the tuple"
    ),
    "scripts/backend_migrations_v36.py": (
        "a HISTORICAL migration: it recorded the CHECK as it was in v36 and must "
        "never be edited, or the migration chain stops describing what it built"
    ),
    "tests/test_adapts.py": "this file: the transcription from the standard below",
}


def test_no_second_literal_list_of_finding_categories():
    """A mirror of §7.4.4 anywhere else is a future divergence.

    Three existed when this test was written — the clause module, the argparse
    `choices` list and the MCP tool schema — all agreeing, which is a STATE and
    not a property. The detector is the SPEC-type guard's, generalised over the
    list's own values rather than copied: a second detector would be this very
    defect one level up.
    """
    from closed_list_counts import ADAPT_FINDING_CATEGORY_LIST, sources

    list_re = ADAPT_FINDING_CATEGORY_LIST.literal_list_re()
    offenders = sorted(
        rel for rel, src in sources() if rel not in ALLOWED_CATEGORY_LISTS and list_re.search(src)
    )
    assert not offenders, (
        "a second literal list of backward-finding categories is a future "
        f"divergence, not a mirror; found in: {offenders}. Import "
        "FINDING_CATEGORIES, or add the path to ALLOWED_CATEGORY_LISTS with the "
        "reason it must stay literal."
    )


def test_the_literal_list_detector_is_derived_from_the_values():
    """NEGATIVE SCENARIO: the detector must fire on a copy and stay off prose.

    Its SPEC ancestor was a hand-written alternation of the type names — a
    detector of literal copies that was one — and ADR-013 made the cost plain:
    widening the list meant editing the detector by hand. This one is built
    from the values, so the two move together.
    """
    from closed_list_counts import ADAPT_FINDING_CATEGORY_LIST as subject

    list_re = subject.literal_list_re()
    copy = ", ".join(f'"{v}"' for v in FINDING_CATEGORIES)
    assert list_re.search(f"CATS = [{copy}]"), "a full copy must be found"
    truncated = ", ".join(f'"{v}"' for v in FINDING_CATEGORIES[:4])
    assert list_re.search(f"CATS = [{truncated}]"), "a TRUNCATED mirror is the drift's own shape"
    assert not list_re.search('a finding of category "gap" or "scope"'), "prose must stay clean"
    assert not list_re.search(", ".join(f'"{v}"' for v in FINDING_CATEGORIES[:3])), (
        "three in a row is a quotation, not a copy — the run floor must hold"
    )


def test_no_hand_written_count_of_finding_categories():
    offenders = scan_tree(ADAPT_FINDING_CATEGORY_LIST, ALLOWED_ADAPT_COUNTS)
    assert not offenders, (
        "the count of backward-finding categories must be formatted from "
        f"len(FINDING_CATEGORIES), never written beside the list: {offenders}. "
        "If a count is genuinely historical — a migration recording what it "
        "built — add the path to ALLOWED_ADAPT_COUNTS with that reason; never "
        "to silence a live claim."
    )


class TestTheCategoryCountMatcher:
    """Fixtures are STRINGS, and that is the point (memory #485).

    A degenerate measurer is repaired by changing the substrate a test hands it,
    never by relaxing the assertion; a diff that touches the `assert` is the tell
    that a fix was fitted to the test. Every red sample below is a line this
    repository actually carried before this change.
    """

    @pytest.mark.parametrize(
        "sample",
        [
            # Number LAST.
            # The service error, verbatim in shape: the constant is named on
            # the same line, which is what makes it a claim ABOUT this list.
            'f"Valid (closed list of 7): " + ", ".join(FINDING_CATEGORIES)',
            '"Add a backward finding to an ADAPT. category is a CLOSED list of 7"',
            # Number FIRST — the order a phrase-shaped matcher misses.
            '"""Add a backward finding. ``category`` must be one of the 7 closed types."""',
            "# RENAR backward-finding categories — CLOSED list of 7 (mirrors the DB CHECK).",
            # HYPHENATED — seven of the eleven sites wrote it this way, and the
            # digit guard rejects a digit after a hyphen ON PURPOSE (ADR-013).
            "    # --- backward findings (closed-7 §7) ---",
            '"""Insert a backward finding; ``category`` enforced as closed-7 by CHECK."""',
            'help="Add a backward finding (closed-7 §7)"',
            # "closed to N" — the clause-evidence phrasing.
            '"evidence": "ADAPT backward-finding categories closed to 7"',
        ],
    )
    def test_reds_on_a_written_count_in_every_form_this_repo_used(self, sample):
        assert written_counts(sample), (
            "the count is written out here; a matcher that misses it is reading "
            f"one formulation and not the property: {sample!r}"
        )

    def test_reds_even_though_seven_is_currently_correct(self):
        """The number agreeing with the list is not the property under test.

        A matcher satisfied by agreement cannot tell a derived count from a
        written one — the degenerate measurer of memory #484, facing the other
        way. §7.4.4 closes the list at seven and so do we; both samples below are
        RIGHT, and both must red.
        """
        assert len(FINDING_CATEGORIES) == 7, "the samples below agree with the list on purpose"
        assert written_counts("a CLOSED list of 7 backward-finding categories")
        assert written_counts("backward findings: closed-7 by CHECK")

    @pytest.mark.parametrize(
        "sample",
        [
            # The only acceptable form: no literal exists to drift.
            'f"Valid (closed list of {len(FINDING_CATEGORIES)}): ..."',
            'f"backward-finding categories closed at {len(FINDING_CATEGORIES)}"',
            # THE DISCRIMINATION THIS LIST FORCED, and the reason the SPEC
            # matcher could not simply be pointed at it: "closed-7" IS a count
            # and "ADR-013" is NOT, though both put a digit after a hyphen. The
            # cue is the word in front of it, not the punctuation. Remove that
            # distinction and every line below becomes a false positive.
            "# ADR-013 admitted two categories to the ADAPT finding list",
            "# §7.4.4 closes the backward-finding categories, QG-0 does not",
            "from backend_migrations_v36 import categories_check  # ADAPT findings",
        ],
    )
    def test_stays_green_on_derived_counts_and_on_digits_that_count_nothing(self, sample):
        """Without this branch a matcher returning a finding for every line would
        pass every red case above and look identical to a working one."""
        assert written_counts(sample) == [], (
            "nothing here writes a count of the closed list; a matcher that reds "
            f"on this is finding digits, not claims: {sample!r}"
        )

    def test_the_matcher_does_not_stray_onto_another_lists_count(self):
        """The Shared Brain has its own four categories, and decision #256 puts
        brain outside release 1.9 entirely. A subject broad enough to match
        "Sync all 4 categories" would drag an unrelated closed list into this
        task, which is how one task silently becomes three."""
        brain = '"""Sync all 4 categories. One failure does not abort others."""'
        assert written_counts(brain) == []


# === AC6/AC8: supersession needs a REASON, and 'approved' needs a signature ===
#
# Both properties are about the SAME thing: a state the standard attaches a
# condition to must not be reachable without that condition. One is enforced
# (supersession), the other is enforced by there being no write path at all
# (approved) — and the difference is a MEASUREMENT, not a preference. See the
# call-site census below.


def test_supersede_without_a_reason_is_refused(svc):
    """NEGATIVE: dezavuation with no rationale is refused, not recorded empty.

    Half a dezavuation is worse than none. The status and the `supersedes` edge
    both existed before v50, so a supersession could be recorded mechanically
    while being unable to cite the requirement it contradicts (ADR-007 p.108).
    That record is syntactically valid and substantively empty — the degenerate
    control ADR-021 names, expressed in the data schema.

    BOTH halves of the state are asserted, because asserting only the half the
    guard was written for is how the orphan below went unseen: this test used
    to check the parent alone and passed while `adapt_delta` left a committed
    child behind (external review L3, DB record #30).
    """
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="supersession_rationale"):
        svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")
    # The parent is still live: a refusal that had already flipped it would
    # leave the very state it refused to create.
    assert svc.be.adapt_get("a1")["status"] == "draft"
    # And the child was never written: a refusal is a NON-EVENT, not a partial
    # write. Both writes share one transaction precisely so this holds.
    assert svc.be.adapt_get("a1-d1") is None


def test_supersede_with_blank_reason_is_refused(svc):
    """NEGATIVE: whitespace is not a reason — the check is on content, not presence."""
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="supersession_rationale"):
        svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "   ")
    assert svc.be.adapt_get("a1")["status"] == "draft"
    assert svc.be.adapt_get("a1-d1") is None


def test_a_refused_supersession_does_not_block_its_own_retry(svc):
    """NEGATIVE, and the expensive half: the refusal must not poison the slug.

    `adapt_create` refuses a slug that already exists. So while the refused
    delta's header stayed committed, retrying the SAME slug with a proper
    rationale failed forever with "already exists" — the caller's only recovery
    was to abandon the intended slug and leave a garbage row behind. A guard
    that cannot be satisfied on the second attempt is not a guard, it is a
    trap.
    """
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="supersession_rationale"):
        svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")

    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "TZ§4 contradicts §2")

    assert svc.be.adapt_get("a1")["status"] == "superseded"
    child = svc.be.adapt_get("a1-d1")
    assert child is not None
    assert child["parent_adapt"] == "a1"
    assert child["delta_n"] == 1


def test_a_refused_supersession_leaves_the_manifest_count_untouched(svc):
    """The orphan was not merely untidy — it lied in the conformance manifest.

    `renar_conformance.gather_signals` counts a current change-set as
    `delta_n > 0 AND status != 'superseded'`. The refused delta's header
    satisfied both, so a REFUSED supersession inflated `delta_adapts_count` and
    presented itself as a live delta of a parent nobody had superseded.

    Asked through the real `gather_signals` rather than a copy of its
    predicate: a test that restates the rule it checks stops tracking the rule
    the moment the rule moves.
    """
    from renar_conformance import gather_signals

    before = gather_signals(svc.be._conn)["raw"]["delta_adapts_count"]
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError, match="supersession_rationale"):
        svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")
    after = gather_signals(svc.be._conn)["raw"]["delta_adapts_count"]
    assert after == before, "a refused supersession must add no live delta to the manifest"


def test_a_delta_refused_inside_the_transaction_leaves_it_closed(svc):
    """NEGATIVE: the non-rationale failure path must also unwind, and fully.

    An invalid slug is rejected by `adapt_create` AFTER the transaction opens,
    so it exercises the branch the rationale guard does not. Leaving that path
    without a rollback would be worse than the orphan it fixes: the connection
    would stay inside an open transaction, and every later write in the process
    would ride along in it, committing or vanishing as a group by accident.

    The open-transaction flag is asserted directly, because the damage is
    invisible in the rows: a later successful `adapt_create` looks perfectly
    normal right up until something rolls back.
    """
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ServiceError):
        svc.adapt_delta("a1", "not a valid slug!", "T delta", "TZ-1-delta-1", "a real reason")

    assert svc.be._in_tx is False, "a refusal must not leave the transaction open"
    assert svc.be.adapt_get("a1")["status"] == "draft"
    # The connection is still usable, which is the point of asserting the flag.
    svc.adapt_create("a2", "T2", "TZ-2")
    assert svc.be.adapt_get("a2") is not None


def test_a_refusal_does_not_unwind_a_transaction_it_does_not_own(svc):
    """NEGATIVE: the fix for the orphan must not become a worse trap.

    `begin_tx` no-ops inside an open transaction, but `commit_tx` and
    `rollback_tx` do not — they commit or roll back the connection outright.
    So a delta nested inside someone else's transaction, refused by the
    rationale guard, would roll back THEIR rows and hand them a closed
    transaction they still believed they owned. No exception would say so: the
    caller sees only the ServiceError it expected, and its own `rollback_tx`
    in the handler becomes a second, meaningless rollback.

    Measured before the guard was added: an outer `begin_tx` + `epic_add` lost
    its epic to exactly this. Ownership accounting is why it no longer does.
    """
    svc.adapt_create("a1", "T", "TZ-1")

    svc.be.begin_tx()
    svc.be.epic_add("outer-epic", "Outer epic", None)
    with pytest.raises(ServiceError, match="supersession_rationale"):
        svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1")

    # The caller still owns its transaction, and still owns its rows.
    assert svc.be._in_tx is True, "a nested refusal must not close the caller's transaction"
    assert svc.be.epic_get("outer-epic") is not None, "the caller's write must survive"

    # AND THE GUARANTEE IS NOW KEPT, NOT DELEGATED. This assertion used to read
    # `is not None`, and the comment above it explained why: the hand-written
    # `owns_tx` guard could decline to roll back rows that were not its own,
    # but it had no way to undo its OWN half, so the delta header stayed and
    # the duty of removing it passed to whoever opened the transaction. That
    # needed a SAVEPOINT, and `SQLiteBackend.transaction()` now uses one
    # (task transaction-owners-mostly-do-not-check-ownership). The refusal is a
    # non-event on its own terms: nobody had to clean up after it.
    assert svc.be.adapt_get("a1-d1") is None, "the refused delta undoes its own half"

    # The caller's own rows are still the caller's to discard, unchanged.
    svc.be.rollback_tx()
    assert svc.be.epic_get("outer-epic") is None
    assert svc.be.adapt_get("a1")["status"] == "draft"


def test_the_reason_is_stored_and_readable(svc):
    """The rationale is not merely demanded at the door — it is kept."""
    svc.adapt_create("a1", "T", "TZ-1")
    svc.adapt_delta("a1", "a1-d1", "T delta", "TZ-1-delta-1", "TZ§4 contradicts §2")
    assert svc.be.adapt_get("a1")["supersession_rationale"] == "TZ§4 contradicts §2"


def test_the_rule_lives_at_the_lowest_primitive(svc):
    """The refusal is the BACKEND's, so a future caller cannot route around it.

    Enforcing this in `adapt_delta` alone would close today's only door and
    leave the next one open — the mistake that cost session #209 a whole task
    (memory #556). The rule sits on the primitive that WRITES the column.
    """
    svc.adapt_create("a1", "T", "TZ-1")
    with pytest.raises(ValueError, match="supersession_rationale"):
        svc.be.adapt_set_status("a1", "superseded")
    assert svc.be.adapt_get("a1")["status"] == "draft"


def test_trigger_stage_round_trips(svc):
    """ADR-007's trigger-stage is writable and readable, not a dead column.

    A field nothing can write is as degenerate as a control that cannot fail;
    the column is plumbed through create rather than merely added to the DDL.
    """
    svc.adapt_create("a1", "T", "TZ-1", trigger_stage="design")
    assert svc.be.adapt_get("a1")["trigger_stage"] == "design"


# --- the census that keeps 'approved' unreachable without a signature -------

# This test reads the source tree, so no import edge selects it from the change
# that would add a status setter. Declared, not opted out of (memory #559).
CROSSCUTTING_SCOPE = ["scripts/"]

# Every place that WRITES an ADAPT status, and why each is allowed to.
# Measured, not assumed: my own first reading of this change claimed widening
# the domain would make 'approved' settable from the CLI, and the inventory
# showed there is no user-facing status setter at all — --status appears only as
# a LIST FILTER in project_parser_adapts and in the MCP tool schema.
EXPECTED_STATUS_WRITERS = {
    "scripts/service_adapts.py": 2,  # sign() -> approved, adapt_delta() -> superseded
}


def test_status_write_sites_are_exactly_the_two_measured():
    """§13.3.3 p.77 wants 'approved' WITH an Architect signature.

    Today that holds because the only writer of 'approved' is `sign()`, which
    runs after both signature roles are present. Nothing states that as a rule,
    so this census does: a third writer — a `tausik adapt set-status` command,
    say — turns this red and forces whoever adds it to answer the signature
    question instead of discovering it later.
    """
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts = os.path.join(repo, "scripts")
    found: dict[str, int] = {}
    for name in sorted(os.listdir(scripts)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(scripts, name), encoding="utf-8") as fh:
            body = fh.read()
        # the definition itself is not a call site
        calls = body.count("adapt_set_status(") - body.count("def adapt_set_status(")
        if calls:
            found[f"scripts/{name}"] = calls
    assert found == EXPECTED_STATUS_WRITERS, (
        f"the set of ADAPT status writers changed: {found} vs {EXPECTED_STATUS_WRITERS}. "
        "A new writer must say how it keeps 'approved' behind an Architect signature "
        "(§13.3.3 p.77) before this expectation is updated."
    )
