# LLM Pipeline Compact Context

Last updated: 2026-03-29

## 1) Pipeline purpose
Run table QA experiments, score exact match (EM), and generate router-oriented disagreement analysis.

Core runtime path:
- Questions source: tests/questions_clean_audit copy.jsonl
- Prompt building: TXT/JSON/HTML table input + prompt template
- Model call: provider-specific API through shared runner
- Row-level output: CSV with prediction, EM, prompt metadata, and optional route metadata

## 2) Main execution entrypoints
- run_experiment_csv.py
  - Shared runner (Gemini default) used by both direct Gemini and MiniMax adapter.
  - Includes prompt build, API retry loop, answer extraction, EM scoring, append-only CSV write.
- run_experiment_minimax.py
  - Adapter that monkey-patches model call to MiniMax Anthropic-compatible endpoint.
  - Delegates full run loop to run_experiment_csv.run(...).

## 3) Router implementation (new)
Implemented in utils/intent_router.py and integrated into shared runtime loop.

### 3.1 Intent taxonomy
- COUNTING
- RANKING
- COMPARISON
- MULTI_HOP
- CALCULATION (default)

### 3.2 Precedence (first match wins)
1. COUNTING
2. RANKING
3. COMPARISON
4. MULTI_HOP
5. CALCULATION

Rule: COUNTING overrides CALCULATION when both cues are present (example: question contains both "how many" and "total").

### 3.3 Route policy
- RANKING -> C3 profile
- COUNTING -> C1 profile
- COMPARISON -> C1 profile
- CALCULATION -> C1 profile
- MULTI_HOP -> confidence-gated:
  - C3 profile if conf_mh >= mh_conf_threshold
  - else C1 profile

Profile definitions:
- C1 profile: `RealHiTBench/html` + `run_doc/prompts/C1_Vanilla.md`
- C3 profile: `table_inputs/*.txt` + `run_doc/prompts/C3_SchemaOnly.md`
- Executed provider model remains fixed to `--model` for all rows.

### 3.4 Multi-hop confidence
conf_mh = 0.4*s_constraints + 0.3*s_operators + 0.3*s_cross_ref

Where:
- s_constraints = min(1, constraint_marker_count / 3)
- s_operators = min(1, distinct_operator_group_count / 3)
- s_cross_ref = min(1, cross_reference_marker_count / 2)

## 4) Runtime flags added (new)
Available in both run_experiment_csv.py and run_experiment_minimax.py:
- --enable-intent-routing
- --mh-conf-threshold (default 0.55)
- --route-policy-version (default router_v1_2026_03_29)
- --shadow-mode
- --c1-model
- --c3-model

Behavior notes:
- Routing disabled by default (backward compatible).
- Active routing switches profile per row (C1/C3 profile) while keeping executed model fixed.
- Shadow mode is log-only for routing and keeps execution on baseline CLI profile.
- `--c1-model` and `--c3-model` are backward-compatibility flags and are ignored.
- If routing is enabled and output CSV already exists without route columns, runner raises a schema mismatch error and asks for a new output file.

## 5) CSV schema
Base columns:
- id, question, correct_answer, model_answer, full_response, full_prompt, filename, sub_type, EM, strategy, prompt_tokens, schema_match

Route columns (when routing enabled):
- route_intent
- route_model
- route_confidence
- route_reason
- route_policy_version
- shadow_mode
- profile_selected
- profile_executed
- profile_fallback_applied
- profile_fallback_reason
- prompt_template_used
- input_mode_used
- executed_model

## 6) Analysis pipeline
Router EDA script:
- scripts/eda_router_disagreement.py

Inputs:
- score/minimax/C1_vanilla_minimax_audit.csv
- score/minimax/C3_schema_only_minimax_audit.csv
- score/minimax/C5_full_method_minimax_audit.csv
- tests/questions_clean_audit copy.jsonl

Outputs (default score/minimax/router_eda):
- router_main_comparison.csv
- router_by_table_summary.csv
- router_by_subtype_summary.csv
- router_disagreement_only.csv
- router_executive_summary.md
- charts/*.png

## 7) Newest operational hygiene changes
Noise suppression for tooling and search:
- .vscode/settings.json updated:
  - search.exclude includes tests/artifacts/mismatch_inspection/_work/legacy_outputs/**
  - files.exclude includes tests/artifacts/mismatch_inspection/_work/legacy_outputs/**
- .gitignore updated:
  - tests/artifacts/mismatch_inspection/_work/legacy_outputs/

Documentation consolidation:
- Markdown/PDF documents moved under run_doc/ preserving relative paths.

## 8) Minimal run examples
MiniMax routed run (active routing):
- python run_experiment_minimax.py --questions "tests/questions_clean_audit copy.jsonl" --prompt-file "run_doc/prompts/C3_SchemaOnly.md" --output "score/minimax/router_active.csv" --model "MiniMax-M2.7" --enable-intent-routing --mh-conf-threshold 0.55

MiniMax routed run (shadow mode):
- python run_experiment_minimax.py --questions "tests/questions_clean_audit copy.jsonl" --prompt-file "run_doc/prompts/C3_SchemaOnly.md" --output "score/minimax/router_shadow.csv" --model "MiniMax-M2.7" --enable-intent-routing --shadow-mode

## 9) Current status snapshot
- Router integrated end-to-end in runtime path.
- Taxonomy and precedence aligned with requested COUNTING/RANKING/COMPARISON/MULTI_HOP/default CALCULATION policy.
- Syntax checks passed for modified runtime/router files.
