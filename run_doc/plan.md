## Plan: Intent Router V1 Full Pipeline

Build a deterministic, confidence-gated intent router integrated into the runtime experiment loop and extended through evaluation/reporting. The design is agent-native: resumable, parallelizable, and auditable at per-question level.

**Scope**
- Included: intent detection, confidence scoring, routing selection, runtime integration, policy logging, offline evaluation artifacts.
- Excluded: learned intent classifier training, production serving stack, human-in-the-loop workflows.

**Route Taxonomy**
| Intent | Trigger idea | Route | Empirical support |
|---|---|---|---|
| ORDERING | rank, top-k, highest to lowest, sorted order output | C3 | Strong |
| COMPOSITIONAL_MULTI_HOP | combine multiple constraints/steps across parts of table | C3 only when high-confidence | Weak-to-neutral (currently tied with C1) |
| DIRECT_COUNT | how many, count, cardinality | C1 | Strong |
| DIRECT_CALC | sum, avg, total, difference with direct arithmetic | C1 | Strong |
| DIRECT_COMPARE | which is larger/smaller, pairwise compare | C1 | Strong |
| OTHER_UNCERTAIN | ambiguous/noisy intent | C1 default | Safer baseline |

**Variable Implementation Spec**
1. Router input variables
- question_text: raw question string from query field.
- subqtype_hint: optional subtype hint from metadata if present.
- table_id: table identifier used for logging and manifest keys.
- policy_version: immutable routing policy version string, example router_v1_2026_03_29.

2. Text normalization variables
- q_norm: lowercase question text.
- q_clean: whitespace-collapsed and punctuation-simplified text.
- tokens: tokenized q_clean list.

3. Intent trigger dictionaries
- ORDERING_TRIGGERS: rank, ranking, top, bottom, highest, lowest, sort, sorted, order.
- DIRECT_COUNT_TRIGGERS: how many, count, number of, cardinality.
- DIRECT_CALC_TRIGGERS: sum, total, average, mean, difference, minus, plus, ratio, percent.
- DIRECT_COMPARE_TRIGGERS: larger, smaller, greater, less, compare, versus, than.
- MULTIHOP_TRIGGERS: combined, both, and, where, excluding, with at least, with at most, after filtering, then.

4. Match-count variables
- c_ordering: number of ORDERING trigger matches.
- c_count: number of DIRECT_COUNT trigger matches.
- c_calc: number of DIRECT_CALC trigger matches.
- c_compare: number of DIRECT_COMPARE trigger matches.
- c_multihop: number of MULTIHOP trigger matches.

5. Precedence and intent variables
- intent_precedence: ORDERING, DIRECT_COUNT, DIRECT_CALC, DIRECT_COMPARE, COMPOSITIONAL_MULTI_HOP, OTHER_UNCERTAIN.
- route_intent: chosen intent label after precedence resolution.
- route_reason: concise reason string including matched cues.

6. Confidence feature variables for multi-hop gate
- constraint_marker_count: number of explicit constraint markers, for example and, both, with, where, excluding, not, at least, at most.
- distinct_operator_group_count: number of distinct operator groups present among filter, aggregate, compare, rank, arithmetic-transform.
- cross_reference_marker_count: number of cross-reference cues, for example same row, corresponding, per category, compared with, between, then use that.

7. Normalized confidence components
- s_constraints = min(1, constraint_marker_count / 3).
- s_operators = min(1, distinct_operator_group_count / 3).
- s_cross_ref = min(1, cross_reference_marker_count / 2).

8. Confidence score and threshold variables
- conf_mh = 0.4*s_constraints + 0.3*s_operators + 0.3*s_cross_ref.
- mh_conf_threshold: default 0.55, tunable via CLI.
- route_confidence: set to conf_mh for COMPOSITIONAL_MULTI_HOP; set to 1.0 for deterministic non-multi-hop intents.

9. Route decision variables
- route_model:
- C3 when route_intent is ORDERING.
- C1 when route_intent is DIRECT_COUNT, DIRECT_CALC, DIRECT_COMPARE, OTHER_UNCERTAIN.
- For COMPOSITIONAL_MULTI_HOP: C3 if conf_mh >= mh_conf_threshold, else C1.
- route_policy_version: policy_version copied into each output row.

10. Runtime control variables for agent-native efficiency
- enable_intent_routing: feature flag, default false for backward compatibility.
- shadow_mode: compute and log routing, but execute configured base model only.
- max_workers: bounded concurrency for request throughput.
- retry_max and retry_wait_seconds: resilient queue controls.
- manifest_key: policy_version + qid + table_id + prompt_hash + route_model.
- run_manifest_status: pending, running, done, failed.

11. Output schema variables
- Existing columns remain unchanged.
- Added columns: route_intent, route_model, route_confidence, route_reason, route_policy_version, shadow_mode.

**Integration Steps**
1. Runtime entrypoint integration
- Integrate routing in shared run loop before model invocation so both Gemini and MiniMax paths inherit behavior.
- Add CLI flags for enable_intent_routing, mh_conf_threshold, route_policy_version, shadow_mode.

2. Routing engine module
- Implement deterministic router in a dedicated utility module.
- Unit test exact trigger precedence and confidence computations.

3. Agent-native orchestrator
- Add one orchestrator entrypoint for P0-P5 policy runs.
- Add resumable manifest and idempotent per-question keying.
- Add bounded parallel dispatch with retry-aware queueing.

4. Evaluation integration
- Reuse existing EM and F1 computation scripts for routed outputs.
- Extend router EDA script to produce policy_comparison_main, by_intent, by_subtype, by_table, disagreement_only, win_loss_tie, executive summary.
- Add paired significance checks with McNemar and bootstrap CI.

5. Rollout protocol
- Run shadow mode first.
- Promote to active routing on balanced subset.
- Confirm on full benchmark before locking policy version.

**Relevant files**
- c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py
- c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_minimax.py
- c:/Users/nqmi/Downloads/Tree-Experiment/utils/intent_router.py
- c:/Users/nqmi/Downloads/Tree-Experiment/scripts/eda_router_disagreement.py
- c:/Users/nqmi/Downloads/Tree-Experiment/score/evaluate_qa.py
- c:/Users/nqmi/Downloads/Tree-Experiment/score/mcnemar_test.py
- c:/Users/nqmi/Downloads/Tree-Experiment/tests/test_intent_router.py
- c:/Users/nqmi/Downloads/Tree-Experiment/tests/test_router_pipeline_smoke.py

**Verification checks**
1. Determinism: route outputs identical across repeated runs with same inputs.
2. Coverage: no missing route_intent or route_model.
3. Consistency: summary aggregates exactly reconcile with per-question records.
4. Efficiency: measured overhead stays small and resume avoids duplicate calls.
5. Effectiveness: policy delta is non-negative against best single model on target slices.
