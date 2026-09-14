"""A host is told the truth about whether its rules are enforced.

enforcement-coverage-is-two-of-five-hosts. All five hosts were handed the same
sentence — "Quality gates enforce these automatically" — while only claude and
qwen carried hooks and opencode a plugin. Cursor and kilo carried nothing, and
nothing anywhere said so.

WHAT IS CHECKED HERE IS THE FACT, NOT THE NAME. Every test below builds a real
profile directory, runs the real generator against it, and reads what came out.
Nothing asserts that a constant is present or that a function is called; a test
shaped that way would pass against a hard-coded sentence, which is the defect.

The centre of the file is the mutation: take a host's mechanism away and the
sentence MUST change. A notice that survives its own subject being deleted is not
derived from anything, whatever its source says.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "bootstrap"), str(_REPO / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import enforcement_coverage as be  # noqa: E402
import service_doctor_enforcement as sde  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/", "scripts/enforcement_coverage.py", "scripts/ide_utils.py"]

_CLAIM = "enforce these automatically"


def _write_hooks(profile: Path, n: int) -> None:
    """A settings.json shaped the way bootstrap writes one, with `n` commands."""
    profile.mkdir(parents=True, exist_ok=True)
    (profile / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Write",
                            "hooks": [{"type": "command", "command": f"h{i}"} for i in range(n)],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


class TestTheNoticeIsDerivedFromDisk:
    def test_a_profile_with_hooks_is_described_by_its_real_count(self, tmp_path: Path):
        profile = tmp_path / ".claude"
        _write_hooks(profile, 7)
        notice = be.build_enforcement_notice(str(profile))
        assert _CLAIM in notice
        assert "7 hook commands" in notice, notice

    def test_an_empty_profile_denies_enforcement(self, tmp_path: Path):
        profile = tmp_path / ".cursor"
        profile.mkdir()
        assert be.build_enforcement_notice(str(profile)) == be.NO_MECHANISM_NOTICE

    def test_a_host_agnostic_file_says_unknown_rather_than_zero(self):
        """Decision #334: what cannot be measured here is absent, not nought.

        AGENTS.md is read by kilo, codex and others. Answering "not enforced"
        there would be a guess about a host nobody has named, and answering
        "enforced" would be the original defect.
        """
        notice = be.build_enforcement_notice(None)
        assert notice == be.UNKNOWN_HOST_NOTICE
        assert notice != be.NO_MECHANISM_NOTICE
        assert _CLAIM not in notice

    def test_a_plugin_is_called_a_plugin_and_not_a_hook(self, tmp_path: Path):
        """OpenCode enforces through a plugin. Calling it a hook would be a small
        lie of exactly the family being fixed."""
        profile = tmp_path / ".opencode"
        (profile / "plugins").mkdir(parents=True)
        (profile / "plugins" / "tausik-qg0.js").write_text("//", encoding="utf-8")
        notice = be.build_enforcement_notice(str(profile))
        assert "1 plugin" in notice
        assert "hook" not in notice

    def test_both_shapes_are_named_when_both_are_present(self, tmp_path: Path):
        profile = tmp_path / ".hybrid"
        _write_hooks(profile, 2)
        (profile / "plugins").mkdir()
        (profile / "plugins" / "p.mjs").write_text("//", encoding="utf-8")
        assert "2 hook commands and 1 plugin" in be.build_enforcement_notice(str(profile))

    def test_an_unreadable_profile_denies_rather_than_flatters(self, tmp_path: Path):
        """A settings file we cannot parse must not be counted as enforcement.

        The cautious answer is the honest one here: we can prove a mechanism is
        deployed only by reading it, and "could not read" is not proof.
        """
        profile = tmp_path / ".broken"
        profile.mkdir()
        (profile / "settings.json").write_text("{not json", encoding="utf-8")
        assert be.build_enforcement_notice(str(profile)) == be.NO_MECHANISM_NOTICE

    def test_a_missing_profile_is_not_enforcement(self, tmp_path: Path):
        assert be.build_enforcement_notice(str(tmp_path / "nope")) == be.NO_MECHANISM_NOTICE


class TestTakingTheMechanismAwayChangesTheSentence:
    """The mutation. Without it every test above passes against a constant."""

    def test_removing_the_hooks_flips_the_notice_to_the_honest_one(self, tmp_path: Path):
        profile = tmp_path / ".claude"
        _write_hooks(profile, 4)
        with_mechanism = be.build_enforcement_notice(str(profile))
        (profile / "settings.json").unlink()
        without = be.build_enforcement_notice(str(profile))

        assert with_mechanism != without, (
            "the notice did not change when the mechanism was deleted — it is not "
            "derived from the deployment, whatever it claims to be"
        )
        assert _CLAIM in with_mechanism
        assert _CLAIM not in without
        assert without == be.NO_MECHANISM_NOTICE

    def test_emptying_the_hooks_list_counts_as_no_mechanism(self, tmp_path: Path):
        """A stanza present but empty enforces exactly nothing.

        The interesting mutation: the FILE is still there and the `hooks` key is
        still there, so any check looking for their presence stays green while
        every rule became advisory.
        """
        profile = tmp_path / ".claude"
        _write_hooks(profile, 0)
        assert be.build_enforcement_notice(str(profile)) == be.NO_MECHANISM_NOTICE

    def test_adding_a_mechanism_flips_it_back(self, tmp_path: Path):
        profile = tmp_path / ".cursor"
        profile.mkdir()
        assert be.build_enforcement_notice(str(profile)) == be.NO_MECHANISM_NOTICE
        _write_hooks(profile, 3)
        assert "3 hook commands" in be.build_enforcement_notice(str(profile))


class TestTheGeneratedFilesCarryIt:
    """Run the real generators; read what landed on disk."""

    def _generate(self, tmp_path: Path, ide: str) -> str:
        from bootstrap_generate import generate_claude_md, generate_cursorrules
        from bootstrap_opencode import generate_opencode_rules
        from bootstrap_qwen import generate_qwen_md

        p, name, stacks = str(tmp_path), "proj", ["python"]
        if ide == "claude":
            generate_claude_md(p, name, stacks)
        elif ide == "cursor":
            generate_cursorrules(p, name, stacks)
        elif ide == "qwen":
            generate_qwen_md(p, name, stacks)
        elif ide == "opencode":
            return generate_opencode_rules(p, name, stacks)
        else:
            raise AssertionError(f"no generator wired for {ide}")
        rel = sde.host_specific_rules_file(ide)
        assert rel
        return os.path.join(p, rel)

    @pytest.mark.parametrize("ide", ["claude", "cursor", "qwen"])
    def test_a_host_without_a_profile_gets_the_honest_file(self, tmp_path: Path, ide: str):
        """The mechanism sentence moved INTO the per-rule paragraph when
        `kilo-enforcement-through-the-mcp-boundary` merged the two: saying it
        twice cost a line on every turn. So the assertion is the fact, not the
        constant — the file must state that nothing is deployed, and must not
        claim automatic enforcement."""
        path = self._generate(tmp_path, ide)
        text = Path(path).read_text(encoding="utf-8")
        assert "NO REAL-TIME MECHANISM IS DEPLOYED HERE" in text
        assert "TAUSIK does not generate a real-time payload for this host" in text
        assert _CLAIM not in text

    def test_a_host_with_hooks_gets_the_claim(self, tmp_path: Path):
        _write_hooks(tmp_path / ".claude", 5)
        text = Path(self._generate(tmp_path, "claude")).read_text(encoding="utf-8")
        assert "5 hook commands" in text

    def test_agents_md_is_host_agnostic_and_says_so(self, tmp_path: Path):
        """Even with a fully equipped .claude next to it, AGENTS.md must not
        borrow that answer: kilo reads this file too."""
        from bootstrap_generate import generate_agents_md

        _write_hooks(tmp_path / ".claude", 9)
        generate_agents_md(str(tmp_path), "proj", ["python"])
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert be.UNKNOWN_HOST_NOTICE.strip() in text
        assert "9 hook commands" not in text


class TestTheBorderIsHeld:
    """The gap is DECLARED, not closed. Closing it was never this task."""

    def test_bootstrap_writes_no_hooks_payload_for_cursor(self, tmp_path: Path):
        from bootstrap_generate import generate_cursorrules

        generate_cursorrules(str(tmp_path), "proj", ["python"])
        assert be.deployed_enforcement(str(tmp_path / ".cursor")) == {"hooks": 0, "plugins": 0}

    def test_the_wrong_reason_is_gone_from_the_shipped_rules(self, tmp_path: Path):
        """The old caveat said Cursor has "no hooks API". That is a claim about
        the host, it was not ours to make, and a wrong reason closes an open
        question — worse than giving none."""
        from bootstrap_generate import generate_cursorrules

        generate_cursorrules(str(tmp_path), "proj", ["python"])
        text = (tmp_path / ".cursorrules").read_text(encoding="utf-8")
        assert "no hooks API" not in text
        assert "does not expose a PreToolUse hooks API" not in text
        assert "TAUSIK does not generate a real-time payload for this host" in text

    def test_no_host_is_named_as_enforced_without_being_measured(self, tmp_path: Path):
        """AC5: no imitation of parity. The rules table must not hand-list which
        hosts enforce Rule 1 — that list is what rotted."""
        from bootstrap_generate import generate_cursorrules

        generate_cursorrules(str(tmp_path), "proj", ["python"])
        text = (tmp_path / ".cursorrules").read_text(encoding="utf-8")
        row = [ln for ln in text.splitlines() if "Rule 1 Task before code" in ln]
        assert row, "the Rule 1 row vanished"
        assert "Instruction-only in Cursor" not in row[0]
        assert "Claude Code, VS Code Claude Extension, Qwen Code" not in row[0]


class TestTheRulesFileMappingIsDerivedNotListed:
    """Decision #335: a hand-kept list rots. The first version of this check
    carried its own host -> rules-file map, which was a copy of one `ide_utils`
    already held. The copy is gone; these tests hold the derivation to the real
    generators."""

    @pytest.mark.parametrize("ide", ["claude", "cursor", "qwen", "opencode"])
    def test_the_derived_path_is_what_the_generator_actually_writes(
        self, tmp_path: Path, ide: str
    ):
        path = TestTheGeneratedFilesCarryIt()._generate(tmp_path, ide)
        expected = os.path.join(str(tmp_path), sde.host_specific_rules_file(ide) or "")
        assert os.path.normpath(path) == os.path.normpath(expected)
        assert os.path.isfile(path), f"{ide} generator wrote nothing at the derived path"

    def test_a_file_two_hosts_read_speaks_for_neither(self):
        """AGENTS.md is codex's rules file and kilo's. Comparing it against one
        host's profile would invent a contradiction out of a sentence written for
        nobody in particular — so the mapping yields None for both, from the
        registry itself rather than from a special case."""
        from ide_utils import IDE_REGISTRY

        assert IDE_REGISTRY["kilo"]["rules_file"] == IDE_REGISTRY["codex"]["rules_file"]
        assert sde.host_specific_rules_file("kilo") is None
        assert sde.host_specific_rules_file("codex") is None

    def test_a_host_the_registry_does_not_know_yields_nothing(self):
        assert sde.host_specific_rules_file("nonesuch") is None

    def test_the_two_host_maps_in_this_repo_agree(self):
        """`bootstrap_config.IDE_DIRS` and `ide_utils.IDE_REGISTRY` are two
        records of the same fact, and this module derives from the second while
        bootstrap dispatches on the first. They must not drift: a host whose
        profile directory differs between them would be measured in one place and
        written in another.
        """
        from bootstrap_config import IDE_DIRS
        from ide_utils import IDE_REGISTRY

        assert {k: v["config_dir"] for k, v in IDE_REGISTRY.items()} == IDE_DIRS

    def test_every_scaffolded_host_is_known_to_the_registry(self):
        from bootstrap_config import SCAFFOLD_IDES
        from ide_utils import IDE_REGISTRY

        assert set(SCAFFOLD_IDES) <= set(IDE_REGISTRY)


class TestDoctorSaysItAloud:
    def test_it_reports_coverage_per_host(self, tmp_path: Path):
        _write_hooks(tmp_path / ".claude", 6)
        (tmp_path / ".cursor").mkdir()
        rows = list(sde.check_enforcement_coverage(str(tmp_path)))
        summary = next(d for s, _, d in rows if s == "ok")
        assert "claude: 6 hook commands" in summary
        assert "cursor: none" in summary

    def test_a_file_claiming_enforcement_without_a_mechanism_is_a_warning(self, tmp_path: Path):
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(
            "Quality gates (`.tausik/tausik gates status`) enforce these automatically.\n",
            encoding="utf-8",
        )
        warns = [d for s, _, d in sde.check_enforcement_coverage(str(tmp_path)) if s == "warn"]
        assert warns and ".cursorrules" in warns[0]

    def test_the_legacy_wording_is_caught_and_not_only_the_new_one(self, tmp_path: Path):
        """The files still lying in the wild carry the OLD sentence. A matcher
        tuned to the new one would be blind to every single one of them."""
        (tmp_path / ".cursor").mkdir()
        legacy = "Quality gates (`.tausik/tausik gates status`) enforce these automatically."
        assert legacy != be.build_enforcement_notice(str(tmp_path / ".claude")).strip()
        (tmp_path / ".cursorrules").write_text(legacy, encoding="utf-8")
        assert any(s == "warn" for s, _, _ in sde.check_enforcement_coverage(str(tmp_path)))

    def test_a_file_denying_enforcement_that_has_it_is_also_a_warning(self, tmp_path: Path):
        """The other direction. A stale honest file understates the host, and an
        agent that believes it will skip gates that would have caught it."""
        _write_hooks(tmp_path / ".cursor", 3)
        (tmp_path / ".cursorrules").write_text(be.NO_MECHANISM_NOTICE, encoding="utf-8")
        warns = [d for s, _, d in sde.check_enforcement_coverage(str(tmp_path)) if s == "warn"]
        assert warns and "instructions only" in warns[0]

    def test_the_declared_gap_is_not_a_warning(self, tmp_path: Path):
        """Cursor without a mechanism, and a file that says so, is the intended
        state. Warning here would train the reader to ignore this check."""
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursorrules").write_text(be.NO_MECHANISM_NOTICE, encoding="utf-8")
        assert not [s for s, _, _ in sde.check_enforcement_coverage(str(tmp_path)) if s == "warn"]

    def test_an_unscaffolded_project_says_nothing(self, tmp_path: Path):
        assert list(sde.check_enforcement_coverage(str(tmp_path))) == []


class TestCodexПлатитЗаСВОЁИмяФайла:
    """Отчёт О ПРИНУЖДЕНИИ, недосчитавший принуждения, — та же болезнь.

    Codex держит тот же полезный груз в `hooks.json`, а не в `settings.json`.
    Пока список форм этого не знал, `doctor` писал «codex: none», при том что в
    `.codex/` лежали двадцать четыре команды хуков, и читатель, решающий, защищён
    ли этот хост, получал ровно обратное правде (смена #241).
    """

    def _write_codex_hooks(self, profile: Path, n: int) -> None:
        profile.mkdir(parents=True, exist_ok=True)
        (profile / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [
                                    {"type": "command", "command": f"h{i}"} for i in range(n)
                                ],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

    def test_хуки_из_hooks_json_считаются(self, tmp_path: Path):
        profile = tmp_path / ".codex"
        self._write_codex_hooks(profile, 5)
        assert "5 hook commands" in be.describe_enforcement(be.deployed_enforcement(str(profile)))

    def test_форма_имени_объявлена_а_не_зашита_в_условие(self):
        """Список форм — точка расширения, и она названа. Следующий хост со
        своим именем файла добавляется сюда, а не новой веткой в счётчике."""
        assert "hooks.json" in be.SETTINGS_FILES
        assert "settings.json" in be.SETTINGS_FILES

    def test_пустой_профиль_codex_по_прежнему_ноль(self, tmp_path: Path):
        """Отрицательная половина: новая форма не смеет засчитывать пустоту."""
        profile = tmp_path / ".codex"
        profile.mkdir()
        assert be.describe_enforcement(be.deployed_enforcement(str(profile))) == ""
