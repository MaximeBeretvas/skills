# The weave file

One `.sql` file in `analyses/`, named `wv_<slug>.sql` where `<slug>` is a short kebab-case handle for the question. It is the run's state: phase 2 must be completable from this file alone.

It compiles as a dbt analysis (`ref()` resolves), so it stays reviewable in the PR as the documented origin of the models.

It has two terminal shapes.

## Dead-end shape (phase 1 stopped)

Header comment, then the best staging-based query you could build, then the gap explanation. Kept as proof for later investigation.

```sql
-- WEAVE FILE — DEAD END
-- Question: <the natural-language question, verbatim>
-- Staging models used: <ref names>
-- What this query does: <plain-language summary>
--
-- DEAD END: <why staging cannot answer this — which data/columns are absent,
--   or what the data actually shows vs. the question's premise>

<the query>
```

## Resume shape (phase 1 approved)

Everything phase 2 needs to weave the models cold. Header carries the approved assumptions, the phase-1 result, and the layering + naming plan; body is the approved query.

```sql
-- WEAVE FILE — APPROVED, READY TO WEAVE
-- Question: <verbatim>
-- Staging models used: <ref names>
-- What this query does: <plain-language summary>
--
-- APPROVED ASSUMPTIONS (confirmed by user):
--   - grain: <...>
--   - dedup: <...>
--   - date boundaries: <...>
--   - status filters: <...>
--   - <any other interpretation choice that was surfaced>
--
-- PHASE-1 RESULT (the answer to preserve — parity target):
--   <key aggregate numbers / sample rows the user approved>
--
-- LAYERING & NAMING PLAN (approved by user):
--   - staging: reuse only; new staging only for <un-staged source, or "none">
--   - intermediate: <names + what each does, or "none — logic doesn't warrant it">
--   - mart: <name + domain folder>
--
-- Lineage rule: staging-only. Do NOT ref existing intermediate/marts.

<the approved big query>
```
