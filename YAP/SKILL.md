---
name: YAP
description: >
  Draft an implementation plan broken into independently verifiable vertical
  slices, get explicit approval, then save it to Docs/Plans/<name>/. Invoke
  by typing /YAP.
disable-model-invocation: true
---

# YAP (Yet Another Plan)

A plan that can't be checked step-by-step isn't a plan, it's a hope. Every
step this skill produces is a **vertical slice**: a change you can point at
and say "done" or "not done," in an order the agent can't jump ahead of.

## Steps

1. **Capture the goal.** Take the user's request as the goal statement.
   *Done when:* you can state the goal in 1-2 sentences without guessing.

2. **Enter plan mode.** Call `EnterPlanMode`. Everything through approval
   happens inside it. *Done when:* plan mode is active.

3. **Interview the user relentlessly** about every aspect of this plan until
   you reach a shared understanding. Walk down each branch of the design
   tree, resolving dependencies between decisions one-by-one. For each
   question, provide your recommended answer.

   Ask the questions one at a time, waiting for feedback on each question
   before continuing. Asking multiple questions at once is bewildering.

   If a fact can be found by exploring the codebase, look it up rather than
   asking. The decisions, though, are the user's — put each one to them and
   wait for their answer.

   Do not enact the plan until the user confirms you have reached a shared
   understanding. *Done when:* the user confirms the design tree is resolved.

4. **Delegate drafting to the Plan agent.** Spawn the `Plan` subagent with
   the goal and this exact output contract in the prompt:
   - Break the implementation into **vertical slices** — each step must be
     independently verifiable on its own, never split by task-type (e.g.
     never "write the code" as one step and "write the test" as another,
     where neither is checkable alone).
   - For each step, produce: a goal, concrete actions, a **blocking note**
     (which earlier step it depends on, or "none"), and a **verification**
     method that is a concrete, checkable command/query/output — never a
     vague "make sure it works."
   - Also produce: a short goal summary, and the list of files the
     implementation will touch with a one-line reason each.
   *Done when:* the Plan agent has returned a draft covering the goal
   summary, file list, and an ordered list of steps each with actions,
   blocking note, and verification.

5. **Present for approval via `ExitPlanMode`.** Show the full draft —
   goal, files, and every step with its verification. If the user requests
   changes, revise and present again through `ExitPlanMode`. Repeat until
   the response is an unambiguous approval. *Done when:* the user has
   explicitly approved the current draft, with no outstanding change
   requests. Never write files before this.

6. **Derive the plan name.** Auto-generate a kebab-case slug from the goal
   (e.g. `add-settlement-exposures`) and show it as part of the approved
   draft so the user can rename it before saving. *Done when:* you have a
   slug the user has not objected to.

7. **Resolve the output location.** Default to `Docs/Plans/<name>/` at the
   repo root. If the repo has no `Docs/` folder or its CLAUDE.md specifies a
   different plan-storage convention, ask the user where to save instead.
   If `Docs/Plans/<name>/` already exists, stop and ask the user whether to
   overwrite it (revising an existing plan) or pick a different name — never
   silently overwrite or auto-suffix. *Done when:* you have a confirmed,
   non-conflicting target folder.

8. **Write the files**, following [templates.md](references/templates.md)
   for exact structure:
   - `context.md` — goal summary + file list with reasons.
   - `plan_<name>.md` — approach + numbered links to each step file. Step
     detail lives in the step files, not duplicated here.
   - `step_<n>_<slug>.md` — one per step, each linking back to both
     `context.md` and `plan_<name>.md`, containing that step's blocking
     note, actions, and verification.
   *Done when:* every step from the approved draft has a corresponding
   file, and `plan_<name>.md`'s step list matches the step files exactly.

9. **Stop.** Report the saved file paths to the user. Do not begin
   implementing step 1 — implementation is a separate, later request.
   *Done when:* the file paths have been reported and no code has been
   changed.
