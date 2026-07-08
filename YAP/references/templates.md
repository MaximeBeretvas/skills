# File templates

## context.md

```markdown
# <Plan Title>

## Goal

<2-4 sentences: what this plan achieves and why>

## Files involved

- `<path/to/file>` — <one line: why this file matters to the plan>
- `<path/to/file>` — <one line: why this file matters to the plan>
```

## plan_<name>.md

```markdown
# <Plan Title>

See [context.md](context.md) for the goal and files involved.

## Approach

<short paragraph: overall strategy, key decisions, trade-offs>

## Steps

1. [<step title>](step_1_<slug>.md)
2. [<step title>](step_2_<slug>.md)
3. [<step title>](step_3_<slug>.md)
```

## step_<n>_<slug>.md

```markdown
# Step <n>: <title>

Context: [context.md](context.md) · Plan: [plan_<name>.md](plan_<name>.md)

## Blocked by

<"None — can start immediately" OR "Step <k> — requires <what> to exist first">

## Goal

<1-2 sentences: what this step accomplishes, standalone>

## Actions

- <concrete action>
- <concrete action>

## Verification

<exact command to run, query to execute, or file/output to inspect, plus
the expected result that proves this step is done>
```
