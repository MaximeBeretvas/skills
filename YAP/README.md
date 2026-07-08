# YAP (Yet Another Planning)

**YAP** stands for *Yet Another Planning*.

A planning skill for coding agents. It turns a request into an implementation
plan made of **vertical slices** — each step is a change you can point at and
call "done" or "not done" on its own, ordered so the agent can't skip ahead.

> A plan that can't be checked step-by-step isn't a plan, it's a hope.

## Invoke

Type `/YAP` in an agent that has the skill installed. (Model auto-invocation is
disabled — it only runs when you ask for it.)

## What it does

1. Captures the goal in a sentence or two.
2. Enters plan mode and interviews you one question at a time, resolving each
   design decision before moving on and looking up anything it can find itself.
3. Drafts the plan as vertical slices — each with a goal, concrete actions, a
   blocking note (what it depends on), and a concrete verification method.
4. Presents the draft for explicit approval before writing anything.
5. On approval, saves it to `Docs/Plans/<name>/` as `context.md`,
   `plan_<name>.md`, and one `step_<n>_<slug>.md` per step.
6. Stops — implementing the plan is a separate, later request.

The saved plan is designed to feed the **ralph loop** (below): hand the
vertical-sliced steps to an agent that works through them one verifiable slice
at a time.

## The ralph loop

`ralph_loop.sh` runs a YAP plan folder step-by-step. Each `step_<n>_*.md` is
executed by a fresh `claude` session, verified against its own Verify section,
and committed before the next step runs. It stops on the first failure so you
can fix and resume.

Two equivalent versions ship in `scripts/`:

- **`ralph_loop.sh`** — bash, for macOS / Linux / WSL / Git Bash. Requires the
  `claude` CLI and `jq`.
- **`ralph_loop.ps1`** — PowerShell, for Windows. Requires **PowerShell 7+**
  (`pwsh`), the `claude` CLI, and `jq`.

Both share `ralph_format.jq`. The scripts ship inside the skill, so installing
YAP installs the loop too — no separate download.

### Find the script

It lives at `<skills-dir>/YAP/scripts/ralph_loop.sh`, where `<skills-dir>`
depends on the agent and install scope you chose:

| Agent / scope | Path |
| ------------- | ---- |
| Claude Code, project | `.claude/skills/YAP/scripts/ralph_loop.sh` |
| Claude Code, global (`-g`) | `~/.claude/skills/YAP/scripts/ralph_loop.sh` |
| Cursor, global | `~/.cursor/skills/YAP/scripts/ralph_loop.sh` |
| other agents | see the [supported-agents table](https://github.com/vercel-labs/skills#supported-agents) |

If unsure, `npx skills list` shows what's installed, or run
`find ~ -path '*/YAP/scripts/ralph_loop.sh' 2>/dev/null`.

### Run it

Run from inside the git repo whose plan you want to execute (the repo root is
taken from your current directory's git root). Substitute your own script path
for `RALPH` below; running it via `bash` avoids any executable-bit issues from
the install:

```bash
RALPH=~/.claude/skills/YAP/scripts/ralph_loop.sh

# supervised (default): interactive session per step, you approve risky actions live
bash "$RALPH" Docs/Plans/<name>

# resume from step n after fixing a failure
bash "$RALPH" Docs/Plans/<name> --from 3

# override model / reasoning effort (defaults: sonnet / high)
bash "$RALPH" Docs/Plans/<name> --model sonnet --effort high

# fully unattended: headless, auto-commit each step, aborts on any escalated action
bash "$RALPH" Docs/Plans/<name> --headless
```

### Run it on Windows (PowerShell)

Same behaviour, PowerShell-native flags (`-From`, `-Model`, `-Effort`,
`-Headless` instead of `--from` etc.). Run from PowerShell 7+ (`pwsh`) inside
the git repo whose plan you want to execute:

```powershell
$RALPH = "$HOME/.claude/skills/YAP/scripts/ralph_loop.ps1"

# supervised (default)
& $RALPH Docs/Plans/<name>

# resume from step n
& $RALPH Docs/Plans/<name> -From 3

# override model / reasoning effort (defaults: sonnet / high)
& $RALPH Docs/Plans/<name> -Model sonnet -Effort high

# fully unattended
& $RALPH Docs/Plans/<name> -Headless
```

If PowerShell blocks the script, allow local scripts once with
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Vendor it into a project

To keep the loop with a specific project instead of calling it from the global
skills dir, run the bundled installer from your project root — it copies both
scripts into a folder you name (default `./scripts`):

```bash
# copies ralph_loop.sh + ralph_format.jq into ./scripts
bash ~/.claude/skills/YAP/scripts/install_ralph.sh

# or choose the target folder
bash ~/.claude/skills/YAP/scripts/install_ralph.sh Scripts
```

After that the loop is self-contained in the project (the jq formatter is
resolved next to the script), so you can commit it and run
`bash scripts/ralph_loop.sh Docs/Plans/<name>`.

On Windows, use the PowerShell installer instead:

```powershell
& "$HOME/.claude/skills/YAP/scripts/install_ralph.ps1"
```

It copies `ralph_loop.ps1` + `ralph_format.jq` into `./scripts` (or a target you
pass), then run `& ./scripts/ralph_loop.ps1 Docs/Plans/<name>`.

### `just` recipe

Optional [`just`](https://github.com/casey/just) recipe — drop into your
project's justfile, adjusting the path to match your install location (or point
it at the vendored `./scripts` copy):

```just
# Run a YAP plan folder step-by-step via the ralph loop
ralph plan *args:
    bash ~/.claude/skills/YAP/scripts/ralph_loop.sh {{plan}} {{args}}
```

Then `just ralph Docs/Plans/<name>`.

## Acknowledgements

YAP is strongly inspired by **Matt Pocock's "grill me" skill** and his
planning workflow. The relentless one-question-at-a-time interview and the
insistence on independently checkable steps come directly from that approach.

- Repo: [mattpocock/skills](https://github.com/mattpocock/skills)
- The skill: [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)

## Install

```bash
npx skills add MaximeBeretvas/skills --skill YAP
```

Or via the Claude Code marketplace — see the [repo README](../README.md).
