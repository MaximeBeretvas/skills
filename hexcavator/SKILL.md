---
name: hexcavator
description: >
  Excavate a Hex report app into a data-engineer blueprint: the story it
  tells, its metrics/KPIs, a recommended fact/dim mart architecture, a
  Mermaid ER diagram, table schemas mapped to existing dbt staging models,
  and the legacy BigQuery lineage behind anything not yet in dbt. Invoke by
  typing /hexcavator.
disable-model-invocation: true
---

# Hexcavator

A Hex app built without dbt is a pile of ad-hoc SQL. Hexcavator digs the
**blueprint** out of it: one markdown document a data engineer uses to
rebuild the app's data layer as proper dbt intermediate and mart models on
top of the existing staging layer. The skill produces the blueprint only —
it never writes dbt model files.

Every mapping the blueprint asserts must trace to a staging model that
actually exists. A cited column that can't be found is not a mapping — it's a
**data gap**, and belongs in section 6, not section 5.

## Input

One Hex export yaml under `Hex/<app>/<app>.yaml` in the target dbt repo. If
the user didn't name one, list the `Hex/` subfolders and ask which app.

## Steps

1. **Render the Hex export.** Run the bundled parser on the target yaml:
   `uv run <skill-dir>/scripts/hex_yaml_compact.py <path-to-hex.yaml>`
   (raw exports run to hundreds of KB of UI noise — never read them
   directly). *Done when:* you have the compact markdown of every cell.

2. **Mine the app.** From the compact output, extract: the narrative the app
   tells (what question it answers, for whom), the metrics/KPIs it computes
   or displays (name + formula/definition), and every source table and
   column its SQL cells read from. *Done when:* you can name the app's story,
   its KPI list, and its source columns without rereading.

3. **Inventory the staging layer.** Get the existing staging models and their
   columns via the dbt MCP (`get_all_models`, then `get_model_details` on the
   `stg_` models). If the dbt MCP is unavailable, read the staging
   `schema.yml` files and `.sql` under `models/staging/`. *Done when:* you
   have a name+column list for each staging model the app could draw on.

4. **Design the marts.** Map the app's needs onto a star schema: fact
   table(s) at a stated grain, dimension table(s) for the entities. Follow
   the repo's naming (`fct_`, `dim_`, `int_` for intermediates). For each
   recommended column, record which staging model+column it derives from.
   Anything the app needs that no staging model supplies goes on the
   data-gaps list. *Done when:* every recommended column is either mapped to
   a staging source or flagged as a gap.

5. **Trace the external BigQuery lineage.** Do this only if step 4 flagged
   sources the app reads directly from BigQuery (raw tables/views, not dbt
   models) — the legacy pipeline that lives outside dbt. Reconstruct where
   that data comes from, using the BigQuery MCP:
   1. List the fully-qualified external tables/views the Hex SQL selects from
      (`project.dataset.table`).
   2. For each, call `get_table_info` for its type and, if it's a view, its
      SQL definition (or query `INFORMATION_SCHEMA.VIEWS` via `execute_sql`).
   3. If it's a view, extract the tables/views its definition reads from and
      repeat step 2 on each — recurse until you reach base tables (no upstream)
      or a node already seen.
   4. Record each `upstream → downstream` edge, plus the key columns the Hex
      app pulls from each node (inferred from the Hex SQL).
   This lineage is legacy and considered bad — documented only to understand
   the app's current data flow, never a target to reproduce. If the BigQuery
   MCP is unavailable, list the raw external tables and note the lineage
   couldn't be resolved. *Done when:* every external source resolves down to
   base tables, with no unresolved view left in the graph.

6. **Write the blueprint** to `Docs/Blueprints/<app>/blueprint.md` with these
   sections, in order:
   1. **Story** — what the app tells and for whom, in a short paragraph.
   2. **Metrics & KPIs** — each metric with its definition/formula.
   3. **Recommended mart architecture** — the fact and dimension tables,
      each with its grain and one-line purpose.
   4. **ER diagram** — a Mermaid `erDiagram` of the recommended tables and
      their relationships (PK/FK, cardinality).
   5. **Table schemas** — per recommended model, a column table:
      `column | type | description | source (stg model.column)`.
   6. **Data gaps & open questions** — needed fields/grain no staging model
      provides, plus grain or definition assumptions the engineer must
      confirm.
   7. **External BigQuery lineage (legacy — to be replaced)** — a Mermaid
      `flowchart LR` of the raw BigQuery table/view dependencies from step 5,
      base tables up to what the Hex SQL reads, each node annotated with the
      key columns the app pulls. State plainly that this is the legacy
      pipeline the marts in sections 3–5 replace, not a design to reproduce.
      Omit this section entirely if the app reads only dbt models.
   *Done when:* the file exists with every applicable section populated.

7. **Verify the mappings.** Re-check every `stg_` model and column cited in
   section 5 against the staging inventory from step 3. Any that don't exist
   move to section 6 (data gaps); do not leave them presented as real
   mappings. *Done when:* every source reference in section 5 is confirmed to
   exist, and the rest have been demoted.

## Mermaid ER reference

```
erDiagram
    DIM_ACCOUNT ||--o{ FCT_ORDER : places
    DIM_GAME    ||--o{ FCT_ORDER : "sold for"
    FCT_ORDER {
        string order_id PK
        string account_id FK
        string game_id FK
        numeric revenue_vat_excl
    }
```

Relationship syntax: `||--o{` one-to-many, `}o--o{` many-to-many,
`||--||` one-to-one.

## Mermaid lineage reference (section 7)

```
flowchart LR
    raw_orders["DTC.raw_orders<br/>base table"]
    v_fnb["DTC.v_fnb_enriched<br/>view · cols: order_id, revenue, supplier"]
    hex["Hex SQL: DTC_FnB<br/>cols: Revenue_VATexcl, FnB_Supplier"]
    raw_orders --> v_fnb --> hex
```

Direction flows upstream → downstream (base tables on the left, what the Hex
app reads on the right). Put the node's key columns in the label.
