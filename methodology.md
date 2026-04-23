# Methodology

## 1. Chapter Scope

This chapter describes the methodology used to evaluate large language models (LLMs) on table question answering. The focus is on two core components:

1. The algorithm for processing input tables and questions.
2. The algorithm for constructing prompts that guide model reasoning over tabular evidence.

The chapter is written as an undergraduate thesis methodology: it emphasizes procedure, reproducibility, and design rationale rather than software artifacts.

## 2. Research Design

The study follows a pipeline-based experimental design. Each sample consists of a question and its associated table. The pipeline transforms raw table content into a structured representation, integrates that representation into a prompt template, queries a model, and evaluates the generated answer.

At a high level, the workflow has four stages:

1. Input acquisition and validation.
2. Structural parsing of table content.
3. Prompt assembly.
4. Model inference and answer scoring.

Only stages 1 to 3 are detailed algorithmically in this chapter, because they define how evidence is prepared and presented to the model.

## 3. Input Processing Method

### 3.1 Input Units

Each experimental unit includes:

1. A unique question identifier.
2. A table identifier linking the question to one table source.
3. A natural-language question.
4. A gold answer used for evaluation.

Input processing begins by validating that each question has a resolvable table identifier and non-empty question text.

### 3.2 Table Normalization

Raw table sources are typically HTML pages that contain additional non-table content (navigation blocks, formatting tags, or visual styling). To reduce noise before prompting, normalization keeps only evidence relevant to question answering:

1. Retain the table region and caption text if present.
2. Remove decorative style attributes and unrelated page elements.
3. Preserve textual values and cell order.

This step reduces token waste and improves evidence density in the final prompt.

### 3.3 Structural Parsing

After normalization, the table is parsed into two complementary hierarchies:

1. Column hierarchy (header logic and grouped columns).
2. Row hierarchy (row headers, grouped rows, and nested categories).

Because real-world HTML tables are heterogeneous, parsing is performed with a fallback strategy set:

1. Primary parser for regular table markup.
2. Secondary parser for irregular span patterns.
3. Fallback parser for malformed or partially structured tables.

The first successful parser output is accepted if it returns a non-empty structure.

### 3.4 Tree Building

After parsing succeeds, the method constructs two explicit trees:

1. A column tree, where internal nodes represent grouped headers and leaves represent atomic answer-bearing columns.
2. A row tree, where internal nodes represent grouped row headers and leaves represent atomic row endpoints.

Tree construction is performed from normalized sheet structure, including merged-cell expansion. This ensures that hierarchical header relationships are represented as parent-child links rather than repeated flat text.

The tree representation is important for two reasons:

1. It preserves multi-level schema relationships that are often lost in plain text linearization.
2. It provides a deterministic basis for path extraction, which is used in prompts.

### 3.5 Column Path and Row Path Encoding

From the trees, the method extracts root-to-leaf paths.

1. Column path: a sequence of header labels from the column-tree root to one leaf column.
2. Row path: a sequence of row-header labels from the row-tree root to one leaf row.

A path is serialized as an ordered label chain, for example:

1. Column path example: `Economy > 2022 > GDP`.
2. Row path example: `Region > East > Urban`.

These paths are used as compact semantic keys. They reduce ambiguity when repeated terms appear in different parts of the table and help the model align question intent to the correct table region.

### 3.6 Structural Sanity Check

A sanity check compares:

1. Expected column count from normalized HTML traversal.
2. Extracted leaf-column count from parsed structure.

Matching counts indicate that the parsed schema is likely coherent. Mismatches are flagged for analysis, but the sample can still proceed to prompting to avoid unnecessary data loss.

### 3.7 Algorithm 1: Input Processing

```text
Algorithm 1 Input Processing, Tree Building, and Path Extraction
Input: Question set Q, table source collection T
Output: Processed sample list S

Initialize S as empty list

for each question q in Q do
    if q.table_id is missing or q.question is empty then
        continue

    table_raw <- fetch table from T using q.table_id
    if table_raw is missing then
        continue

    table_clean <- normalize_html(table_raw)

    parse_ok <- false
    for parser in [primary, secondary, fallback] do
        structure <- parser(table_clean)
        if structure is non-empty then
            parse_ok <- true
            break
        end if
    end for

    if parse_ok is false then
        continue

    column_tree <- build_column_tree(structure)
    row_tree <- build_row_tree(structure)

    column_paths <- flatten_root_to_leaf_paths(column_tree)
    row_paths <- flatten_root_to_leaf_paths(row_tree)

    expected_cols <- count_expected_columns(table_clean)
    extracted_cols <- count_leaf_columns(column_tree)
    schema_match <- (expected_cols == extracted_cols)

    sample <- {
        id: q.id,
        question: q.question,
        answer: q.gold_answer,
        table_id: q.table_id,
        column_structure: serialize(column_tree),
        row_structure: serialize(row_tree),
        column_paths: serialize(column_paths),
        row_paths: serialize(row_paths),
        table_evidence: table_clean,
        schema_match: schema_match
    }

    append sample to S
end for

return S
```

