# HO-Tree Pipeline

> How hierarchical-order trees are built from HTML tables.

## Overview

```
HTML table ──► openpyxl Workbook ──► Merge expansion
     │                                     │
     │                          ┌──────────┴──────────┐
     │                     Schema sub-sheet      Data sub-sheet
     │                          │                     │
     │                     IndexTree              BodyTree
     │                          │                     │
     │                          └──────────┬──────────┘
     │                               FeatureTree
     │                                     │
     └─────────────────────────────────────►│
                                           │
                          ┌────────────────┼────────────────┐
                     JSON dict      Hierarchical string   Schema list
```

The pipeline converts an HTML `<table>` into a **FeatureTree** — a pair
of an **IndexTree** (column headers / schema) and a **BodyTree** (data
rows).  Three output formats are available for downstream QA prompts.

---

## Modules

| Module | Purpose |
|---|---|
| `experiment/batch_runner.py` | CLI entry-point; iterates over HTML files and writes results |
| `experiment/tree_builder.py` | Three tree-building strategies with automatic fallback |
| `experiment/tree_output.py` | Serialises a FeatureTree to JSON / string / schema |
| `experiment/data_loader.py` | Discovers HTML files and loads QA items from JSON |
| `experiment/prompt_templates.py` | Four prompt templates for LLM-based table QA |
| `experiment/debug_single.py` | Build & inspect a single table interactively |
| `table2tree/extract_excel.py` | Loads an Excel file, expands merges, preprocesses cells |
| `table2tree/feature_tree.py` | Core data structures and construction algorithms |
| `utils/sheet_utils.py` | openpyxl helpers (merge handling, sub-sheet extraction) |
| `utils/split_utils.py` | Splits a sheet into schema and data sub-sheets |
| `utils/api_utils.py` | `llm_generate()` wrapper for OpenAI-compatible APIs |
| `utils/constants.py` | Shared constants (paths, type tags, API config) |

---

## Step-by-step pipeline

### 1. HTML → openpyxl Workbook

```
html2workbook(html_string)          # utils/sheet_utils.py
```

Parses the HTML with **BeautifulSoup**, extracts `<table>` tags, and
writes them into an in-memory **openpyxl** `Workbook`.  Row/column spans
(`rowspan`, `colspan`) become Excel merged-cell ranges.

### 2. Merge expansion

```
sheet2structure(sheet)              # utils/sheet_utils.py
```

Walks every merged-cell range and copies the top-left value into each
constituent cell, then **unmerges** the range.  After this step every
cell carries its own value and the sheet is ready for positional lookups.

### 3. Cell preprocessing

```
preprocess_sheet(sheet)             # table2tree/extract_excel.py
```

Stringifies every non-merged cell value so downstream code can rely on
uniform `str` types.

### 4. Schema / data split

```
split_schema_row(sheet)             # utils/split_utils.py
  → (schema_sub_sheet, data_sub_sheet)
```

Determines where the column-header rows end and data rows begin.
Two detection modes:

| Mode | Trigger | How it works |
|---|---|---|
| **Merge-based** | Sheet still has merged cells | Height = max bottom-row of any first-row merge |
| **Content-based** | No merges (flattened CSV) | Heuristics: skip title rows (≥80 % same value), detect column-header rows (distinct text), stop at first data row (≥3 numeric cells) or row-group header |

### 5. IndexTree construction

```
construct_index_tree(schema_sheet)            # merge-aware
construct_index_tree_flattened(schema_sheet)   # value-group-aware
construct_index_tree_smart(schema_sheet)       # auto-selects above
```

Recursively walks the schema sub-sheet column-by-column:

1. Read the **top-left cell** of the current column span.
2. If the cell's merge extends fewer rows than the full schema height ⇒
   there are sub-headers below.  Extract a sub-sheet for the remaining
   rows & columns, recurse.
3. Otherwise create a **leaf `IndexNode`** with the cell value.

For flattened sheets (no merge info) `construct_index_tree_flattened`
groups consecutive columns that share the same value on a given row and
recurses on rows below each group.

Result: an `IndexTree` whose `leaf_nodes` list is a left-to-right
ordering of the finest-grained column headers.

### 6. BodyTree construction

```
construct_body_tree(index_tree, data_sheet)
```

DFS over the data sub-sheet, left-to-right, top-to-bottom:

* Each cell becomes a `BodyNode` with `(x1, y1, x2, y2)` coordinates.
* The node is linked to the corresponding `IndexNode` leaf via
  `index_tree.add_leaf_body_node_by_pos(node, depth)`.
* Merge-granularity changes determine parent/child relationships:
  when a cell on the right is *wider* than the current cell it becomes a
  shared child (reused from a previous DFS branch).

### 7. FeatureTree assembly

```
construct_sheet(sheet)             # wraps steps 4-6
construct_feature_tree(tree_dict)  # recursive, supports nested dicts
```

`construct_sheet` is the single-table path (split → index → body →
FeatureTree).

`construct_feature_tree` handles the recursive case: a `tree_dict` maps
string keys to either:

* a **dict** → recurse to get a nested FeatureTree,
* a **scalar** → wrap in a `BodyNode`,
* a **sheet** → call `construct_sheet`.

Each key/value pair becomes an `IndexNode`/`BodyNode` pair, assembled
into the final tree.

---

## Tree-building strategies (`experiment/tree_builder.py`)

The experiment layer offers three strategies exposed through
`html_to_tree(html, strategy)`:

| Strategy | Description |
|---|---|
| `direct` | `html2workbook` → `sheet2structure` → `preprocess_sheet` → `construct_sheet` |
| `fixed` | Like *direct*, but caps header height at `min(detected, 4)` rows |
| `structured` | `get_structured_xlsx_sheet` → wrap in `{DEFAULT_TABLE_NAME: sheet}` → `construct_feature_tree` |

`html_to_tree(html)` (no strategy) tries **direct → fixed → structured**
and returns the first that succeeds, together with the strategy name.

---

## Output formats (`experiment/tree_output.py`)

| Format | Method | Use |
|---|---|---|
| `json` | `FeatureTree.__json__()` | Nested dict; key-value or list-of-dicts |
| `hierarchical` | `FeatureTree.__str__()` | Numbered outline (`1.1 Header: val, val, …`) |
| `schema` | `IndexTree.get_flatten_schema()` | Flat list of hyphenated column paths |

---

## Data flow summary

```
batch_runner.main()
  │
  ├─ data_loader.discover_tables(html_dir)
  │     → list of .html paths
  │
  └─ for each html_path:
       ├─ tree_builder.html_to_tree(html_string)
       │     → (FeatureTree, strategy_used)
       │
       ├─ tree_output.tree_to_json(tree)
       ├─ tree_output.tree_to_hierarchical(tree)
       └─ tree_output.tree_to_schema(tree)
```

---

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_tree_building.py -v

# Build trees for all HTML tables in a directory
python -m experiment.batch_runner --html_dir RealHiTBench/html --out results/
```
