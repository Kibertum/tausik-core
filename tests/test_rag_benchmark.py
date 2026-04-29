"""Benchmark: FTS5 RAG store under load.

Run: pytest tests/test_rag_benchmark.py -v -s
"""

from __future__ import annotations

import os
import sys
import time


# Add RAG module to path
_rag_dir = os.path.join(os.path.dirname(__file__), "..", "agents", "claude", "mcp", "codebase-rag")
sys.path.insert(0, os.path.abspath(_rag_dir))

from rag_store import RAGStore


def _make_chunks(file_idx: int, chunks_per_file: int = 5) -> list[dict]:
    """Generate realistic code chunks."""
    chunks = []
    for i in range(chunks_per_file):
        chunks.append({
            "content": f"""def function_{file_idx}_{i}(arg1, arg2):
    \"\"\"Process data for module {file_idx}.\"\"\"
    result = arg1 + arg2
    if result > 100:
        raise ValueError("Overflow in function_{file_idx}_{i}")
    return result * {i + 1}

class Handler_{file_idx}_{i}:
    def __init__(self):
        self.state = {{}}
    def process(self, data):
        return self.state.get(data, None)
""",
            "chunk_index": i,
            "language": "python",
            "start_line": i * 15 + 1,
            "end_line": (i + 1) * 15,
            "chunk_type": "code",
        })
    return chunks


class TestFTS5Benchmark:
    """FTS5 RAGStore load test."""

    def test_index_1000_files(self, tmp_path):
        """Index 1000 files × 5 chunks = 5000 chunks."""
        store = RAGStore(str(tmp_path / "bench.db"))
        num_files = 1000
        chunks_per_file = 5

        t0 = time.time()
        for i in range(num_files):
            chunks = _make_chunks(i, chunks_per_file)
            store.upsert_file(f"src/module_{i}/handler.py", chunks)
        index_time = time.time() - t0

        status = store.status()
        assert status["total_chunks"] == num_files * chunks_per_file
        assert status["total_files"] == num_files

        print(f"\n  FTS5 index: {num_files} files, {num_files * chunks_per_file} chunks in {index_time:.2f}s")
        print(f"  Rate: {num_files / index_time:.0f} files/sec")

        # Search benchmark
        queries = ["function process", "Handler state", "ValueError Overflow", "result module", "arg1 arg2"]
        t0 = time.time()
        total_results = 0
        iterations = 100
        for _ in range(iterations):
            for q in queries:
                results = store.search(q, limit=20)
                total_results += len(results)
        search_time = time.time() - t0
        total_queries = iterations * len(queries)

        print(f"  FTS5 search: {total_queries} queries in {search_time:.2f}s")
        print(f"  Rate: {total_queries / search_time:.0f} queries/sec")
        print(f"  Avg results: {total_results / total_queries:.1f}")

        # Delete benchmark
        t0 = time.time()
        for i in range(0, num_files, 10):
            store.delete_file(f"src/module_{i}/handler.py")
        delete_time = time.time() - t0
        deleted = num_files // 10

        print(f"  FTS5 delete: {deleted} files in {delete_time:.2f}s")

        store.close()

        # Assertions — performance gates
        assert index_time < 30, f"Indexing too slow: {index_time:.1f}s > 30s"
        assert search_time < 10, f"Search too slow: {search_time:.1f}s > 10s"

    def test_concurrent_upsert_search(self, tmp_path):
        """Simulate concurrent indexing and searching."""
        store = RAGStore(str(tmp_path / "concurrent.db"))

        # Pre-populate
        for i in range(100):
            store.upsert_file(f"src/mod_{i}.py", _make_chunks(i, 3))

        # Interleave upsert and search
        t0 = time.time()
        for i in range(100, 200):
            store.upsert_file(f"src/mod_{i}.py", _make_chunks(i, 3))
            store.search("function process", limit=10)
            store.search("Handler state", limit=10)
        elapsed = time.time() - t0

        print(f"\n  FTS5 concurrent upsert+search: 100 upserts + 200 searches in {elapsed:.2f}s")
        assert elapsed < 15, f"Too slow: {elapsed:.1f}s > 15s"
        store.close()


