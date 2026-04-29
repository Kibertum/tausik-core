**English** | [Русский](../ru/quickstart.md)

# Quick Start

TAUSIK — **T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge.

Step-by-step guide: from zero to your first task with an AI agent.
Takes 10-15 minutes. No prior experience with AI tools required.

---

## Step 0. What You'll Need

Make sure the following are installed on your computer:

1. **Python 3.11 or newer**
   - Windows: download from [python.org](https://www.python.org/downloads/), check "Add to PATH" during installation. Alternative: `winget install Python.Python.3.13`
   - macOS: `brew install python@3.13`
   - Linux (Ubuntu/Debian): `sudo apt install python3.13` · Fedora: `sudo dnf install python3.13`
   - Verify: open a terminal and type `python --version` (should show 3.11+)
   - Bootstrap will automatically create an isolated virtual environment (`.tausik/venv/`) and install all required dependencies. Your system Python will not be modified. If a suitable Python is not found, bootstrap will show download instructions.

2. **Git**
   - Windows: download from [git-scm.com](https://git-scm.com/downloads)
   - macOS: `brew install git`
   - Linux: `sudo apt install git`
   - Verify: `git --version`

3. **Visual Studio Code**
   - Download from [code.visualstudio.com](https://code.visualstudio.com/)

4. **AI IDE — one of the following:**
   - **Claude Code** — VSCode extension or CLI: `npm install -g @anthropic-ai/claude-code`
   - **Cursor** — download from [cursor.com](https://cursor.com)
   - **Qwen Code (GigaCode)** — install from [qwen.ai/qwencode](https://qwen.ai/qwencode)
   - **Windsurf** — download from [windsurf.com](https://windsurf.com)
   - You'll need an API key or subscription for your chosen IDE

## Step 1. Create a Repository

Go to [github.com](https://github.com) (or GitLab, Bitbucket — any Git hosting).

1. Click **New Repository**
2. Name it, for example: `my-project`
3. Check "Add a README file"
4. Click **Create Repository**

Now clone the repository to your computer:

```bash
git clone https://github.com/your-username/my-project.git
cd my-project
```

> If you already have a project — skip this step and navigate to your project folder.

## Step 2. Connect TAUSIK

> **Already have a project with code?** See [Migrating an Existing Project](#migrating-an-existing-project) below — TAUSIK merges into your setup without overwriting anything.

There are two ways — tell your AI agent, or do it manually. We recommend the first.

### Option A: Tell your agent (easiest)

Open your project in the IDE, open your AI agent (Claude Code, Cursor, Qwen Code, Windsurf) and write:

```
Add https://github.com/Kibertum/tausik-core as a git submodule in .tausik-lib,
run python .tausik-lib/bootstrap/bootstrap.py --init,
add .tausik/ to .gitignore
```

The agent will execute all three steps — you just confirm its actions.

### Option B: Manually via terminal

If you prefer doing everything by hand:

```bash
# Connect TAUSIK as a Git submodule
# (A submodule is a reference to another Git repository inside yours —
#  it keeps TAUSIK's code linked but separate from your project)
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib

# Run bootstrap (one command does everything)
# Project name is auto-derived from the directory name
python .tausik-lib/bootstrap/bootstrap.py --init

# Add working data to .gitignore
echo ".tausik/" >> .gitignore
```

### Restart Your IDE

**After bootstrap, restart your IDE window** (Claude Code, Cursor, Qwen Code, Windsurf). Bootstrap generates project MCP configs (`.mcp.json` for Claude ecosystem and `.cursor/mcp.json` for Cursor), but IDEs load them only on startup. Without restart, the agent may fall back to CLI mode instead of using MCP tools.

> **Qwen Code users:** Bootstrap also creates `.qwen/settings.json` with MCP config and `QWEN.md` with project instructions. Use `--ide qwen` if you only use Qwen Code, or `--ide all` for multi-IDE setups.

### What Happens After Bootstrap

Regardless of which option you chose — the result is the same:

- A `.tausik/` folder appears — database, scripts, configuration
- A `.claude/` folder appears — skills and settings for Claude Code
- A `CLAUDE.md` file appears — instructions for the AI agent
- TAUSIK detects your project's stack (Python, React, Go, etc.) and enables appropriate checks

**Two directories to understand:**

- **`.tausik-lib/`** — the framework source code (git submodule, tracked in version control). This is TAUSIK itself.
- **`.tausik/`** — runtime data: database, config, virtual environment. Added to `.gitignore` — this is local working data, never committed.

Team members who clone the repo just need to run `git submodule update --init` to get the framework, then `python .tausik-lib/bootstrap/bootstrap.py --smart` to set up their local `.tausik/`.

`.claude/` and `CLAUDE.md` — keep these under version control. These are instructions
for the agent, they should be in the repository.

## Step 3. Verify Installation

```bash
.tausik/tausik status
```

> **Windows note:** This command requires Git Bash or WSL. If you're using cmd.exe or PowerShell, run `python .tausik/scripts/project.py status` instead.

If you see something like:

```
Tasks: 0/0 done
Session: none
Epics: 0
```

Everything is working. TAUSIK is ready.

## Step 4. Open the Project in VSCode

```bash
code .
```

VSCode will open with your project. In the side panel or at the bottom you'll see
Claude Code — a chat with the AI agent.

If Claude Code doesn't appear — check that the extension is installed (Ctrl+Shift+X → "Claude Code").

## Step 5. Start a Session

Write in the Claude Code chat:

```
start working
```

The agent will open a session, show the project status, and suggest what to work on.
On the first run the project is empty — that's normal.

## Step 6. Create Your First Task

Simply describe what needs to be done, in your own words:

```
create a landing page with the title "My Project" and a "Get Started" button
```

The agent will:
1. Create a task in the database
2. Formulate a goal and acceptance criteria (what counts as "done")
3. Start working — write code, create files

You'll see the agent working: creating files, writing code, verifying everything works.
You can intervene at any time — provide clarification, ask to change the approach.

## Step 7. Complete the Task

When the agent finishes (or you decide the result is satisfactory), write:

```
done, ship it
```

The agent will:
1. Check the code — run tests, linters, quality gates
2. Verify that the acceptance criteria are met
3. Close the task
4. Offer to commit the changes

Answer "yes" to the commit offer — and your first task is complete.

## Step 8. Wrap Up

When you're done working for the day:

```
that's all for today
```

The agent will save context: what was done, what's unfinished, what decisions were made.
Next time you say "start working" — the agent will load this context
and continue from where you left off.

---

## Full Work Cycle

Here's what typical work with TAUSIK looks like after setup:

```
You: "start working"                          → agent opens a session
You: "fix the bug — form doesn't submit"      → agent creates a task, starts
    ... agent works ...
You: "done, ship it"                          → agent verifies, commits
You: "one more — add email validation"        → next task
    ... agent works ...
You: "done, ship it"                          → verify, commit
You: "that's all for today"                   → agent saves context
```

Two or three messages per task. Everything else — automatic.

---

## Troubleshooting

**"command not found: .tausik/tausik"**
- On Windows use Git Bash or WSL, not cmd.exe
- Or call directly: `python .tausik/scripts/project.py status`

**"Python not found"**
- Make sure Python is in PATH: `python --version`
- On some systems the command is `python3`

**"Claude Code doesn't see skills"**
- Restart VSCode after bootstrap
- Make sure `.claude/` is created and not empty

**"Database is locked"**
- Delete the file `.tausik/tausik.db-wal` and try again
- This happens if a previous process terminated incorrectly

**Agent doesn't create tasks, just writes code**
- Check that `CLAUDE.md` exists in the project root
- Check that it contains a "Constraints" section with the "No code without a task" rule

---

## Migrating an Existing Project

If you already have a project with code and want to add TAUSIK:

1. **Navigate to your project root** and connect TAUSIK as a submodule:
   ```bash
   git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
   python .tausik-lib/bootstrap/bootstrap.py --init
   ```

2. **Bootstrap auto-detects your environment:**
   - Recognizes your stack (Python, React, Go, etc.) and enables matching quality gates
   - Detects existing config files (`.eslintrc`, `pyproject.toml`, etc.)
   - Preserves your existing `.gitignore`, `CLAUDE.md`, `.mcp.json`, and `.cursor/mcp.json` — merges instead of overwriting

3. **What gets tracked in git:**
   - `.tausik-lib/` — the framework itself (git submodule, tracked)
   - `.tausik/` — runtime data (database, config, venv) — added to `.gitignore`, never committed
   - `.claude/` and `CLAUDE.md` — agent instructions, tracked

4. **Starting fresh vs. importing:**
   - TAUSIK starts with a clean task database. There is no automatic import from other systems.
   - If you have existing tasks, create them manually with `task quick "title"` or plan them with `/plan`.
   - Your code history stays in git — TAUSIK only manages the AI workflow layer on top.

After setup, verify with `.tausik/tausik status` and start working normally.

---

## What's Next

You've mastered the basic cycle. Next you can learn more about:

- **[Workflow](workflow.md)** — quick and full modes, quality gates, memory
- **[Skills](skills.md)** — all phrases the agent understands
- **[CLI Commands](cli.md)** — if you want to call TAUSIK from the terminal directly
