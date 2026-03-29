# Router EDA Executive Summary

Generated: 2026-03-29 10:24:25

## Dataset Coverage

- Total rows in merged comparison: 625
- Disagreement rows: 134 (21.44%)
- All-wrong rows: 147 (23.52%)
- Rows using filename fallback instead of JSONL table_id: 0
- Rows missing JSONL table_id metadata: 0

## Load Diagnostics

- c1: raw=624, deduped=624, duplicates_removed=0
- c3: raw=625, deduped=625, duplicates_removed=0
- c5: raw=624, deduped=624, duplicates_removed=0
- metadata: raw=625, deduped=625, duplicates_removed=0

## Overall EM Accuracy

- C1: 70.51%
- C3: 70.40%
- C5: 58.33%

## Top Table Risk (Router Focus)

- economy-table65: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1,C3,C5
- economy-table67: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1,C3
- economy-table82: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1
- environment-table18: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1
- environment-table33: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C3
- science-table40: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C3
- science-table46: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1,C3
- society-table51: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C5
- sport-table02: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1,C3
- business-table07: risk=60.00%, disagreement=100.00%, all_wrong=0.00%, best_model=C1,C3

## Top Subtype Risk (Router Focus)

- Comparison: risk=34.11%, disagreement=33.68%, all_wrong=34.74%, best_model=C1
- Ranking: risk=33.81%, disagreement=35.71%, all_wrong=30.95%, best_model=C3
- Multi-hop Numerical Reasoning: risk=21.67%, disagreement=15.00%, all_wrong=31.67%, best_model=C1,C3
- Calculation: risk=18.71%, disagreement=13.93%, all_wrong=25.87%, best_model=C1,C3
- Counting: risk=15.03%, disagreement=18.92%, all_wrong=9.19%, best_model=C1

## Chart Index

- Model Accuracy: C:/Users/nqmi/Downloads/Tree-Experiment/score/minimax/router_eda/charts/model_accuracy_comparison.png
- Pattern Distribution by Subtype: C:/Users/nqmi/Downloads/Tree-Experiment/score/minimax/router_eda/charts/pattern_distribution_by_subtype.png
- Top Table Router Risk: C:/Users/nqmi/Downloads/Tree-Experiment/score/minimax/router_eda/charts/table_router_risk_top.png
- Subtype Accuracy Heatmap: C:/Users/nqmi/Downloads/Tree-Experiment/score/minimax/router_eda/charts/subtype_accuracy_heatmap.png
- Disagreement vs Best Accuracy: C:/Users/nqmi/Downloads/Tree-Experiment/score/minimax/router_eda/charts/disagreement_vs_best_accuracy.png
