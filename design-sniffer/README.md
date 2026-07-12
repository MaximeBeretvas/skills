# design-sniffer

Sniff a live website's **real rendered styles** and turn them into a validated,
schema-compliant `DESIGN.md` — the [google-labs-code/design.md](https://github.com/google-labs-code/design.md)
format for describing a visual identity to coding agents.

> Every token traces to a style the browser actually rendered — or to something
> you explicitly asked for. Nothing is guessed.

## Install

```bash
npx skills add MaximeBeretvas/skills --skill design-sniffer
```

Or via the Claude Code marketplace — see the [repo README](../README.md).

## Invoke

Type `/design-sniffer` in an agent that has the skill installed. (Model
auto-invocation is disabled — it only runs when you ask for it.)

## Requirements

- **Claude in Chrome** — the only reliable way to read *computed* styles.
  Modern sites (Tailwind, CSS-in-JS, JS-loaded fonts) expose almost nothing
  useful in raw HTML, so the skill drives a real browser and reads
  `getComputedStyle`. Without a connected browser it stops rather than guess.
- **Node / npx** — to run the official validator.

## What it does

1. Asks a short, bounded checklist only for what isn't already given: the URL,
   scope (full system vs specific parts), which subpages matter, and whether an
   existing `DESIGN.md` should be updated. No taste or strategy questions.
2. **Sniffs** the homepage plus up to 3 representative subpages in Chrome,
   reading `getComputedStyle` on headings, body, buttons, links, cards and
   inputs to pull the real font families/sizes/weights, colors, corner radius
   and spacing rhythm. Captures the default theme; only asks about light/dark
   when a real toggle exists.
3. Drafts `DESIGN.md` strictly to the bundled schema — YAML tokens plus prose
   sections in canonical order, no invented styles, no extra sections.
4. **Validates for real** with `npx @google/design.md lint`, fixing until the
   linter reports zero errors. Schema-compliance is the tool's verdict, not a
   judgment call.
5. Shows you a plain-language summary (palette, fonts, radius, spacing, lint
   result) and the file, and iterates relentlessly on anything you reject —
   re-sniffing the site for the affected tokens rather than guessing — until you
   approve.

On approval it writes `DESIGN.md` to your selected folder.

## Updating an existing DESIGN.md

Point the skill at a folder that already has a `DESIGN.md` and tell it what to
change. It reads the file, asks targeted questions, re-sniffs the site for only
the affected tokens, applies surgical edits, re-lints to zero errors, and shows
a before/after of exactly which tokens moved — leaving everything you already
approved untouched.

## The design.md format

`DESIGN.md` combines machine-readable design tokens (YAML front matter:
`colors`, `typography`, `rounded`, `spacing`, `components`) with human-readable
rationale (markdown sections). The canonical spec is bundled at
[`references/spec.md`](references/spec.md) and validated by the
[`@google/design.md`](https://www.npmjs.com/package/@google/design.md) CLI.

> **Note.** `npx @google/design.md spec` is currently broken upstream (it can't
> locate its own bundled `spec.md`), which is why this skill ships the spec
> locally. The `lint` command — the part that guarantees compliance — works
> fine.
