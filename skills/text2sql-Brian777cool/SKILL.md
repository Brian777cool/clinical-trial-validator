---
name: text2sql-Brian777cool
description: Convert a natural-language question + SQLite schema into a verified read-only SQL query. AIASE 2026 Basic Track.
version: 0.1.0
metadata:
  hermes:
    tags: [sql, text2sql, data, aiase-2026]
    category: data
---

# Text2SQL Skill (Basic Track)

> **TODO for student**: rename folder `text2sql-Brian777cool` → `text2sql-<your_github_id>`,
> and change `name:` above to match. Then fill in the procedure / strengthen the harness.

## When to Use

When the user sends a JSON payload with `question`, `db_schema` (SQLite DDL), and optional `task_id` + `dialect`. The skill must produce a single read-only SQLite query whose result on the hidden DB matches the gold answer under bag equality.

Trigger example:

```
/text2sql-<your_github_id> {"task_id":"task_nl2sql_017",
  "question":"List the names of all students who scored above 90 ...",
  "db_schema":"CREATE TABLE Students(...); ...", "dialect":"sqlite"}
```

## Procedure

1. **Parse** the input payload. Extract `task_id`, `question`, `db_schema`, `dialect`.
2. **Plan** the SQL. Identify the relevant tables, JOIN keys, filters, aggregations. (See `## Pitfalls`.)
3. **Draft** a single SQLite read-only SQL statement.
4. **Validate** the SQL by running `python scripts/validate_sql.py` and passing both the schema and your draft SQL as a JSON payload (see script docstring). It returns `{ok: bool, error: str}`.
   - If `ok=false`, read the error message and **retry up to 3 times**, fixing the issue each time (typo, missing column, wrong table alias, etc.). After 3 failures, proceed with the best draft and lower `confidence`.
5. **Emit** the final contract by running `python scripts/run.py` and passing it the final `{task_id, sql, rationale, confidence}` as a JSON argv. The script prints a single fenced ```json``` block — return that block as your final response **unchanged**.

## Pitfalls

- **Many-to-many JOINs without DISTINCT** → duplicate rows. The grader uses bag (multiset) equality, so duplicate rows fail. If the question semantically asks for a set ("list the students who ..."), use `DISTINCT`.
- **Column / table names** must exist in the given schema. `validate_sql.py` uses `EXPLAIN` against an in-memory DB built from the DDL; references to nonexistent columns will fail there.
- **Dialect**: always SQLite. No window functions, no CTE / `WITH`, no recursive queries (regardless of what dialect the LLM "feels like" using). See spec §2.2.
- **Single statement**: exactly one query, no semicolon-separated multiples.
- **Read-only**: no `INSERT` / `UPDATE` / `DELETE` / DDL.
- **task_id** in your output must equal the input `task_id`. The grader rejects mismatches.

## Verification

The output of `scripts/run.py` is a single fenced ```json``` block with:

- `task_id` (must equal input)
- `sql` (single read-only SQLite query)
- `rationale` (string)
- `confidence` (number in `[0.0, 1.0]`)

The block must be the **last** fenced JSON in stdout. Do not add any reasoning after it.
