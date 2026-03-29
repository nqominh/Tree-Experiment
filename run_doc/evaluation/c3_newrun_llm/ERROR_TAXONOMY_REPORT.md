# C3 New-Run Error Taxonomy Report

## Coverage
- Total items: 103
- CORRECT: 32
- INCORRECT: 69
- UNCERTAIN: 0
- UNKNOWN SubQType mappings: 0

## Top SubQTypes By Incorrect Rate

| SubQType | Total | Correct | Incorrect | Uncertain | Accuracy | Incorrect Rate |
|---|---:|---:|---:|---:|---:|---:|
| Counting | 15 | 1 | 14 | 0 | 0.0667 | 0.9333 |
| Multi-hop Numerical Reasoning | 13 | 2 | 10 | 0 | 0.1538 | 0.7692 |
| Calculation | 49 | 12 | 36 | 0 | 0.2449 | 0.7347 |
| Ranking | 11 | 5 | 6 | 0 | 0.4545 | 0.5455 |
| Comparison | 15 | 12 | 3 | 0 | 0.8000 | 0.2000 |

## Output Files
- evaluation/c3_newrun_llm/evaluation_master_c3_newrun.enriched.csv
- evaluation/c3_newrun_llm/taxonomy_by_subqtype.csv
- evaluation/c3_newrun_llm/taxonomy_by_subqtype_final_label.csv
- evaluation/c3_newrun_llm/incorrect_examples_by_subqtype.csv