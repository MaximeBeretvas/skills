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

`scripts/ralph_loop.sh` runs a YAP plan folder step-by-step. Each `step_<n>_*.md`
is executed by a fresh `claude` session, verified against its own Verify
section, and committed before the next step runs. It stops on the first failure
so you can fix and resume.

Run it from inside the git repo whose plan you want to execute (the repo root is
taken from your current directory's git root):

```bash
# supervised (default): interactive session per step, you approve risky actions live
./scripts/ralph_loop.sh Docs/Plans/<name>

# resume from step n after fixing a failure
./scripts/ralph_loop.sh Docs/Plans/<name> --from 3

# override model / reasoning effort (defaults: sonnet / high)
./scripts/ralph_loop.sh Docs/Plans/<name> --model sonnet --effort high

# fully unattended: headless, auto-commit each step, aborts on any escalated action
./scripts/ralph_loop.sh Docs/Plans/<name> --headless
```

Requires the `claude` CLI and `jq`. Path to the script depends on your install
scope — e.g. `~/.claude/skills/YAP/scripts/ralph_loop.sh` for a global install.

Optional [`just`](https://github.com/casey/just) recipe — drop into your project's justfile:

```just
# Run a YAP plan folder step-by-step via the ralph loop
ralph plan *args:
    ~/.claude/skills/YAP/scripts/ralph_loop.sh {{plan}} {{args}}
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
