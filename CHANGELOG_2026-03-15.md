# Changelog - 2026-03-15

## Summary
Completed end-to-end evaluation and audit cleanup updates, including pipeline refactors, 3-judge aggregation, write-back tooling, inter-rater reliability, clean-audit generation, and conservative artifact organization.

## Code And Pipeline Updates

### 1) Evaluation pipeline scripts
- Added and updated script set for extraction, batching, aggregation, and write-back:
  - `01_extract.py`
  - `02_format_batches.py`
  - `03_parse_outputs.py`
  - `04_write_back_adjusted_results.py`
- Created organized evaluation workspace with script copies and usage docs:
  - `evaluation/01_extract.py`
  - `evaluation/02_format_batches.py`
  - `evaluation/03_parse_outputs.py`
  - `evaluation/04_write_back_adjusted_results.py`
  - `evaluation/README.md`

### 2) Batch/prompt format update
- `02_format_batches.py` now generates:
  - Shared prompt markdown file (`judge_prompt.md`)
  - Per-batch CSV item files (`batch_XX_items.csv`)
  - `judgement` column for LLM fill-in
- Added explicit numeric tolerance guidance for 2-decimal judgment:
  - Absolute difference `< 0.005` treated as equivalent after rounding.

### 3) Extraction and normalization improvements
- Added shared normalization utility:
  - `utils/answer_normalization.py`
- Refactored `run_experiment_csv.py` to use shared EM normalization.
- Improved multi-line answer extraction from `full_response` with better section parsing and fallback guards.

### 4) 3-judge aggregation and write-back
- Implemented 3-reviewer majority logic in `03_parse_outputs.py`:
  - Majority CORRECT/INCORRECT -> final label
  - No binary majority -> HUMAN_REVIEW
- Enhanced lock handling on master CSV writes with fallback behavior.
- Updated write-back behavior in `04_write_back_adjusted_results.py`:
  - Writes final verdict directly into `EM` column (no separate EM_adjusted field)
  - Fail-fast validation on IDs/columns/duplicates
  - No partial write if validation fails

### 5) Fleiss kappa for 3 reviewers
- Added `score/calculate_fleiss_kappa.py`.
- Uses same class mapping constraints as Cohen workflow:
  - `__MATCH__`, `__CORRECTION__`, `__NO_INFO__`
- Default now runs on all rows.
- Adds `final_judged_answer` by majority vote over reviewer answers.
- If all three reviewers provide three different answers, `final_judged_answer` is left blank.

### 6) Clean-audit dataset generation and thorough testing
- Rebuilt clean dataset generation in `score/create_clean_dataset.py`:
  - Source of truth: `final_judged_answer`
  - Clean output: `tests/questions_clean_audit.jsonl`
  - Blank/no-info separated to: `tests/questions_clean_audit_needs_review.csv`
  - Enforced `ProcessedAnswer == final_judged_answer` in clean output
- Rebuilt verification in `score/test_clean_dataset.py` with strict checks:
  - ID existence and uniqueness
  - Processed/label/answer alignment
  - Exclusion of blank/no-info rows from clean set
  - Presence of excluded rows in needs-review CSV

## Run Outcomes Captured Today
- C3 three-judge aggregation completed and written.
- C1 three-judge aggregation completed and written.
- Fleiss kappa (all rows) completed and saved back to audit CSV.
- Clean audit dataset generation and test validation passed.

## Conservative Cleanup (No Path-Breaking Refactor)
To avoid breaking path-sensitive scripts, only legacy outputs were moved.

### New archive structure
- `old_experiments/csv_variants/`
- `old_experiments/judge_artifacts/`
- `old_experiments/model_exports/`
- `old_experiments/temp_outputs/`
- `old_experiments/reports/`

### Moved files
- Historical CSV variants and interim experiment outputs moved to `old_experiments/csv_variants/`.
- Root-level judged batch CSV duplicates moved to `old_experiments/judge_artifacts/`.
- Gemini batch exports (`csv/jsonl/tsv`) moved to `old_experiments/model_exports/`.
- Temporary analysis outputs moved to `old_experiments/temp_outputs/`.
- Legacy report HTML/TXT artifacts moved to `old_experiments/reports/`.

## Intentionally Kept In Place
Kept active canonical files and path-sensitive scripts in place to preserve current commands and defaults:
- Core scripts at root and `evaluation/`
- Active evaluation outputs (`evaluation_master.csv`, `final_results.csv`, `human_review_list.csv`)
- Main experiment output (`experiment_results.csv`)
- `score/` and `tests/` active files

## Notes
- This was a conservative organization pass.
- A full source-tree refactor can be done later if needed, with explicit path updates across scripts.
