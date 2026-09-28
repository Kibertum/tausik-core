"""Semantic re-rank sits ON TOP of FTS5, and every gate that keeps it there is a measurement.

WHAT THE PLAN WANTED: pure local embeddings as the search. WHAT THE RECORD SAYS, and why this
is a re-rank instead: Cursor's online A/B (2025-11-06) got +12.5% offline accuracy and +0.3%
on code actually kept, +2.6% only past a thousand files; Sourcegraph REMOVED embeddings for
BM25F over a code graph; short keyword queries — the dominant shape an agent sends — take
semantic retrieval to nDCG@10 near zero; CORE-Bench (June 2026) says the hybrid wins and no
method dominates.

THE NEGATIVE HALF IS THE CONTRACT, and it is most of this file. With no provider, on a small
corpus, on a keyword query, or with a provider that is down, slow or answering nonsense, the
caller must get the FTS5 order — not an error, not an empty list, and not a reshuffle.

ON THIS MACHINE THE CORPUS GATE IS CLOSED: the shared store held 45 rows against a threshold
of 1000, so the measured activation rate is zero. That is the answer to "does this help us",
not a gap in the work.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import semantic_rerank as sr  # noqa: E402

_PROV = sr.Provider("http://127.0.0.1:0/api/embed", "test-model", 2.0)


def _rows(n: int) -> list[dict[str, object]]:
    return [{"id": i, "title": f"row {i}", "content": f"body {i}"} for i in range(n)]


def _fixed(order: list[int]):
    """An embedder that makes the semantic order exactly ``order``.

    The preference is carried as an ANGLE, not a magnitude: cosine normalises length away, so
    a vector that differs only in scale ranks identically to every other one — the first draft
    of this helper did exactly that and quietly tested nothing but the tie-break.
    """
    pref = {idx: 1.0 / (rank + 1) for rank, idx in enumerate(order)}

    def embedder(prov, texts):
        vecs = [[1.0, 0.0]]
        for i in range(len(texts) - 1):
            p = pref[i]
            vecs.append([p, math.sqrt(max(0.0, 1.0 - p * p))])
        return vecs

    return embedder


class TestTheQueryShapeGate:
    @pytest.mark.parametrize(
        ("query", "natural"),
        [
            pytest.param("как мы решали проблему с кэшем", True, id="ru_question"),
            pytest.param("how did we handle the cache", True, id="en_question"),
            pytest.param("cache invalidation bug", False, id="three_keywords"),
            pytest.param("sqlite fts5 bm25 rank weights", False, id="five_bare_nouns"),
            pytest.param("verify", False, id="one_word"),
            pytest.param("", False, id="empty"),
        ],
    )
    def test_glue_words_and_length_separate_a_question_from_a_bag(self, query, natural):
        """Five bare nouns is the case that matters: length alone would have passed it, and
        semantic retrieval fails on exactly that shape."""
        assert sr.is_natural_language(query) is natural


class TestTheProviderIsOptional:
    def test_no_configuration_means_no_provider(self):
        assert sr.provider_from_config(None) is None
        assert sr.provider_from_config({}) is None

    @pytest.mark.parametrize(
        "block",
        [
            pytest.param(
                {"enabled": False, "endpoint": "http://127.0.0.1:11434/api/embed", "model": "m"},
                id="off",
            ),
            pytest.param({"enabled": True, "model": "m"}, id="no_endpoint"),
            pytest.param(
                {"enabled": True, "endpoint": "http://127.0.0.1:11434/api/embed"}, id="no_model"
            ),
            pytest.param({"enabled": True, "endpoint": "", "model": "m"}, id="empty_endpoint"),
            pytest.param(
                {"enabled": True, "endpoint": "https://api.example.com/v1/embed", "model": "m"},
                id="not_loopback",
            ),
        ],
    )
    def test_an_incomplete_block_is_no_provider_rather_than_a_guess(self, block):
        assert sr.provider_from_config({"semantic_rerank": block}) is None

    def test_a_bad_timeout_falls_back_instead_of_raising(self):
        prov = sr.provider_from_config(
            {
                "semantic_rerank": {
                    "enabled": True,
                    "endpoint": "http://127.0.0.1:11434/api/embed",
                    "model": "m",
                    "timeout_s": "soon",
                }
            }
        )
        assert prov is not None and prov.timeout_s == sr.DEFAULT_TIMEOUT_S


class TestTheGateNamesItsReason:
    @pytest.mark.parametrize(
        ("prov", "corpus", "query", "reason"),
        [
            pytest.param(None, 5000, "как мы это решали в прошлый раз", "no-provider", id="none"),
            pytest.param(_PROV, 45, "как мы это решали в прошлый раз", "small-corpus", id="small"),
            pytest.param(_PROV, 5000, "fts5 bm25 weights", "keyword-query", id="keyword"),
            pytest.param(_PROV, 5000, "как мы это решали в прошлый раз", None, id="open"),
        ],
    )
    def test_each_closed_gate_is_distinguishable_from_the_others(self, prov, corpus, query, reason):
        """Named reasons, not a boolean: "never switched on" and "not worth switching on" are
        different answers about whether the feature earns its keep."""
        assert sr.gate(query, corpus, prov) == reason

    def test_the_corpus_threshold_is_the_one_the_numbers_named(self):
        assert sr.MIN_CORPUS_ROWS == 1_000


class TestAClosedGateCostsNothing:
    """THE ZERO-DEPENDENCY PATH: identical output, no provider touched, no error."""

    @pytest.mark.parametrize(
        ("prov", "corpus", "query"),
        [
            pytest.param(None, 5000, "как мы решали это раньше", id="no_provider"),
            pytest.param(_PROV, 45, "как мы решали это раньше", id="small_corpus"),
            pytest.param(_PROV, 5000, "bm25 rank weights", id="keyword_query"),
        ],
    )
    def test_the_keyword_order_is_returned_untouched(self, prov, corpus, query):
        rows = _rows(8)

        def must_not_be_called(*_a, **_k):
            raise AssertionError("a closed gate must not reach the provider")

        out, d = sr.rerank(query, rows, prov, corpus, 5, embedder=must_not_be_called)
        assert [r["id"] for r in out] == [0, 1, 2, 3, 4]
        assert d.gate is not None and d.ran is False and d.changed_top is False

    def test_no_candidates_is_an_empty_page_and_not_an_error(self):
        out, d = sr.rerank("как мы решали это раньше", [], None, 5000, 5)
        assert out == [] and d.gate == "no-provider"


class TestAFailingProviderDegrades:
    def test_a_provider_that_answers_nothing_costs_only_the_reordering(self):
        rows = _rows(8)
        out, d = sr.rerank(
            "как мы решали это раньше", rows, _PROV, 5000, 5, embedder=lambda *_: None
        )
        assert [r["id"] for r in out] == [0, 1, 2, 3, 4]
        assert d.gate == "provider-failed"

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({"embeddings": [[1.0]]}, id="wrong_count"),
            pytest.param({"embeddings": "not-a-list"}, id="wrong_type"),
            pytest.param({}, id="no_key"),
            pytest.param({"embeddings": [["a"], ["b"]]}, id="not_numbers"),
        ],
    )
    def test_a_wrong_shaped_answer_is_treated_as_a_failure_not_guessed_at(self, body, monkeypatch):
        """A provider answering nonsense must be indistinguishable from one that is down:
        guessing what the numbers meant would reorder a search by noise."""
        import urllib.request

        class _Resp:
            def read(self):
                return json.dumps(body).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

        monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: _Resp())
        assert sr.embed(_PROV, ["one", "two"]) is None

    def test_an_unreachable_endpoint_returns_none_rather_than_raising(self):
        """The endpoint in the fixture is port 0 — nothing is listening, by construction."""
        assert sr.embed(sr.Provider("http://127.0.0.1:1/api/embed", "m", 0.2), ["x"]) is None

    def test_a_layer_over_its_budget_hands_back_the_keyword_order(self, monkeypatch):
        rows = _rows(8)
        clock = iter([0.0, 9.0])
        monkeypatch.setattr(sr.time, "monotonic", lambda: next(clock))
        out, d = sr.rerank(
            "как мы решали это раньше",
            rows,
            _PROV,
            5000,
            5,
            embedder=lambda p, texts: [[1.0]] * len(texts),
        )
        assert [r["id"] for r in out] == [0, 1, 2, 3, 4]
        assert d.gate == "over-budget" and d.elapsed_ms >= 2000


class TestFusionReordersAndNeverRetrieves:
    def test_the_page_is_always_a_permutation_of_what_fts5_found(self):
        rows = _rows(8)
        out, d = sr.rerank(
            "как мы решали это раньше",
            rows,
            _PROV,
            5000,
            5,
            embedder=_fixed([7, 6, 5, 4, 3, 2, 1, 0]),
        )
        assert d.ran and len(out) == 5
        assert set(r["id"] for r in out) <= set(range(8)), "no row appears that FTS5 did not"

    def test_a_semantic_favourite_can_reach_the_page_but_only_through_fusion(self):
        """RRF, not replacement: the seventh candidate rises, and the keyword leader stays on
        the page. A layer that simply adopted the semantic order would be the replacement this
        task exists not to build."""
        rows = _rows(8)
        out, _ = sr.rerank(
            "как мы решали это раньше",
            rows,
            _PROV,
            5000,
            5,
            embedder=_fixed([7, 0, 1, 2, 3, 4, 5, 6]),
        )
        ids = [r["id"] for r in out]
        assert 7 in ids, "the semantic favourite reached the page"
        assert 0 in ids, "and the keyword leader did not lose its place"

    def test_agreement_changes_nothing(self):
        rows = _rows(8)
        out, d = sr.rerank(
            "как мы решали это раньше", rows, _PROV, 5000, 5, embedder=_fixed(list(range(8)))
        )
        assert [r["id"] for r in out] == [0, 1, 2, 3, 4]
        assert d.ran and d.changed_top is False

    def test_a_fusion_over_mismatched_sets_keeps_the_spine(self):
        """A dropped hit is worse than no fusion, so the mismatch falls back rather than
        computing a score over a set it cannot account for."""
        assert sr.fuse([0, 1, 2], [0, 1]) == [0, 1, 2]

    def test_ties_resolve_to_the_keyword_order(self):
        assert sr.fuse([0, 1, 2], [0, 1, 2]) == [0, 1, 2]

    @pytest.mark.parametrize(
        ("a", "b", "expected"),
        [
            pytest.param([1.0, 0.0], [1.0, 0.0], 1.0, id="identical"),
            pytest.param([1.0, 0.0], [0.0, 1.0], 0.0, id="orthogonal"),
            pytest.param([0.0, 0.0], [1.0, 1.0], 0.0, id="zero_vector"),
            pytest.param([1.0], [1.0, 0.0], 0.0, id="length_mismatch"),
        ],
    )
    def test_cosine_answers_zero_instead_of_raising(self, a, b, expected):
        assert sr.cosine(a, b) == pytest.approx(expected)


class TestTheMeasurementIsOnOurOwnTraffic:
    def test_no_records_is_reported_as_no_records(self, tmp_path):
        """Absence as absence: a rate over nothing is a number that invites a conclusion."""
        r = sr.report(str(tmp_path))
        assert r == {"searches": 0, "ran": 0, "changed_top": 0, "gates": {}, "p95_ms": None}
        assert "no searches recorded" in sr.render_report(r)

    def test_the_report_separates_ran_from_gated(self, tmp_path):
        for d in (
            sr.Decision(None, 5000, 20, True, 300),
            sr.Decision(None, 5000, 20, False, 400),
            sr.Decision("small-corpus", 45, 5, False, 0),
            sr.Decision("no-provider", 0, 5, False, 0),
        ):
            sr.log_decision(str(tmp_path), d)
        r = sr.report(str(tmp_path))
        assert r["searches"] == 4 and r["ran"] == 2 and r["changed_top"] == 1
        assert r["gates"] == {"small-corpus": 1, "no-provider": 1}
        assert r["p95_ms"] == 400

    def test_the_query_text_is_never_written_down(self, tmp_path):
        """A search string can hold a secret, and a telemetry file is the last place to find
        that out — so the record carries shapes, never words."""
        sr.log_decision(str(tmp_path), sr.Decision(None, 5000, 20, True, 300))
        line = json.loads((tmp_path / sr.SIDECAR_NAME).read_text(encoding="utf-8").strip())
        assert set(line) == {"ts", "gate", "corpus_rows", "candidates", "changed_top", "elapsed_ms"}

    def test_a_truncated_tail_line_does_not_refuse_the_report(self, tmp_path):
        sr.log_decision(str(tmp_path), sr.Decision(None, 5000, 20, True, 300))
        with open(tmp_path / sr.SIDECAR_NAME, "a", encoding="utf-8") as fh:
            fh.write('{"gate": nul')
        assert sr.report(str(tmp_path))["searches"] == 1

    def test_an_unwritable_directory_costs_the_record_and_not_the_search(self, tmp_path):
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("x", encoding="utf-8")
        sr.log_decision(str(blocker), sr.Decision(None, 5000, 20, True, 300))  # must not raise

    def test_the_sidecar_has_a_declared_lifetime(self):
        """A file that grows per search and has no retention policy is the omission this
        project already paid for once, at 19 MiB."""
        from telemetry_retention import POLICIES

        policy = next((p for p in POLICIES if p.name == sr.SIDECAR_NAME), None)
        assert policy is not None, f"{sr.SIDECAR_NAME} has no retention policy"
        assert policy.keep_lines is not None and len(policy.reason) > 40


class TestTheKeywordPathIsUnchangedByDefault:
    def test_the_candidate_window_stays_at_the_page_size_with_no_provider(self, tmp_path):
        """The default checkout must not pay for a switched-off feature: a widened window on
        every search would be a cost with no benefit, which is how optional stops being it."""
        import sqlite3

        from knowledge_read import _rerank_window

        conn = sqlite3.connect(":memory:")
        window, prov, corpus = _rerank_window(conn, "как мы решали это раньше", 5)
        assert window == 5 and prov is None and corpus == 0


class TestTheLatencyBudgetIsRealAndNotAspirational:
    def test_the_default_search_stays_far_under_the_two_second_promise(self):
        """MEASURED on the live store: median 6.3 ms, p95 46.2 ms over 20 searches — the bound
        asserted here is 2 s, so it holds with roughly forty times the headroom. A wall-clock
        assertion with that much room is a guard against a regression of kind, not of noise.
        """
        import time

        from knowledge_read import search_shared_memory

        worst = 0.0
        for q in ("как мы решали проблему с кэшем", "fts5 bm25", "почему падает тест"):
            started = time.perf_counter()
            search_shared_memory(q, limit=5)
            worst = max(worst, time.perf_counter() - started)
        assert worst < 2.0, f"slowest local search took {worst:.2f}s against a 2s budget"

    def test_the_probe_answers_from_the_corpus_rather_than_from_an_empty_log(self):
        """The on-our-own-traffic answer for a checkout with no provider: instrumenting the
        switched-off path would cost a file write per search to learn what the corpus size
        already says."""
        text = sr.probe()
        assert "threshold of 1000" in text
        assert "Provider configured:" in text
        assert "natural-language query would meet" in text
        assert "keyword query would meet" in text


class TestTheEndpointGoesThroughTheBoundary:
    """An embeddings provider is handed whole rows verbatim, so where it lives is the
    boundary's question and not this module's — one place decides, which is what decision
    #358 left behind after four of them disagreed."""

    @pytest.mark.parametrize(
        ("endpoint", "refused"),
        [
            pytest.param("https://api.example.com/v1/embed", True, id="hosted"),
            pytest.param("http://10.0.0.5:11434/api/embed", True, id="lan"),
            pytest.param("http://127.0.0.1:11434/api/embed", False, id="loopback_v4"),
            pytest.param("http://[::1]:11434/api/embed", False, id="loopback_v6"),
        ],
    )
    def test_the_refusal_carries_a_reason_a_human_can_act_on(self, endpoint, refused):
        reason = sr.endpoint_refusal(endpoint)
        assert (reason is not None) is refused
        if refused:
            assert "loopback" in reason

    def test_a_refused_endpoint_closes_the_gate_instead_of_breaking_the_search(self):
        """Returned, not raised: a misconfigured endpoint must cost the feature, not the
        answer. The probe prints the refusal so it does not merely look switched off."""
        prov = sr.provider_from_config(
            {
                "semantic_rerank": {
                    "enabled": True,
                    "endpoint": "https://api.example.com/v1/embed",
                    "model": "m",
                }
            }
        )
        assert prov is None
        assert sr.gate("как мы это решали раньше", 5000, prov) == "no-provider"
