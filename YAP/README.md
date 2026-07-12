# YAP (Yet Another Planning)

**YAP** stands for *Yet Another Planning*.

A planning skill for coding agents. It turns a request into an implementation
plan made of **vertical slices** — each step is a change you can point at and
call "done" or "not done" on its own, ordered so the agent can't skip ahead.

> A plan that can't be checked step-by-step isn't a plan, it's a hope.

## Install

```bash
npx skills add MaximeBeretvas/skills --skill YAP
```

Or via the Claude Code marketplace — see the [repo README](../README.md). To
run the plans this skill produces, install the separate
[ralph-loop-install](../ralph-loop-install/SKILL.md) skill.

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

`ralph_loop.py` runs a YAP plan folder step-by-step. Each `step_<n>_*.md`
is executed by a fresh `claude` session, verified against its own Verification
section, and committed before the next step runs. It stops on the first failure
so you can fix and resume.

It's a single cross-platform script (macOS / Linux / Windows) — requires
**Python 3.8+** and the `claude` CLI, nothing else (stdlib only). It ships with
the separate [ralph-loop-install](../ralph-loop-install/SKILL.md) skill, not
with YAP — install that skill too, or ask it to vendor the script into this
repo's `scripts/` folder. See the [repo README](../README.md#yap-plan-then-execute)
for exact run commands, headless mode, and the optional `just` recipe.

## Acknowledgements

YAP is strongly inspired by **Matt Pocock's "grill me" skill** and his planning
workflow. The relentless one-question-at-a-time interview and the insistence on
independently checkable steps come directly from that approach. The ralph loop
above follows the same workflow: run each planned slice, verify it, then move on.

- Matt Pocock's skills repo: [mattpocock/skills](https://github.com/mattpocock/skills)
- The "grill me" skill: [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)
