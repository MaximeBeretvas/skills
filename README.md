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
