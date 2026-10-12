"""How a write-target list was arrived at — shared by every dialect parser.

Consumers have DIFFERENT costs of error, so the parsers state their confidence
instead of each consumer re-deriving it:

* PARSED — the command tokenized; a target here was found structurally.
* REGEX_FALLBACK — the command did NOT tokenize (unbalanced quotes, a heredoc
  body carrying a lone quote), so a regex guessed. It deliberately
  over-detects, and its "paths" can be visible garbage.

For QG-0 an over-detection is cheap: the worst case asks for a task the write
would have needed anyway. For a guard whose block message accuses the agent of
leaking knowledge, and whose only escapes are an untrue marker or a permanent
config exemption, a false positive is expensive — it trains the bypass.

These live in their own module because BOTH shell dialects must speak the same
vocabulary and neither may import the other: `bash_write_parse` and
`pwsh_write_parse` are siblings, and routing the constants through either one
would make them mutually dependent. Two copies of two strings would work right
up until someone changed one of them.
"""

from __future__ import annotations

CONFIDENCE_PARSED = "parsed"
CONFIDENCE_REGEX_FALLBACK = "regex_fallback"
