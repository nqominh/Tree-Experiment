# C3 New-Run LLM Evaluation Runbook

Date: 2026-03-16

## Scope
- Evaluate only the new C3 wrong predictions (EM==0) from the resumed run.
- Source wrong-set file: score/C3_newrun_EM0_only.csv (103 items).

## Executed Steps

### 1) Build minimal XLSX input (required by 01_extract.py)
Command:

```powershell
.venv\Scripts\python.exe -c "import pandas as pd; from pathlib import Path; src=Path('score/C3_newrun_EM0_only.csv'); out=Path('evaluation/c3_newrun_llm/C3_newrun_EM0_minimal.xlsx'); keep=['id','question','correct_answer','model_answer','EM']; df=pd.read_csv(src,dtype=object)[keep]; out.parent.mkdir(parents=True, exist_ok=True); df.to_excel(out,index=False); print({'rows':len(df),'xlsx':out.as_posix()})"
```

Output:
- evaluation/c3_newrun_llm/C3_newrun_EM0_minimal.xlsx

### 2) Extract EM==0 items to evaluation master
Command:

```powershell
.venv\Scripts\python.exe evaluation/01_extract.py --input evaluation/c3_newrun_llm/C3_newrun_EM0_minimal.xlsx --output evaluation/c3_newrun_llm/evaluation_master_c3_newrun.csv
```

Result:
- EM==0 rows extracted: 103
- Output: evaluation/c3_newrun_llm/evaluation_master_c3_newrun.csv

### 3) Create LLM judge batches
Command:

```powershell
.venv\Scripts\python.exe evaluation/02_format_batches.py --input evaluation/c3_newrun_llm/evaluation_master_c3_newrun.csv --batch-size 50 --output-dir evaluation/c3_newrun_llm/batches
```

Result:
- Total items: 103
- Batches created: 3
- Prompt: evaluation/c3_newrun_llm/batches/judge_prompt.md
- Batch files:
  - evaluation/c3_newrun_llm/batches/batch_01_items.csv
  - evaluation/c3_newrun_llm/batches/batch_02_items.csv
  - evaluation/c3_newrun_llm/batches/batch_03_items.csv

## Next Steps (Manual + Finalization)

### 4) Fill judgements with LLM judges
- Use evaluation/c3_newrun_llm/batches/judge_prompt.md
- For each batch CSV, collect three judge labels and write them into:
  - Claude Sonnet 4.6
  - GPT 5.4 Thinking
  - Grok Expert
in evaluation/c3_newrun_llm/evaluation_master_c3_newrun.csv.

### 5) Aggregate final labels
Command:

```powershell
.venv\Scripts\python.exe evaluation/03_parse_outputs.py --master evaluation/c3_newrun_llm/evaluation_master_c3_newrun.csv --output evaluation/c3_newrun_llm/final_results_c3_newrun.csv --human-review-output evaluation/c3_newrun_llm/human_review_list_c3_newrun.csv --summary-output evaluation/c3_newrun_llm/summary_report_c3_newrun.txt
```

### 6) Write final labels back to C3 result file
Command:

```powershell
.venv\Scripts\python.exe evaluation/04_write_back_adjusted_results.py --original score/C3_schema_only.backup_before_reextract.csv --result evaluation/c3_newrun_llm/final_results_c3_newrun.csv --output score/C3_schema_only.backup_before_reextract.updated.csv
```

## Notes
- Keep this run isolated under evaluation/c3_newrun_llm for reproducibility.
- The write-back step is fail-fast: all IDs in final_results must exist in original file.
