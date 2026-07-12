---
name: design-sniffer
description: >
  Sniff a live website's real rendered styles and produce a validated,
  schema-compliant DESIGN.md (the google-labs-code/design.md format). Invoke
  by typing /design-sniffer.
disable-model-invocation: true
---

You **sniff** a website: you read the styles the browser actually renders, never
the styles you'd guess. Every token in the output traces to a value you
observed on the live site or a value the user explicitly gave you. No invented
colors, fonts, or spacing. No sections the schema doesn't define.

The output is a `DESIGN.md` in the [google-labs-code/design.md](https://github.com/google-labs-code/design.md)
format. The canonical schema is bundled at [`references/spec.md`](references/spec.md) —
read it before drafting. Correctness is not your judgment call: the official
linter (`npx @google/design.md lint`) is the arbiter, and the file is not done
until it reports **zero errors**.

## Step 1 — Mode and checklist

Determine whether this is a **new** file or an **update** to an existing one
(the user tells you, or you find a `DESIGN.md` in the folder). For an update,
go to Step 6.

For a new file, ask only what isn't already answered, and only these — nothing
about branding strategy, roadmap, or taste:

- The target URL (required — stop until you have it).
- Scope: the full system, or only some parts (colors only, typography only, …)?
- Which subpages matter, if the user has a preference (else you pick).
- Whether an existing `DESIGN.md` should be updated instead.

Skip any question whose answer is already given or observable on the site. Ask
the rest in one short batch, then proceed. Do not interrogate — the relentless
questioning happens later, in the validation loop.

## Step 2 — Sniff the site

The only reliable source of real tokens is **computed style** in a rendered
browser. Raw HTML/CSS lies on modern sites (Tailwind, CSS-in-JS, JS-loaded
fonts). Use Claude in Chrome.

Load the browser tools in one call:

```
ToolSearch "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__read_page"
```

If no browser is connected, tell the user Chrome is required for this skill and
stop — do not fall back to raw-HTML guessing.

Navigate the homepage plus **up to 3** representative subpages (an article/detail
page, a form/interactive page, a listing page — whatever the site has). On each,
run `javascript_tool` to read `getComputedStyle` on representative elements and
report back the raw values. Probe at least:

- Typographic scale: `h1, h2, h3, h4, p, a, button, blockquote, small, code` —
  capture `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`.
- Colors: text color and background color of `body`, headings, primary buttons,
  links (default and, where reachable, `:hover`), cards/surfaces, borders.
- Shape and spacing: `borderRadius` on buttons/cards/inputs; padding/margins and
  gaps that reveal the spacing rhythm (look for a repeated base like 4px/8px).

Capture the theme the site renders **by default** (usually light). Only if a
distinct alternate theme (a working dark/light toggle) exists do you ask the
user which theme to encode. Collapse near-duplicate observed values into a
coherent scale; record the actual hexes and px/rem values as you saw them.

Completion criterion: for every token group you intend to emit, you hold at
least one real observed value. Anything you couldn't observe stays out — it does
not get guessed.

## Step 3 — Draft DESIGN.md

Read [`references/spec.md`](references/spec.md), then draft the file strictly to
it:

- YAML front matter with the token groups you have evidence for (`colors`,
  `typography`, `rounded`, `spacing`, `components`), plus `name`.
- Markdown body sections in the canonical order only: Overview, Colors,
  Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts.
  Omit any section you have no evidence for; never add a section the spec
  doesn't define.
- Component `backgroundColor`/`textColor` should reference color tokens
  (`{colors.primary}`) so the linter can check them and contrast.
- Prose describes what you observed; it does not editorialize beyond the site.

Write the draft to a scratch path first (not the user's folder yet).

## Step 4 — Lint until clean

Run the official linter in the sandbox:

```
npx -y @google/design.md lint <path-to-draft>
```

Read the JSON. Fix every `error`, and every `warning` you can honestly fix from
observed data (broken refs, section order, missing primary/typography, low
contrast). Re-run until `summary.errors` is `0`. Leave a warning unfixed only
when fixing it would require inventing a value — and note that to the user.

(`npx @google/design.md spec` is currently broken upstream, which is why the
schema is bundled locally. The `lint` command works and is authoritative.)

## Step 5 — Validate with the user

Show a plain-language summary — the palette with hex swatches described, the
font families and scale, radius and spacing rhythm, and the linter result
(errors/warnings) — plus the file itself.

Ask the user to approve. If they don't, this is where you are relentless: pin
down exactly what's wrong, re-sniff the site for only the affected tokens (never
guess a replacement), apply the change, re-lint to zero errors, and show the
summary again. Repeat until they approve.

On approval, write `DESIGN.md` to the user's selected folder and present it as a
card.

## Step 6 — Update an existing DESIGN.md

Read the existing file. Ask specifically what should change — one targeted
question set, not a re-interview. For each requested change, re-sniff the site
for only the affected tokens (a request like "make the accent match the real
button colour" is answered from the live site, not from memory). Apply just
those edits; leave every already-approved token untouched. Re-lint to zero
errors. Show a **before/after** of exactly which tokens moved, then Step 5's
approval loop.

## Constraints

- Every value comes from an observed computed style or an explicit user
  instruction. If you cannot source a value, omit it.
- Emit only schema-defined sections and token groups. Unknown sections are not
  invented.
- The file ships only after `npx @google/design.md lint` reports zero errors.
