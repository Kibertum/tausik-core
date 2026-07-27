---
slug: bootstrap-deploy-fix
title: "Fix bootstrap — deploy core skills + smoke-test from clean clone"
status: done
epic: v13-mcp-and-discipline
---

CRITICAL BLOCKER discovered in session #36: 9 of 15 core skills (review, brain, commit, debug, interview, markitdown, ship, skill-test, test) exist in agents/skills/ but are NOT copied to .claude/skills/ by bootstrap. /review fires bundled Claude Code skill instead of TAUSIK's 6-agent pipeline. Must close before Story 4 (qd-1 multi-agent review) runs.
