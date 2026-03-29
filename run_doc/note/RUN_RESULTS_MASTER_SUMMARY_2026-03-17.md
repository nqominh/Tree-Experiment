# Run Results Master Summary (as of 2026-03-17)

## Scope
This file consolidates experiment outcomes from the start of the C1/C3/C5 workflow, including:
- Raw run accuracy from output CSV files
- Coverage for first 251-question set and full 625-question set
- LLM-judge aggregation summaries
- Fleiss' kappa where available

## Dataset Anchors
- First 251 set: tests/questions_clean_audit.jsonl
- Full set target: tests/questions_clean_audit copy.jsonl (625 IDs)

Notes:
- Some run files include an extra ID 672 that is not in the 625-ID full-copy set.
- Accuracies below are computed directly from EM column in run CSVs.

## Core Run Accuracy Summary

| Run | File | Rows in file | Coverage in 251 set | Accuracy on 251 set | Coverage in 625 set | Accuracy on 625 set |
|---|---|---:|---:|---:|---:|---:|
| C1 Vanilla (initial 251 run) | score/C1_vanilla.csv | 251 | 251 | 66.93% (168/251) | 250 | 67.20% (168/250) |
| C3 SchemaOnly (early mis-scoped copy run) | score/C3_schema_only.from_copy_backup_2026-03-16.csv | 278 | 251 | 66.14% (166/251) | 277 | 63.54% (176/277) |
| C3 SchemaOnly (resumed to full) | score/C3_schema_only.backup_before_reextract.csv | 626 | 251 | 66.14% (166/251) | 625 | 70.08% (438/625) |
| C5 FullMethod (current progress) | score/C5_full.csv | 411 | 251 | 58.17% (146/251) | 410 | 61.71% (253/410) |

Interpretation:
- C3 full-run file is effectively complete for the 625-ID full set (plus one extra non-full-set ID).
- C5 full-set run is in progress (410/625 full-set IDs currently present).

## LLM-Judge Aggregation Results

### A) C1 first-251 wrong subset adjudication
Source summary: evaluation/summary_report_c1.txt
- Total EM==0 items adjudicated: 83
- Final labels:
  - CORRECT: 52
  - INCORRECT: 31
  - HUMAN_REVIEW: 0

Potential corrected C1(251) accuracy if applied:
- Raw CORRECT = 168
- Plus adjudicated CORRECT among EM==0 = 52
- Adjusted CORRECT = 220 / 251 = 87.65%

### B) C3 new-run (remaining/full extension) adjudication
Source summary: evaluation/c3_newrun_llm/summary_report_c3_newrun.txt
- Total EM==0 items adjudicated: 103
- Final labels:
  - CORRECT: 32
  - INCORRECT: 69
  - HUMAN_REVIEW: 2

## Fleiss' Kappa Results

### A) C1 adjudication set
Computed from: evaluation/evaluation_master_c1_for_fleiss.csv
Output: evaluation/evaluation_master_c1_with_fleiss.csv
- Items: 83
- Exact 3-way agreement: 13/83 (15.66%)
- Fleiss' kappa: 0.1127

### B) C3 new-run adjudication set
Computed from: evaluation/c3_newrun_llm/evaluation_master_c3_newrun_for_fleiss.csv
Output: evaluation/c3_newrun_llm/evaluation_master_c3_newrun_with_fleiss.csv
- Items: 103
- Exact 3-way agreement: 57/103 (55.34%)
- Fleiss' kappa: 0.4239

## File Map (quick access)
- C1 run: score/C1_vanilla.csv
- C3 full run: score/C3_schema_only.backup_before_reextract.csv
- C5 run-in-progress: score/C5_full.csv
- C1 judge summary: evaluation/summary_report_c1.txt
- C3 judge summary: evaluation/c3_newrun_llm/summary_report_c3_newrun.txt
- C1 Fleiss output: evaluation/evaluation_master_c1_with_fleiss.csv
- C3 Fleiss output: evaluation/c3_newrun_llm/evaluation_master_c3_newrun_with_fleiss.csv
