"""The denominator the pytest gate reports has to be a real count.

full-pytest-hangs-while-scoped-pytest-is-green. `count_test_files` exists so a
scoped gate can say "2 of 318" instead of an unqualified "42 passed". The
mapping half of this module is pinned in tests/test_gates.py
(TestResolveTestFilesForRelevant); what is new here is the counting half and the
index it now shares with it.

Named for the module by the same basename heuristic the module implements, so a
scoped verify of gate_test_resolver.py actually runs these.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_test_resolver import (  # noqa: E402
    build_tests_index,
    count_test_files,
    resolve_test_files_for_relevant,
)
# Импортируется под другим именем НАРОЧНО: `test_roots` начинается с `test_`,
# и pytest собрал бы саму функцию как тест — он и собрал, отчитавшись ошибкой
# «fixture 'base' not found» вместо честного прогона.
from gate_test_resolver import test_roots as roots_of  # noqa: E402


def _tree(tmp_path, *rel_paths):
    for rel in rel_paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("def test_x(): pass")
    return str(tmp_path)


class TestCountTestFiles:
    def test_it_counts_nested_layouts(self, tmp_path):
        root = _tree(
            tmp_path,
            "tests/test_a.py",
            "tests/integration/test_b.py",
            "tests/unit/deep/test_c.py",
        )
        assert count_test_files(root) == 3

    def test_it_ignores_non_test_files_in_tests(self, tmp_path):
        root = _tree(tmp_path, "tests/test_a.py", "tests/conftest.py", "tests/helpers.py")
        assert count_test_files(root) == 1

    def test_a_missing_tests_dir_counts_zero_rather_than_raising(self, tmp_path):
        """A project without tests/ must not blow up the gate that reports scope."""
        assert count_test_files(str(tmp_path)) == 0

    def test_same_basename_at_two_depths_counts_twice(self, tmp_path):
        """The index buckets by basename; the count is of FILES, not of names."""
        root = _tree(tmp_path, "tests/test_dup.py", "tests/integration/test_dup.py")
        assert len(build_tests_index(root)["test_dup.py"]) == 2
        assert count_test_files(root) == 2


class TestIndexIsTheOneUsedForMapping:
    def test_the_counter_and_the_mapper_see_the_same_files(self, tmp_path):
        """Numerator and denominator must come from one walk, or they can disagree.

        A count taken from a second, differently-written walk is free to drift
        from the mapping — and then the gate reports "1 of 2" for a suite of
        three, which is exactly the kind of quietly-wrong number this label was
        added to prevent.
        """
        root = _tree(tmp_path, "tests/test_alpha.py", "tests/integration/test_beta.py")
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "alpha.py").write_text("# src")

        mapped = resolve_test_files_for_relevant(["scripts/alpha.py"], root=root)
        indexed = [p for paths in build_tests_index(root).values() for p in paths]

        assert mapped == ["tests/test_alpha.py"]
        assert set(mapped) <= set(indexed)
        assert count_test_files(root) == len(indexed)


class TestDiscoveryReachesTheDepthItPromises:
    """Обещание в докстринге и поведение обнаружения обязаны совпадать.

    Прежний предел был 2, а докстринг называл `services/api/tests` рабочим
    случаем — это три сегмента пути. `test_roots` на таком дереве возвращал
    пустой список: тот же дефект по форме, что и захардкоженный `<root>/tests`,
    который обнаружение и заводилось чинить, только уровнем ниже. Ложное
    обещание приехало тем же коммитом, что и сама глубина.
    """

    def test_a_two_segment_layout_is_found(self, tmp_path):
        root = _tree(tmp_path, "backend/tests/test_quota.py")
        assert roots_of(root) == [os.path.join(root, "backend", "tests")]

    def test_a_three_segment_layout_is_found(self, tmp_path):
        """Ровно тот случай, который докстринг обещал и не доставал."""
        root = _tree(tmp_path, "services/api/tests/test_billing.py")
        assert roots_of(root) == [os.path.join(root, "services", "api", "tests")]
        assert "test_billing.py" in build_tests_index(root)

    def test_the_nearest_level_still_wins(self, tmp_path):
        """НЕГАТИВНЫЙ: рост глубины не заставляет обнаружение уходить вглубь.

        Если тесты лежат в корне, глубокий обход не нужен и не должен добавлять
        чужие каталоги к ответу.
        """
        root = _tree(tmp_path, "tests/test_alpha.py", "services/api/tests/test_beta.py")
        assert roots_of(root) == [os.path.join(root, "tests")]

    def test_a_vendored_tree_is_not_harvested_at_the_new_depth(self, tmp_path):
        """НЕГАТИВНЫЙ: глубже — не значит без разбора.

        Чужой `tests/` в пропускаемом каталоге не наш, и включить его значит
        гонять чужой набор под видом своего. С ростом предела до трёх сегментов
        такие каталоги стали достижимы на бумаге — проверяем, что пропуск
        по-прежнему держит.
        """
        root = _tree(
            tmp_path,
            "node_modules/pkg/tests/test_foreign.py",
            ".venv/lib/tests/test_foreign.py",
            ".tausik-lib/scripts/tests/test_foreign.py",
        )
        assert roots_of(root) == [], f"подцеплены чужие тесты: {roots_of(root)}"

    def test_a_deployed_ide_profile_is_not_harvested(self, tmp_path):
        """НЕГАТИВНЫЙ: развёрнутая копия движка — не тесты проекта.

        Профили спрашиваются у `ide_utils.all_profile_dirs()`, а не
        перечисляются руками, поэтому проверяем на каталоге, взятом ОТТУДА, а
        не на выбранном автором теста.
        """
        from ide_utils import all_profile_dirs

        profile = sorted(all_profile_dirs())[0]
        root = _tree(tmp_path, f"{profile}/scripts/tests/test_engine.py")
        assert roots_of(root) == []

    def test_four_segments_are_out_of_reach_and_that_is_stated(self, tmp_path):
        """Предел назван честно: четыре сегмента не достаются.

        Это не дефект, а объявленная граница — глубже стоит дорого, а риск
        подцепить чужое растёт быстрее пользы. Кому нужно глубже, тот задаёт
        `testing.roots`; проверяем, что этот выход работает.
        """
        root = _tree(tmp_path, "a/b/c/tests/test_deep.py")
        assert roots_of(root) == []

        cfg_dir = tmp_path / ".tausik"
        cfg_dir.mkdir()
        (cfg_dir / "config.json").write_text(
            '{"testing": {"roots": ["a/b/c/tests"]}}', encoding="utf-8"
        )
        assert roots_of(root) == [os.path.join(root, "a", "b", "c", "tests")]
