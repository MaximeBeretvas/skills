# skills

Personal agent skills by [Maxime Beretvas](https://github.com/MaximeBeretvas).

Installable two ways: with the [`skills`](https://github.com/vercel-labs/skills)
CLI (works across Claude Code, Cursor, Codex, and 60+ other agents), or as a
[Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).

## Skills

| Skill | What it does |
| ----- | ------------ |
| **YAP** | Draft an implementation plan broken into independently verifiable vertical slices, get explicit approval, then save it to `Docs/Plans/<name>/`. Invoke by typing `/YAP`. |
| **hexcavator** | Excavate a Hex report app into a data-engineer blueprint — the story it tells, its metrics/KPIs, a recommended fact/dim mart architecture, a Mermaid ER diagram, and table schemas mapped to existing dbt staging models — saved to `Docs/Blueprints/<app>/`. Invoke by typing `/hexcavator`. |

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
