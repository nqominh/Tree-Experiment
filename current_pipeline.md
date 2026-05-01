# Current Table Pipeline Notes

This file records the current table-structure pipeline so future readers can
understand the implementation without re-inspecting the code first.

## Direct Answers To The Four Concerns

1. Stage 1 does not destroy span information.
   - Current behavior: `parse_html_table()` creates one `HtmlCell` object for each
     source `<td>` or `<th>`. That object stores `row`, `col`, `rowspan`,
     `colspan`, `is_header`, `text`, and `raw_text`.
   - The normalized grid stores references to the same `HtmlCell` object in every
     position covered by its span. The grid is flat in shape, but the cell
     metadata is still available through the referenced object.
   - Methodology wording should say "normalized grid plus cell metadata", not
     only "flat 2D grid".
   - Code: `experiment/html_table_extractor_components/parsing.py`,
     `parse_html_table()`.

2. `rowspan` in column headers is not handled by raw boundary-derived edges.
   - Current behavior: the implementation does not derive explicit
     parent-child edges from `colspan` boundaries. It builds each column path by
     reading the detected header rows top-to-bottom for that specific column.
   - Consecutive duplicate labels are skipped. Since a `rowspan` cell appears as
     the same `HtmlCell` object and same label in the rows it spans, it is added
     once to that column path and does not become a parent of labels in adjacent
     columns.
   - Example implication: a `Region` header with `rowspan=2` contributes
     `Region` as the path for its own column; it is not assigned as parent of
     `Q1`, `Q2`, or `Q3` in other columns.
   - Code: `experiment/html_table_extractor_components/builders.py`,
     `build_column_paths()`.

3. Column fallback is top-to-bottom path extraction.
   - Current behavior: there is no separate "no-span" hierarchy algorithm.
     Whether or not span attributes exist, each detected header row is treated as
     one possible depth level in document order for each data column.
   - For each data column, labels encountered from top to bottom are appended to
     that column's path, skipping empty labels and consecutive duplicates.
   - The final column tree is created by inserting those paths into
     `StructureNode`.
   - Code: `build_column_paths()` and `StructureNode.add_path()`.

4. OR logic in column-schema detection can include data rows.
   - Current behavior: this risk exists in the implementation. A row is counted
     as part of the column-schema band when any one of these is true:
     `has_span`, `all_th`, or `mostly_text`.
   - Because `has_span` is independent of numeric density, a numeric data row
     containing a `rowspan` or `colspan` can be retained as a header row.
   - No code change has been made. If this is corrected later, the likely fix is
     to bound the header band at the first row with more than one-third numeric
     non-empty cells, regardless of span attributes, or to make the span rule
     stricter.
   - Code: `experiment/html_table_extractor_components/detection.py`,
     `detect_header_rows()`.

## Active Extractor

Primary public entry point:

- `experiment/html_table_extractor.py`
  - Re-exports the componentized extractor while keeping the old public API.
  - Main callable: `extract_table_structure(html)`.

Actual implementation:

- `experiment/html_table_extractor_components/api.py`
  - Orchestrates parsing, title detection, schema-region detection, path
    extraction, and tree construction.

Returned object:

- `ExtractedTable` in `experiment/html_table_extractor_components/models.py`
  - `column_tree`: rooted `StructureNode` for column paths.
  - `row_tree`: rooted `StructureNode` for row paths.
  - `column_paths`: list of extracted column root-to-leaf paths.
  - `row_paths`: list of extracted row root-to-leaf paths.
  - `data_start_row`: first row index treated as data.
  - `data_start_col`: first column index treated as data.
  - `expected_cols`: grid width minus `data_start_col`.
  - `extracted_cols`: number of unique column paths.
  - `strategy`: currently defaults to `"html_grid"`.
  - `title`: detected table title, if any.

## Execution Order

1. Parse HTML to a normalized grid.
   - File: `parsing.py`.
   - Function: `parse_html_table(html)`.
   - Uses BeautifulSoup and the first `<table>`.
   - Iterates direct child `<tr>` rows and direct child `<td>/<th>` cells.
   - Creates `HtmlCell` objects with text, raw text, start coordinate, span
     values, and header-tag status.
   - Broadcasts the same object reference over every covered grid position.
   - Pads rows to equal width with `None`.

2. Remove duplicate source cells per row when needed.
   - File: `parsing.py`.
   - Function: `unique_cells(row)`.
   - Since spanned cells occupy multiple grid slots, this helper deduplicates by
     Python object identity.

3. Detect title rows.
   - File: `detection.py`.
   - Function: `detect_title(grid)`.
   - Scans up to the first three rows.
   - Counts blank rows as title-area rows.
   - Treats rows as title rows when they contain one broad-spanning source cell
     or a single unique non-empty source cell.
   - Returns `(title, title_rows)`.

