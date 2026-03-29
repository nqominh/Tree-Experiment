# Plan: Full Bidirectional Hierarchy Capture

## Goal

Represent a table's complete hierarchy — both column **and** row headers — with full nesting preserved.

The current schema collapses column headers into flat `-`-joined strings and silently drops row header semantics. The fix introduces a symmetric row-header tree alongside the existing column tree, and replaces the flat row-dict JSON with an **addressed-cell format** where every cell carries explicit `row_path` and `col_path` arrays. This format is naturally readable by LLMs and directly indexable for retrieval.

---

## Proposed Output Format (JSON)

**Current (broken):**
```json
{
  "table": [
    { "Revenue-Q1": "12", "Revenue-Q2": "34" }
  ]
}
```
Problems:
- Column hierarchy flattened into `-`-joined strings
- Row hierarchy completely absent
- `None` appears as literal key when header cells are empty

**Proposed:**
```json
{
  "col_tree": [
    { "label": "Revenue", "children": [{ "label": "Q1" }, { "label": "Q2" }] }
  ],
  "row_tree": [
    { "label": "Total" },
    { "label": "Northeast", "children": [{ "label": "Urban" }, { "label": "Rural" }] }
  ],
  "cells": [
    { "row_path": ["Total"],              "col_path": ["Revenue", "Q1"], "value": "12" },
    { "row_path": ["Northeast", "Urban"], "col_path": ["Revenue", "Q1"], "value": "5"  }
  ]
}
```

- `col_tree` / `row_tree` preserve multi-level nesting as nested node objects — mirror structures.
- `cells` is a flat list; every cell carries its full coordinate addresses. No information is lost.
- Replaces the `-`-joined key hack and makes `None` keys impossible.
- Empty header levels use `null` label rather than the string `"None"`.

### Principle

Row and column hierarchies are the **same structure, different axis**:

| | Column headers | Row headers |
|---|---|---|
| HTML encoding | `colspan` spanning child columns | `rowspan` spanning child rows |
| Traversal direction | Left → right | Top → down |
| Tree type | `IndexTree` / `IndexNode` | Same (mirrored) |
| Cell address component | `col_path` leaf | `row_path` leaf |

---

## Pipeline Fix Steps

### Step 1 — Preserve `<th>` during HTML parsing

**File:** `utils/sheet_utils.py` (line ~113)

Currently `html2workbook()` calls `find_all(['td', 'th'])` and treats both cell types identically — the `<th>` semantic is discarded. Fix: annotate `<th>` cells via a parallel boolean sheet or cell metadata so downstream code knows which cells were semantic headers.

---

### Step 2 — Wire `split_schema_column()`

**File:** `utils/split_utils.py` (line 700)

`split_schema_column()` already exists as a mirror of `split_schema_row()` but is **never called** in the HTML path. Call it inside `construct_sheet()` (or wherever `split_schema_row()` is called) to extract the left-column schema sheet symmetrically.

---

### Step 3 — Build `construct_row_index_tree()`

**File:** `table2tree/feature_tree.py` (line ~393)

Mirror `construct_index_tree()` with a new `construct_row_index_tree()` that traverses the left-column schema sheet **row-first** (tall direction) instead of column-first. Reuse `IndexNode` — only the traversal direction changes, the algorithm is identical.

---

### Step 4 — Attach row tree to `FeatureTree`

**File:** `table2tree/feature_tree.py` (line ~200)

Add a `row_index_tree: IndexTree` field to `FeatureTree`. Populate it from `construct_row_index_tree()` alongside the existing `construct_index_tree()` call.

---

### Step 5 — Add `get_flatten_row_schema()`

**File:** `table2tree/feature_tree.py` (line ~125)

Mirror `get_flatten_schema()` to produce row-header leaf paths for retrieval and tagging.

---

### Step 6 — Rewrite `__json__()`

**File:** `table2tree/feature_tree.py` (line ~309)

Replace the current flat row-dict assembly with the new addressed-cell format:
- Emit `col_tree` (serialized `index_tree`)
- Emit `row_tree` (serialized `row_index_tree`)
- Emit `cells`: each entry has `row_path` (DFS path through `row_index_tree` to leaf), `col_path` (DFS path through `index_tree` to leaf), and `value` (`BodyNode.value`).

---

### Step 7 — Tag rows in `tree_partition.py`

Apply the same `tag_one_list()` grouping logic that currently annotates column `IndexNode`s to the new row `IndexNode`s, so row-header retrieval gets `name2id` / `id2name` indices analogous to the column side.

---

### Step 8 — Update prompt builder

**File:** `experiment/prompt_builder.py`

Update `build_hotree_prompt_schema()` and `build_hotree_prompt_hierarchical()` to include both `col_tree` paths and `row_tree` paths in the LLM context. Render as a **markdown table with explicit row-header columns** to stay closest to the LLM's training distribution, while the internal representation remains cell-centric.

---

## Verification Checklist

- [ ] Load an existing HTML table from `RealHiTBench/html/` and compare old vs new JSON output
- [ ] Assert `len(cells) == num_data_rows × num_data_cols` (no cells lost)
- [ ] Assert `None` no longer appears as a key in any cell's `row_path` or `col_path`
- [ ] Run `run_numerical_reasoning.py` against a sample from `numerical_reasoning_50.jsonl` to verify LLM prompt quality does not regress
- [ ] Validate that `tree_partition.py` `name2id` lookups work symmetrically for rows and columns on a test table with known row groups

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Addressed-cell format over extended flat JSON | Path arrays preserve hierarchy without encoding tricks; any downstream system can reconstruct the original table exactly |
| Reuse `IndexNode` for row headers | Avoids duplicating classes; only the traversal direction changes |
| `split_schema_column()` already exists | No need to write row-schema detection from scratch — just call it |
| Markdown rendering for LLM prompts | LLMs have seen millions of markdown tables during pretraining; staying close to that distribution outweighs the theoretical elegance of passing raw JSON |
