---
name: bug-hunter-Brian777cool
description: Audit a Python function for bugs against its task description, emit a structured bug report per the AIASE 2026 Pairwise Bug Hunter contract.
version: 0.1.0
metadata:
  hermes:
    tags: [code, audit, aiase-2026]
    category: code
---

# Bug Hunter Skill (Pairwise Track)

> **TODO for student**: rename folder + frontmatter `name` to include your github_id;
> fill in the LLM-side audit in the Procedure; strengthen the harness in `scripts/`.

## When to Use

When the user sends a JSON payload with `code` (Python source), `task_description`, and `task_id`. The skill must produce a structured bug report whose `bugs[]` matches actual bugs (Jaccard-ish line+type overlap), with low false-positive rate on clean code.

Trigger example:

```
/bug-hunter-<your_github_id> {"task_id":"task_042",
  "code":"def merge_intervals(intervals): ...",
  "task_description":"Merge overlapping intervals, empty input returns []."}
```

## Procedure

1. **Parse** the payload. Read `code` line-by-line (1-indexed); read the task description for the spec.
2. **Probe** the code by running `python scripts/analyze.py` with the code + task description + entry function name. The script:
   - parses the AST to extract function name + parameters,
   - runs the function on a battery of deterministic edge inputs (empty, single-element, extremes),
   - returns per-input crash / mismatch / OK plus suspicious line ranges.
3. **Review** the analyzer signals. For each suspicious line range, decide:
   - **bug or not** (don't over-report — false positives are penalized).
   - **type**: one of `off_by_one` / `null_deref` / `type_error` / `logic_error` / `edge_case` / `api_misuse` / `inefficient` / `unhandled_input` (see spec §2.3).
   - **severity**: `critical` / `high` / `medium` / `low` — calibrated to "how easily triggered + how severe".
   - **suggested_fix**: actionable, specific.
4. **Verdict**: `clean` if no bugs found, `buggy` otherwise. If `verdict=clean`, `bugs[]` must be `[]`.
5. **Emit** the contract by running `python scripts/run.py` with the final `{task_id, verdict, bugs, confidence}` as argv JSON. Output the resulting fenced JSON block **unchanged**.

## Pitfalls

- **Over-reporting** (always reporting many bugs) destroys score — clean code FP rate is 25% of your grade.
- **Under-reporting** (always `verdict=clean`) also destroys score — F1 on buggy code is 50%.
- **Wrong severity calibration**: empty-input crash = `medium` (edge), wrong-answer-on-common-input = `high`/`critical`. See spec §2.3.
- **Wrong line numbers**: 1-indexed, point at the smallest line range that contains the bug. Don't point at the function signature line for an off-by-one in the loop.

## Verification

The output of `scripts/run.py` is a single fenced ```json``` block with:

- `task_id` (must equal input)
- `verdict` (`"buggy"` or `"clean"`)
- `bugs` (array of bug objects with `line_start`, `line_end`, `severity`, `type`, `description`, `suggested_fix`; **must be `[]` when verdict=clean**)
- `confidence` (number in `[0.0, 1.0]`)
