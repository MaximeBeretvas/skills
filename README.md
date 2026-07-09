# skills

Personal agent skills by [Maxime Beretvas](https://github.com/MaximeBeretvas).

Installable two ways: with the [`skills`](https://github.com/vercel-labs/skills)
CLI (works across Claude Code, Cursor, Codex, and 60+ other agents), or as a
[Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).

## Skills

| Skill | What it does |
| ----- | ------------ |
| **YAP** | Draft an implementation plan broken into independently verifiable vertical slices, get explicit approval, then save it to `Docs/Plans/<name>/`. Then run the bundled loop script to execute it. Invoke by typing `/YAP`. |
| **hexcavator** | Excavate a Hex report app into a data-engineer blueprint — the story it tells, its metrics/KPIs, a recommended fact/dim mart architecture, a Mermaid ER diagram, and table schemas mapped to existing dbt staging models — saved to `Docs/Blueprints/<app>/`. Invoke by typing `/hexcavator`. |

### YAP: plan, then execute

YAP is two phases. First, `/YAP` produces a plan folder at `Docs/Plans/<name>/`
containing a `context.md` and one `step-<n>-*.md` file per vertical slice, each
with its own Verification section.

Second, a bundled Python script, `YAP/scripts/ralph_loop.py`, walks that folder
and runs the plan step by step: it launches a fresh `claude` session for each
`step-<n>-*.md`, has it complete and verify that step, then moves to the next —
stopping on the first failure so you can fix and resume.

**Why it works this way.** A big plan is broken into smaller, testable,
validatable steps so that each one runs in a *fresh* `claude` context window.
That prevents context rot — the degradation you get when one long session
accumulates a bloated, noisy context — and uses the context window far more
efficiently, since each step only carries what that step actually needs.

The script (`ralph_loop.py`) takes its inspiration from Geoffrey Huntley's
[Ralph loop](https://ghuntley.com/ralph/): run an agent in a loop where each
iteration gets a fresh context window and does exactly one task, using files on
disk rather than conversation history as memory. This version swaps the
open-ended loop for an explicit, ordered set of pre-planned, individually
verifiable steps.

```bash
# Run a plan (from inside the target repo)
python YAP/scripts/ralph_loop.py Docs/Plans/<name>/

# Resume from a specific step, or run fully unattended
python YAP/scripts/ralph_loop.py Docs/Plans/<name>/ --from 3
python YAP/scripts/ralph_loop.py Docs/Plans/<name>/ --headless
```

Requires the `claude` CLI and Python 3.8+. By default each step runs as a real
interactive `claude` session (you confirm success); `--headless` switches to
unattended `claude -p` with a parsed pass/fail signal.

#### Running a plan interactively (default)

By default the script drives Claude Code in **interactive mode**, one step at a
time:

1. The script launches a `claude` session pointed at the current
   `step-<n>-*.md`. Claude carries out the step, runs the step's own
   Verification section, and prints a **success or failure** message.
2. When the step is done, you close the Claude Code session (`Ctrl+C`, or
   `/exit`).
3. The script then asks `Mark this step successful and continue? [y/N]`. Answer
   `y` and it commits the step's changes and automatically launches the next
   step; anything else stops the run so you can fix and resume with
   `--from <n>`.

Interactive mode is the default because it lets Claude Code's permission prompts
actually reach you (approve/deny) instead of aborting — use `--headless` only
when you want it fully unattended.

#### Running a plan fully AFK (`--headless`)

`--headless` runs each step unattended inside a [Docker
sandbox](https://docs.docker.com/ai/sandboxes/) (`docker sandbox run claude`,
requires Docker Desktop 4.50+). The sandbox mounts only the repo, so a runaway
agent can't touch your home directory, SSH keys, or system files — the safety
net that makes AFK runs sane. Inside it, Claude runs with
`--permission-mode acceptEdits` so edits don't stall the loop, and the script
parses a JSON success/failure signal per step. Inspired by the [Ralph
loop](https://ghuntley.com/ralph/) and Matt Pocock's
[Getting Started With Ralph](https://www.aihero.dev/getting-started-with-ralph):
if a step reports the whole plan is already done, it emits
`<promise>COMPLETE</promise>` and the loop stops early.

```bash
python YAP/scripts/ralph_loop.py Docs/Plans/<name>/ --headless
```

> **Caveat.** A sandbox mounts only the repo, so your **global** `AGENTS.md` and
> user-level skills won't load (project skills committed in the repo still do).
> You'll authenticate Claude in the sandbox on first run; credentials persist in
> a Docker volume.

## Install with `npx skills`

```bash
# Install every skill in this repo
npx skills add MaximeBeretvas/skills

# Or pick specific skills
npx skills add MaximeBeretvas/skills --skill YAP

# List what's available without installing
npx skills add MaximeBeretvas/skills --list
```

## Install as a Claude Code plugin marketplace

```
/plugin marketplace add MaximeBeretvas/skills
/plugin install maxime-skills@maxime-skills
```

## License

MIT — see [LICENSE](LICENSE).
