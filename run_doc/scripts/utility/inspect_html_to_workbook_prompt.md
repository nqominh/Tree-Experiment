# Prompt: Inspect HTML → Workbook Conversion

You are helping me debug the **HTML → Workbook** stage in a table-processing pipeline.

## Objective
Validate that a table from the local **RealHiTBench/html** folder is correctly converted into workbook cells **before** merge expansion, schema/data splitting, or tree construction.

## Input Source
- Use one HTML file from `RealHiTBench/html` as input.
- If no filename is provided, pick one file automatically (e.g., the first `.html` file).
- Read the file content directly from disk; do **not** require pasted HTML.

## Input Parameters
- `html_folder`: `RealHiTBench/html`
- `html_file` (optional): `{{FILE_NAME.html}}`

## What to check

### 1) Table Selection & Basic Parsing
- State the selected HTML file name and full path.
- If multiple `<table>` tags exist in that file, state which one is selected and why.
- Count `<tr>` rows.
- For each row, count `<th>` and `<td>` cells.

### 2) `rowspan` / `colspan` Mapping
For every cell with `rowspan` or `colspan`, report:
- HTML row/column index
- Target workbook top-left coordinate
- Full occupied coordinate range

Also detect:
- Overlapping occupied coordinates
- Skipped coordinates
- Overwritten coordinates

### 3) Workbook Structure Validation
- Print a compact workbook preview (first **15 rows × 15 cols**) with coordinate + value.
- List all merged ranges created.
- Verify preservation of leading whitespace / indentation (including `&nbsp;`).

### 4) Data Integrity Checks
Identify:
- Dropped cells
- Shifted columns
- Unexpected duplicates
- Unexpected empty gaps/columns
- Rows where actual workbook width differs from expected logical width

### 5) Final Assessment
- Return **Pass** or **Fail** for HTML → Workbook conversion.
- If **Fail**, provide top **3 concrete fixes**.

## Required Output Format
1. Parsed Stats  
	- Include selected file/path and table index used  
2. Span Mapping Table  
3. Workbook Preview  
4. Issues Found  
5. Recommended Fixes  
6. Final Verdict
