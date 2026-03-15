# Evaluation Pipeline

This folder contains the LLM-as-judge evaluation scripts.

## Scripts

- `01_extract.py`: extract rows needing judge review (`EM == 0`) from one or more xlsx files into `evaluation_master.csv`.
- `02_format_batches.py`: create judge prompt markdown and per-batch item CSV files.
- `03_parse_outputs.py`: aggregate votes from 3 judges and write final labels.
- `04_write_back_adjusted_results.py`: write final results back to an original CSV/XLSX file by ID.

## Recommended Run Order

1. Extract review items

```bash
python evaluation/01_extract.py --input score/*.xlsx --output evaluation_master.csv
```

2. Create batches for judges

```bash
python evaluation/02_format_batches.py --input evaluation_master.csv --batch-size 50 --output-dir batches
```

3. Collect judge outputs and aggregate votes

```bash
python evaluation/03_parse_outputs.py --master evaluation_master.csv --output final_results.csv
```

4. Write final labels back to original file by ID

```bash
python evaluation/04_write_back_adjusted_results.py --original score/C3_schema_only.xlsx --result final_results.csv --output score/C3_schema_only.updated.xlsx
```

## Write-Back Behavior

`04_write_back_adjusted_results.py` is fail-fast:

- stops immediately if required columns are missing
- stops immediately on invalid/empty/duplicate IDs
- stops immediately if any result ID is missing in the original file
- performs no partial write

The script writes directly to the `EM` column:

- `CORRECT` -> `1`
- `INCORRECT` -> `0`
- `HUMAN_REVIEW` -> empty

It also writes:

- `judge_final_label`
- `judge_adjudication_source`
- `judge_claude_label` (if present)
- `judge_gpt_label` (if present)
- `judge_grok_label` (if present)
