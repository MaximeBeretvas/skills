---
name: dag-weaver
description: Turn a natural-language analytics question into permanent, PR-ready medallion dbt models. User-invoked — type /dag-weaver.
disable-model-invocation: true
---

Weave a natural-language question into a dbt DAG: staging → intermediate → mart, ending in a PR. Two phases split by a hard approval gate — **answer** the question first, then **weave** the permanent models only once the numbers are approved.

The **weave file** (a `.sql` in `analyses/`) is the spine of the run: it holds the exploratory query and, once approved, everything phase 2 needs to proceed cold if the session breaks. Write it as you go; it is the single source of truth between phases.

Honor the repo's dbt safety rules at all times: **dev target only**, never `--full-refresh` or any destructive command. Defer every layering, naming, materialization, testing, and NULL decision to the `cbdp-dbt-conventions` and `dbt-null-handling` skills rather than restating their rules here.

## Phase 1 — Answer

Goal: a query that answers the question, from staging only, with the risky interpretation choices surfaced.

1. **Shortlist candidate staging models.** Read the staging `schema.yml` docs (model + column descriptions) and the Avro schemas in `Docs/cbdp_info/avro/`; match the question against documented meaning. No warehouse round-trips to shortlist. Search **staging only** — ignore existing intermediate/marts even if one looks relevant.
   - _Done when:_ every staging model plausibly bearing on the question is listed, each with a one-line reason it's in or out.
2. **Probe the candidates.** Query them to confirm they hold what you think — `dbt show --inline` (dev) or the bigquery MCP against the dev dataset, your choice per need. Drop candidates the data doesn't support.
3. **Assemble one big query.** Combine the surviving staging models with CTEs into a single query answering the question. Size is not a concern here; correctness is. Staging-only lineage (`ref()` to staging).
4. **Write the weave file** to `analyses/wv_<slug>.sql` following [analysis-file.md](analysis-file.md) — the query plus header comments explaining what it does, the staging models used, and the assumptions made.
5. **Dead-end check.** If staging cannot answer the question — missing data, wrong grain, or the data contradicts the question's premise — **stop**. Finish the weave file with a `-- DEAD END:` section explaining exactly what's missing (which data/columns don't exist, or what the data actually shows vs. the premise), commit nothing else, and report to the user. Do not create models.
6. **Gate.** Present to the user: the big query, a sample of returned rows plus the key aggregate numbers, and an **explicit assumptions list** — every interpretation choice you were unsure about (grain, dedup, date boundaries, status filters). Wait for approval.
   - _Done when:_ the user has approved the numbers **and** the assumptions. Guessing approval is a failure.

## Phase 2 — Weave

Runs only after the phase-1 gate is approved. Nothing here touches the warehouse destructively.

7. **Finalize the weave file** into resume state per [analysis-file.md](analysis-file.md): approved query + approved assumptions + phase-1 result/aggregates + the proposed layering and naming plan. From here, a cold reader (or a fresh `/dag-weaver`) can complete phase 2 from this file alone.
8. **Branch.** Create and switch to a new branch for the work (e.g. `dag-weaver/<slug>`).
9. **Plan layers and names.** Using `cbdp-dbt-conventions`, decide which layers the logic warrants — mart always; intermediate when the logic genuinely warrants it; new staging **only** for a source with no staging model yet. Derive model names and pick a domain folder from the existing set. **Propose names + placement to the user and get approval** before writing any file.
10. **Write the models**, staging-only throughout — reuse existing staging via `ref()`; do **not** ref existing intermediate/marts even where it duplicates logic. Give every new model a YAML entry with a description and the standard tests (unique/not_null on keys) per `cbdp-dbt-conventions`.
    - _Done when:_ every model in the approved plan exists with SQL and a YAML entry carrying description + tests.

## Verify

All four are required before the skill is done. Fix and re-run on any failure.

11. **Parity.** Build the new mart in dev and assert its output **matches** the approved phase-1 query result (same rows, same numbers). This proves the decomposition preserved the approved answer — the check that makes the whole approach safe.
12. **Build + tests.** `dbt build` the new models against dev; all their tests pass.
13. **Lint.** `just lint` is clean for the new SQL/YAML (from `cbdp_dbt/`; `just fix` to autofix).
14. **Docs + tests present.** Confirm every new model actually has its YAML description and standard tests — not merely that tests passed.
15. **Open the PR.** With verification green, open a PR (base `develop`) summarizing the question, the models woven, and the parity result. Link the weave file as provenance.
    - _Done when:_ the PR is open and its description names the question, the models, and the confirmed parity.
