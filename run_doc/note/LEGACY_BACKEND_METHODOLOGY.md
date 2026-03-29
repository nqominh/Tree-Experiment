# Methodology Research Section: Legacy Backend

## Methodology: Table Decomposition and Output Construction

### Objective
This methodology documents how the legacy backend breaks raw HTML tables into structured components and builds the final experiment input files. The focus is not only on model-ready outputs, but on the intermediate structure-building steps that determine downstream behavior.

### Input and Processing Unit
The processing unit is one unique table per `table_id` referenced in the question file. For each table:

1. Raw HTML is loaded from `RealHiTBench/html/<table_id>.html`.
2. Legacy structure extraction is executed (`backend=legacy`).
3. Three output blocks are assembled into one `.txt` artifact.

This one-table-at-a-time design makes decomposition traceable and reproducible.

### Legacy Breakdown Pipeline
The legacy backend performs a staged breakdown from HTML into hierarchical structure:

1. Parse HTML into an internal tree representation.
2. Build a column index hierarchy (header-side structure).
3. Build a row index hierarchy (stub/row-label structure, when available).
4. Validate extracted column count against expected schema width.
5. Convert index trees to indentation-based text used by prompts.

Conceptually, it transforms:

- HTML layout semantics (merged cells, nesting, header depth)
- into explicit hierarchical text paths
- then into stable prompt-facing output blocks

### How Tables Are Broken Down
The decomposition is represented in two complementary structures.

Column structure (`[COLUMN STRUCTURE]`):
- captures top-down header hierarchy
- keeps parent-child nesting through indentation
- preserves semantic grouping from merged and multi-row headers

Row structure (`[ROW STRUCTURE]`):
- captures left-side categorical hierarchy
- records nested row groups when present
- falls back to `(none)` if no row hierarchy is detected

Both structures are generated from index trees and serialized with deterministic indentation (`two spaces per depth level`).

### How Output Files Are Built
For each table, the final file is assembled in fixed section order:

1. `[COLUMN STRUCTURE]`
2. serialized column hierarchy text
3. `[ROW STRUCTURE]`
4. serialized row hierarchy text
5. `[TABLE HTML]`
6. cleaned HTML payload (caption + table only)

The HTML block is intentionally cleaned to reduce prompt noise:

- keeps `<table>` and relevant `<caption>` content
- removes unrelated document wrapper content
- preserves table content needed for evidence lookup

This gives each output file both a structural abstraction (column/row trees) and a grounded source view (clean HTML).

### Metadata Built Alongside Tables
In parallel with `.txt` generation, the pipeline writes `table_inputs/table_metadata.json` with per-table diagnostics:

- extraction strategy used
- extracted column count
- expected column count
- schema match flag

This metadata is used to monitor breakdown quality and diagnose failure modes even when output files are produced successfully.

### Determinism and Reproducibility
The legacy build is deterministic under fixed inputs:

- same question file
- same source HTML set
- same backend mode (`legacy`)
- same output formatting rules

Because decomposition and serialization are deterministic, file-level equality can be checked exactly across runs.

### Validation of Breakdown Fidelity
Validation is performed at two levels.

Structural validation:
- compare extracted vs expected schema width
- report schema mismatches without aborting full run

Artifact validation:
- compare generated `.txt` files by exact content (hash or direct diff)
- inspect unified diffs to identify where hierarchy changed

This dual validation distinguishes extraction-quality issues from serialization-only differences.

### Why This Matters for Legacy Baseline Research
The legacy backend is the control condition for migration studies because it defines the reference decomposition behavior used by prior experiments. Any new backend must match not only final file existence, but also how table hierarchies are broken down and written into prompt-facing structure.

### Reporting Template (Reusable)
"The legacy backend converts each HTML table into dual hierarchical representations (column and row index trees), serializes them as indentation-based schemas, and packages them with cleaned table HTML in a fixed three-block output format. We evaluate fidelity using schema-width checks and exact artifact comparison to ensure structural compatibility across runs." 
