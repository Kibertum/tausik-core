"""An owner's prohibition, read at the point of action rather than filed and forgotten.

THE MEASUREMENT THAT PRODUCED THIS. The owner said plainly that CI was not wanted until the
release approached. Twenty-three commits followed, each with a push and therefore a pipeline.
Twenty-three to nothing in favour of the ritual.

THE CAUSE IS STRUCTURAL, NOT MOTIVATIONAL, and that is why trying harder does not touch it. The
framework's own rules are GATED: verify blocks a close, the changelog blocks a close, push-ok is
built into the commit ritual. An owner's instruction blocks nothing and is read by nothing. When
the two diverge, the one that stops things wins. The instruction does not evaporate because it
was rejected; it evaporates because it has no enforcement surface.

WHY AN EXACT MARKER AND NOT PROSE. Measured over 399 decisions: a keyword search for a
prohibition returns five, of which three are about something else entirely — a hard gate, a
scanner, a story being added. Forty percent precision is not a detector, it is a coin, and a
coin that cries wolf teaches the reader to switch the signal off. So a decision declares itself:

    ЗАПРЕТ ВЛАДЕЛЬЦА [ci]: CI не трогаем до подхода к релизу
    OWNER BAN [network]: no pushes to the public remote

Nothing else counts. The cost is that a prohibition must be written deliberately — which is the
point, because the owner saying it and the system knowing it are different events.

A SIGNAL, NOT A GATE. The owner's own word is what created the constraint, and the owner can lift
it; a block here would be argued with and then switched off, which is how the framework loses
rules. It prints, and the work continues.
"""

from __future__ import annotations

import re
from typing import Any, Final, NamedTuple

#: The marker, in both languages the project writes decisions in. The tag in brackets is what an
#: action point matches on, so `push-ok` can ask for `ci` or `network` without reading prose.
MARKER: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:ЗАПРЕТ\s+ВЛАДЕЛЬЦА|OWNER\s+BAN)\s*\[([a-z0-9,\- ]+)\]\s*:\s*(.+)",
    re.I | re.S,
)

#: SQL that finds them without reading the corpus. The LIKE runs against the same two prefixes,
#: so the cost is one indexed-ish scan rather than 399 rows parsed on every action.
#: A decision is retired by a `supersedes` EDGE, not by a status column — that is how this
#: project records a reversal, and a lifted constraint that kept printing would turn the signal
#: into noise, which is how signals get switched off.
_SQL: Final[str] = (
    "SELECT d.id, d.decision, d.created_at FROM decisions d "
    "WHERE (d.decision LIKE 'ЗАПРЕТ ВЛАДЕЛЬЦА [%' OR d.decision LIKE 'OWNER BAN [%') "
    "  AND NOT EXISTS ("
    "    SELECT 1 FROM memory_edges e "
    "     WHERE e.relation = 'supersedes' AND e.target_type = 'decision' "
    "       AND e.target_id = d.id AND e.valid_to IS NULL) "
    "ORDER BY d.id DESC"
)


class Ban(NamedTuple):
    id: int
    tags: tuple[str, ...]
    text: str

    def covers(self, tag: str) -> bool:
        return tag.lower() in self.tags


def parse(decision_text: str) -> tuple[tuple[str, ...], str] | None:
    """`(tags, text)` when the decision declares itself a prohibition, else None.

    Only the declaration counts. A decision that merely contains "не" is not a constraint: on
    this project's corpus that reading was right two times out of five.
    """
    m = MARKER.match(decision_text or "")
    if not m:
        return None
    tags = tuple(t.strip().lower() for t in m.group(1).split(",") if t.strip())
    return (tags, m.group(2).strip()) if tags else None


def active_bans(conn: Any, tag: str | None = None) -> list[Ban]:
    """Prohibitions in force, optionally only those covering ``tag``.

    A superseded decision is excluded: a constraint the owner lifted must stop printing, or the
    signal becomes noise and noise gets switched off — the failure this module exists against.
    """
    out: list[Ban] = []
    for row in conn.execute(_SQL).fetchall():
        parsed = parse(row[1])
        if not parsed:
            continue
        tags, text = parsed
        ban = Ban(int(row[0]), tags, text)
        if tag is None or ban.covers(tag):
            out.append(ban)
    return out


def advisory(bans: list[Ban]) -> str:
    """What the action point prints. Empty when there is nothing in force.

    Each line names the decision, so the reader can go and read the whole of it — and so that
    lifting it has an address rather than a conversation.
    """
    if not bans:
        return ""
    lines = ["ЗАПРЕТ ВЛАДЕЛЬЦА в силе — это СИГНАЛ, не ворота; снимает его сам владелец:"]
    lines += [f"  #{b.id} [{', '.join(b.tags)}] {b.text}" for b in bans]
    return "\n".join(lines)
