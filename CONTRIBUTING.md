# Contributing

Maintainer notes for this repo.

## Adding a new skill

1. Create a folder at the repo root containing a `SKILL.md` (see `YAP/` as a template).
2. Add its path to the `skills` array in **both** `.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json`.
3. Add a row to the skills table in [README.md](README.md).
4. Validate with `claude plugin validate .`, then commit and push.
