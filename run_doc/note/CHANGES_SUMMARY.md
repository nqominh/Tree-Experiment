# Changes Summary — Pre-Push Cleanup

## Modified Files (tracked by git)

| File | Change |
|------|--------|
| `experiment/prompt_templates.py` | Added `row_schema` support to `build_hotree_prompt_schema()` |
| `experiment/tree_builder.py` | Added `construct_row_index_tree` calls to `fixed` and `structured` strategies |
| `experiment/tree_output.py` | Added `tree_to_row_schema()`, `tree_to_json_legacy()` |
| `table2tree/feature_tree.py` | Added `row_index_tree`, `construct_row_index_tree()`, new `__json__()` addressed-cell format |
| `utils/split_utils.py` | Added `split_schema_column()` for row header detection |
| `utils/sheet_utils.py` | Added `_th_map` annotation in `html2workbook()` |

## New Files — **KEEP** (part of experiment pipeline)

| File | Purpose |
|------|---------|
| `CURRENT_PROMPT.md` | Experiment prompt template (8-section structure) |
| `prepare_tables.py` | Stage 1 — generates `table_inputs/` files |
| `run_experiment_csv.py` | Stage 2 — calls Gemini API, writes `experiment_results.csv` |
| `highlight_fuzzy.py` | Post-analysis — highlights fuzzy EM matches |
| `tests/questions.jsonl` | 100 questions dataset for the experiment |
| `table_inputs/` (46 files) | Pre-built table inputs (col/row structure + HTML) |

## New Files — **REMOVE** (redundant, generated, or temp)

| File | Reason to remove |
|------|-----------------|
| `run_experiment.py` | Superseded by `run_experiment_csv.py` |
| `run_questions.py` | Superseded by `run_experiment_csv.py` |
| `questions_results.json` | 7 MB generated output from old `run_questions.py` |
| `questions_results.txt` | Generated summary from old `run_questions.py` |
| `tree_batch_results.txt` | Old batch test output |
| `inspect_html_to_workbook.py` | Debug/inspection script, not needed for experiment |
| `inspect_html_to_workbook_prompt.md` | Debug prompt, not needed |
| `inspect_tree.py` | Debug/inspection script |
| `BIDIRECTIONAL_HIERARCHY_PLAN.md` | Implementation plan artifact, not needed in repo |
| `PIPELINE.md` | Old pipeline documentation |
| `experiment_results.csv` | Generated output (re-creatable by running Stage 2) |
| `experiment_results_highlighted.html` | Generated HTML report |
| `_changes.txt` | Temp file |
| `_changes_clean.json` | Temp file |
| `scripts/utility/_get_changes.py` | Temp script |
| `__pycache__/` | Python cache |
| `experiment/__pycache__/` | Python cache |
| `utils/__pycache__/` | Python cache |