## 4. Prompt Construction Method

### 4.1 Prompting Objective

The prompt is designed to make the model reason with explicit table evidence rather than prior world knowledge. To achieve this, the prompt combines:

1. A role instruction that defines the QA task.
2. Structured evidence blocks (column and row hierarchies).
3. Flattened column paths.
4. Flattened row paths.
5. Raw table evidence (normalized HTML text).
6. The user question.
7. Output constraints (short final answer format).

### 4.2 Template Structure

A template-based approach is used to ensure consistency across samples. The template has fixed sections with placeholders:

1. Task instruction section.
2. Evidence section for column structure.
3. Evidence section for row structure.
4. Evidence section for column paths.
5. Evidence section for row paths.
6. Evidence section for table content.
7. Query section with the question string.
8. Response format section requiring a final concise answer.

By using a fixed skeleton, variance from prompt phrasing is minimized, and observed performance differences are more likely to reflect model behavior rather than prompt drift.

### 4.3 Evidence Packing Strategy

Evidence is packed in a structure-first order:

1. Column hierarchy.
2. Row hierarchy.
3. Column paths.
4. Row paths.
5. Table text.

This ordering encourages the model to establish schema context before reading cell-level content, reducing errors caused by column ambiguity.

### 4.4 Algorithm 2: Prompt Assembly

```text
Algorithm 2 Prompt Assembly
Input: Processed sample s, prompt template P
Output: Final prompt string p

p <- P

replace placeholder {COLUMN_STRUCTURE} with s.column_structure in p
replace placeholder {ROW_STRUCTURE} with s.row_structure in p
replace placeholder {COLUMN_PATHS} with s.column_paths in p
replace placeholder {ROW_PATHS} with s.row_paths in p
replace placeholder {TABLE_EVIDENCE} with s.table_evidence in p
replace placeholder {QUESTION} with s.question in p

append instruction:
    "Use only the provided table evidence."
append instruction:
    "Return a single final answer line."

return p
```

### 4.5 Prompt Quality Controls

To keep prompts stable and interpretable, the following controls are applied:

1. No sample-specific ad hoc wording outside template fields.
2. Identical section labels for all prompts.
3. Deterministic placeholder replacement rules.
4. Preservation of table text order during insertion.
5. Stable path ordering from deterministic tree traversal.

These controls make prompt generation reproducible and suitable for thesis-level comparison.

## 5. Model Inference and Output Handling

After prompt assembly, the model generates a textual response. Response handling follows a constrained extraction policy:

1. Prefer explicitly marked final-answer spans if present.
2. Otherwise, extract the last non-empty answer line.
3. Strip formatting markers and normalize spacing.

Predicted answers are then compared with reference answers using normalized exact match. Normalization handles case and formatting variation while preserving semantic comparison.

## 6. Reliability and Validity Considerations

The methodology addresses reliability in three ways:

1. Fixed preprocessing and prompting rules.
2. Consistent template structure across all samples.
3. Explicit fallback logic for irregular table markup.
4. Deterministic root-to-leaf path extraction from trees.

Potential threats to validity remain:

1. Parser fallback may preserve structure but still miss semantic header intent.
2. Very noisy or malformed tables can propagate errors into prompt evidence.
3. Some questions require external context not present in the table.

These limitations are acknowledged during result interpretation.

## 7. Methodological Summary

The proposed methodology converts heterogeneous table-question pairs into a uniform promptable format through two explicit algorithms:

1. Algorithm 1 for input processing and structural encoding.
2. Algorithm 2 for prompt assembly.

This separation between evidence preparation and prompt construction improves reproducibility, clarifies where errors originate, and provides a transparent basis for undergraduate-level empirical analysis of LLM table reasoning.