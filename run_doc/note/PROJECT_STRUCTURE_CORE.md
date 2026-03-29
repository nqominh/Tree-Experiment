# Project Structure (Core Files Only)

This map focuses on the main experiment and evaluation pipeline files.
Utility/debug helpers are intentionally excluded.

## 1) Core Experiment Flow

1. `prepare_tables.py`
   - Stage 1 preprocessing.
   - Reads benchmark HTML tables and builds `table_inputs/*.txt`.
   - Runs schema checks and writes `table_inputs/table_metadata.json`.

2. `run_experiment_csv.py`
   - Stage 2 inference runner.
   - Loads questions, table input (`txt/json/html`), builds prompts, calls Gemini API.
   - Writes row-level outputs to `experiment_results.csv` (or custom output path).

3. `tests/test_tree_building.py`
   - End-to-end and unit tests for table-to-tree conversion and output formats.

## 2) Core Domain Package (`experiment/`)

- `experiment/tree_builder.py`
  - Converts HTML tables into HO-Tree structures.
  - Contains strategy fallback (`direct`, `fixed`, `structured`).

- `experiment/tree_output.py`
  - Serializes tree to schema/JSON/hierarchical formats used by prompts and downstream steps.

- `experiment/schema_validator.py`
  - Validates extracted tree columns vs HTML columns.
  - Used during table preparation to track extraction mismatches.

- `experiment/prompt_templates.py`
  - Prompt constructors for different reasoning/template modes.

- `experiment/data_loader.py`
  - Dataset/table loading helpers used by test and experiment workflow.

- `experiment/batch_runner.py`
  - Batch orchestration entry for multi-item experiment runs.

## 3) Core Modeling Assets

### Prompt Templates (root)
- `EVIDENCE_PROMPT.md`
- `EVIDENCE_PROMPT_HTML.md`
- `EVIDENCE_PROMPT_JSON.md`
- `BASE_PROMPT_TEMPLATE.md`
- `BASE_PROMPT_TEMPLATE_HTML.md`
- `SIMPLE_PROMPT_TEMPLATE.md`

### Prompt Variants (`prompts/`)
- `prompts/C1_Vanilla.md`
- `prompts/C3_SchemaOnly.md`
- `prompts/C5_FullMethod.md`

## 4) Core Data / Inputs

- `tests/questions.jsonl`
  - Primary question set used by the runner.

- `tests/questions_batch2.jsonl`
  - Secondary batch/question split.

- `RealHiTBench/html/`
  - Source HTML tables for preprocessing.

- `table_inputs/`
  - Generated intermediate table representation files (`.txt`) and metadata.

## 5) Core Scoring & Statistical Evaluation (`score/`)

- `score/mcnemar_test.py`
  - Main paired McNemar significance test script.

- `score/mcnemar_simple.py`
  - Simpler McNemar workflow for two-run comparison.

- `score/calculate_kappa.py`
  - Inter-rater agreement (Cohen's kappa) computation.

## 6) Core Documentation

- `README.md`
  - Setup and run commands.

- `PIPELINE.md`
  - High-level workflow documentation.

- `METRICS_REFERENCE.md`
  - Metric definitions and interpretation.

- `llm_judge_pipeline_plan_v2.md`
  - Plan for LLM-as-judge extraction/batching/parsing pipeline.

---

## Excluded (Non-Core)

The following categories are intentionally excluded from this map:
- Utility modules under `utils/`
- One-off analysis scripts (`eda_*`, `visualize_*`, `inspect_*`, `highlight_*`)
- Ad-hoc conversion/debug scripts (`_*.py`, `debug_single.py`)
- Output artifacts (`*.csv`, `*.json`, `*.html`, `*.txt` results)