4. Detect column-schema rows.
   - File: `detection.py`.
   - Function: `detect_header_rows(grid, title_rows)`.
   - Scans from `title_rows` up to at most six further rows.
   - A row is included if any condition holds:
     - all non-empty unique source cells are `<th>`;
     - any non-empty unique source cell has `rowspan > 1` or `colspan > 1`;
     - numeric-like cells are at most `max(1, len(nonempty) // 3)`.
   - Empty rows in the scan are counted as header rows.
   - The scan stops at the first row that fails all criteria.
   - Fallback: if no header row was found but the first post-title row has any
     `<th>`, one header row is used.
   - Known risk: the span condition can include numeric data rows.

5. Detect row-schema columns.
   - File: `detection.py`.
   - Function: `detect_left_header_cols(grid, header_rows)`.
   - Scans at most the first four columns, starting after detected header rows.
   - A column is retained as row schema when it is mostly textual and cells to
     the right provide enough numeric evidence.
   - Special first-column fallback: if following numeric cells outnumber the
     first-column cells, the first column is treated as row schema.

6. Detect two-column metric-table special case.
   - File: `detection.py`.
   - Function: `looks_like_metric_table(...)`.
   - Applies only when the grid has exactly two columns, a title was detected,
     and the left header width is one column.
   - Requires at least three value rows and enough numeric/formula-like values
     in the right column.
   - If true, `extract_table_structure()` emits the title as the only column path
     and no row paths.

7. Compute data-region offsets.
   - File: `api.py`.
   - Normal case:
     - `data_start_row = max(title_rows + header_rows, header_rows)`.
     - `data_start_col = left_header_cols`.
   - Metric-table case:
     - `data_start_col = 1`.
     - `data_start_row = max(title_rows, header_rows)`.

8. Build column paths.
   - File: `builders.py`.
   - Function: `build_column_paths(grid, title_rows, header_rows, data_start_col)`.
   - Header scan range is `[title_rows, title_rows + header_rows)`.
   - For each data column from `data_start_col` to grid width:
     - read labels top-to-bottom;
     - skip empty labels;
     - skip labels equal to the previous appended label;
     - append the resulting path if non-empty and not already seen.
   - This is the effective column hierarchy algorithm for both span and no-span
     tables.

9. Build row paths.
   - File: `builders.py`.
   - Function: `build_row_paths(grid, data_start_row, data_start_col)`.
   - If `data_start_col <= 1` and the first column contains indentation of at
     least two spaces, row hierarchy is inferred from indentation:
     - `depth = indent // 2`;
     - stack is truncated to the current depth;
     - current label is appended.
   - Otherwise, row paths are built left-to-right across the row-schema columns:
     - non-empty labels update a carry list for that column;
     - blank cells inherit the carried label from that column;
     - adjacent duplicate labels in the path are removed.
   - Paths are deduplicated while preserving order.

10. Build rooted ordered trees.
    - File: `models.py`.
    - Class: `StructureNode`.
    - Method: `add_path(path)`.
    - Inserts each label sequence into a root node, reusing existing child labels
      under the same parent and preserving insertion order.

11. Render schema for prompts when needed.
    - File: `rendering.py`.
    - Function: `render_indented(root)`.
    - Emits two spaces per tree depth.
    - Empty trees render as `(none)`.

## Text And Numeric Helpers

- File: `text_utils.py`.
- `normalize_text(value)`:
  - replaces non-breaking spaces with normal spaces;
  - collapses whitespace;
  - strips leading/trailing whitespace.
- `leading_indent(value)`:
  - counts leading spaces after normalizing non-breaking spaces.
- `is_numeric_like(value)`:
  - strips common currency symbols, commas, asterisks, and dash variants;
  - recognizes integer/decimal/percent forms, including parenthesized or negative
    values.

## Alternate HO-Tree Path

There is also an older/alternate pipeline:

- `experiment/tree_builder.py`
  - Main callable: `html_to_tree(html_content, max_header_rows=2)`.
  - Tries `direct`, then `fixed`, then `structured`.
  - Converts HTML to an openpyxl workbook through `utils.sheet_utils.html2workbook`.
  - Uses `table2tree.feature_tree` helpers to construct `FeatureTree` objects.

- `experiment/tree_output.py`
  - `tree_to_schema(tree)`: flattened column paths.
  - `tree_to_row_schema(tree)`: flattened row paths when available.
  - `tree_to_json(tree)`: JSON representation.
  - `tree_to_hierarchical_string(tree)`: native numbered tree string.

This alternate path is used by some legacy tests and prompt-template utilities.
The four concerns above refer to the active `html_table_extractor_components`
implementation, especially `parse_html_table()`, `detect_header_rows()`, and
`build_column_paths()`.

## Recommended Methodology Wording

Use these concise claims in the thesis:

- Stage 1 produces a normalized grid whose entries reference original parsed
  cell objects, so span metadata survives broadcasting.
- Column hierarchy is path-based: each data column is read top-to-bottom through
  the detected header band, consecutive duplicate labels are skipped, and paths
  are inserted into a rooted ordered tree.
- `rowspan` cells in the column-schema region contribute one label to the column
  path they occupy; they do not create child edges to labels in rows they span.
- When spans are absent, the same top-to-bottom path extraction is used, treating
  each header row as a possible depth level.
- The current header-row detector is permissive because span-bearing rows pass
  even if numeric; this should be stated as a limitation or fixed in code before
  claiming the numeric-bound rule.
