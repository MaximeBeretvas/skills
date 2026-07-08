# YAP (Yet Another Plan)

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

The saved plan is designed to feed **Matt Pocock's "ralph loop"** workflow:
hand the vertical-sliced steps to an agent that works through them one
verifiable slice at a time.

## Acknowledgements

YAP is strongly inspired by **Matt Pocock's "grill me" skill** and his
planning workflow. The relentless one-question-at-a-time interview and the
insistence on independently checkable steps come directly from that approach.

## Install

```bash
npx skills add MaximeBeretvas/skills --skill YAP
```

Or via the Claude Code marketplace — see the [repo README](../README.md).
