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

## Evidence rule

Every fact in the blueprint must be **evidence-based** — backed by a tool
call, never guessed:

- Anything about the warehouse — that a model, table, view, or column exists,
  its data type, its lineage — comes from the **dbt MCP** (`get_model_details`,
  `get_all_models`) or the **BigQuery MCP** (`get_table_info`, `execute_sql`).
- Anything about the app — its story, metrics, KPIs, the columns its SQL
  reads — comes from the rendered Hex export (step 1).

If you cannot back a claim with one of these sources, do not write it as fact.
Move it to section 6 (data gaps & open questions) as an explicit assumption or
open question instead. Inferred column-level lineage in section 7 must be
labelled as inferred, not asserted.

## Input

One Hex export yaml under `Hex/<app>/<app>.yaml` in the target dbt repo. If
the user didn't name one, list the `Hex/` subfolders and ask which app.

## Steps

Run the exploration in **subagents** so the raw tool output (the large Hex
export, dbt model dumps, view DDL, `INFORMATION_SCHEMA` results) stays in their
context, not the main one. Each subagent returns a **cited findings brief** —
every fact paired with the tool call that proved it (e.g.
`stg_core__orders.order_id` via dbt `get_model_details`; `DTC.t_fnb_daily` built
by `scheduled_query_…` via `INFORMATION_SCHEMA.JOBS`). Pass back only the brief,
never raw dumps.

1. **Mine the Hex app (subagent).** Spawn one subagent to render and read the
   export:
   - Run `uv run <skill-dir>/scripts/hex_yaml_compact.py <path-to-hex.yaml>`
     (raw exports are hundreds of KB of UI noise — never read them directly).
   - From the compact output, extract the app's story (what it answers, for
     whom), its metrics/KPIs (name + formula), and every source table+column
     its SQL reads.
   - Split those sources into two lists: references to dbt models, and external
     BigQuery tables/views not in dbt.
   *Done when:* the brief carries the story, KPI list, and both source lists.

2. **Inventory staging and trace lineage (parallel subagents).** With the Hex
   brief in hand, spawn two subagents at once:
   - **Staging inventory** — get the staging models and their columns+types via
     the dbt MCP (`get_all_models`, then `get_model_details` on the `stg_`
     models); if the dbt MCP is unavailable, read `schema.yml` + `.sql` under
     `models/staging/`.
   - **BigQuery lineage** — only if step 1 found external sources. For each,
     reconstruct where its data comes from with the BigQuery MCP:
     1. `get_table_info` for its type and, if a view, its SQL (or
        `INFORMATION_SCHEMA.VIEWS` via `execute_sql`).
     2. If a view, recurse into the tables its definition reads until every
        branch ends in a table.
     3. For each table, find its origin via `INFORMATION_SCHEMA.JOBS`
        (region-qualified) on `destination_table`: a populating **scheduled
        query** (job_id begins `scheduled_query_`, or attributed to the Data
        Transfer Service) means it's built in BigQuery — capture that SQL, add
        the scheduled query as a node, and recurse into its inputs; no
        populating query job means the data is **ingested from outside** — mark
        it an ingestion source and end the branch.
     4. Classify every node (view / scheduled-query output / ingested table),
        record each edge and the key columns the app pulls (inferred).
     This lineage is legacy and considered bad — documented only to understand
     current data flow, never reproduced. If the BigQuery MCP is unavailable,
     list the raw external tables and note lineage couldn't be resolved.
   *Done when:* both briefs are back — staging columns+types, and the external
   lineage with every node's origin classified.

3. **Design the marts.** Map the app's needs onto a star schema: fact
   table(s) at a stated grain, dimension table(s) for the entities. Follow
   the repo's naming (`fct_`, `dim_`, `int_` for intermediates). For each
   recommended column, record which staging model+column it derives from.
   Anything the app needs that no staging model supplies goes on the
   data-gaps list. *Done when:* every recommended column is either mapped to
   a staging source or flagged as a gap.

4. **Write the blueprint** to `Docs/Blueprints/<app>/blueprint.md` with these
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
      `flowchart LR` of the dependencies from the lineage brief (step 2), from origin up to what
      the Hex SQL reads, each node annotated with the key columns the app
      pulls. Show scheduled queries as their own nodes feeding the tables they
      build, and mark externally-ingested tables as ingestion sources, so the
      diagram makes clear whether each piece of data is created in BigQuery or
      comes from outside. State plainly that this is the legacy pipeline the
      marts in sections 3–5 replace, not a design to reproduce. Then a nested
      **Pipeline review** subsection: a short assessment of this legacy
      pipeline against data-engineering best practices — SQL quality,
      robustness, idempotency, freshness/scheduling, testing, and cost —
      naming the concrete risks a rebuild should fix. Omit the whole section
      if the app reads only dbt models.
   *Done when:* the file exists with every applicable section populated.

5. **Verify against the evidence rule (subagent).** Delegate verification to a
   fresh subagent so the re-check runs in its own context: it independently
   walks every factual claim in the blueprint and confirms each against the
   tools — `stg_` model/column references and data types via the dbt MCP (or
   staging files); external table/view existence, origin, and lineage via the
   BigQuery MCP; app story, KPIs, and source columns against the rendered Hex
   export — and returns a list of corrections (each unbacked claim + the fix).
   Apply them: warehouse claims that can't be confirmed move to section 6 as
   assumptions; inferred lineage columns in section 7 stay marked inferred.
   *Done when:* the subagent reports no remaining unbacked claim and its
   corrections are applied.

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
    ext[/"POS export<br/>ingested from outside"/]
    raw_orders["DTC.raw_orders<br/>ingested table"]
    sq{{"scheduled query<br/>builds_fnb (daily)"}}
    t_fnb["DTC.t_fnb_daily<br/>table · cols: order_id, revenue, supplier"]
    hex["Hex SQL: DTC_FnB<br/>cols: Revenue_VATexcl, FnB_Supplier"]
    ext --> raw_orders --> sq --> t_fnb --> hex
```

Direction flows upstream → downstream (origin on the left, what the Hex app
reads on the right). Node shapes distinguish origin: `[/.../]` externally
ingested, `{{...}}` scheduled query, `[...]` table/view. Put each node's key
columns in the label.
