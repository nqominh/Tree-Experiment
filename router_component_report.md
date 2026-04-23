# Router Component Report

## Scope
This report explains the deterministic intent router used to select execution profiles for Table QA runs.

Primary implementation:
- [utils/intent_router.py](utils/intent_router.py)

Primary integration:
- [run_experiment_csv.py](run_experiment_csv.py)

Validation tests:
- [tests/test_intent_router.py](tests/test_intent_router.py)

## What The Router Does
The router classifies each question into an intent label and then maps that classification to an execution profile:
- C1: vanilla profile
- C3: schema-oriented profile

The router returns a structured decision object with:
- intent
- route_model
- confidence
- reason
- policy_version
- internal diagnostics (match counts and multi-hop features)

## Public Interface
The main entry point is route_question in [utils/intent_router.py](utils/intent_router.py).

Inputs:
- question_text: raw question string
- policy_version: auditable policy tag
- mh_conf_threshold: promotion threshold for multi-hop routing (default 0.45)
- subqtype_hint: optional metadata hint (reserved for future use)

Output:
- RouteDecision dataclass instance in [utils/intent_router.py](utils/intent_router.py)

## Decision Pipeline
The routing logic follows a deterministic, staged pipeline.

1. Normalize and tokenize question text.
2. Apply ranking override check first.
3. Count trigger matches for each intent class.
4. Resolve base intent by precedence order.
5. Compute independent multi-hop confidence features.
6. Apply final route decision rules.

### Intent Taxonomy
Defined intent labels in [utils/intent_router.py](utils/intent_router.py):
- COUNTING
- RANKING
- COMPARISON
- MULTI_HOP
- CALCULATION

Route labels:
- C1
- C3

### Precedence Rule
Base intent is selected by first matched class in precedence order:
- COUNTING
- RANKING
- COMPARISON
- MULTI_HOP
- CALCULATION

This ensures deterministic behavior for overlapping cues.

### Ranking Override
Before precedence resolution, a hard ranking override checks ranking-specific cues. If matched:
- intent is forced to RANKING
- route_model is forced to C3
- confidence is 1.0
- reason starts with RANK_OVERRIDE

This avoids counting cues hijacking ranking-style questions.

### Multi-hop Confidence
A separate confidence score estimates whether the question is truly multi-hop.

Feature groups:
- Constraint markers
- Distinct operator groups
- Cross-reference markers

Normalized score components:
- s_constraints = min(1, constraint_count / 3)
- s_operators = min(1, distinct_operator_groups / 3)
- s_cross_ref = min(1, cross_ref_count / 2)

Combined score:
- conf_mh = 0.4 * s_constraints + 0.3 * s_operators + 0.3 * s_cross_ref

Promotion rule:
- if conf_mh >= mh_conf_threshold, route to C3 with reason MH_PROMOTION

## Final Routing Rules
The final rules implemented in [utils/intent_router.py](utils/intent_router.py):
- RANKING base intent always routes to C3.
- Any base intent with high enough multi-hop confidence routes to C3.
- Otherwise COUNTING, CALCULATION, COMPARISON, and MULTI_HOP route to C1.
- Unknown fallback routes to C1.

## Integration In Experiment Runner
The experiment runner imports and uses the router in [run_experiment_csv.py](run_experiment_csv.py).

Key integration behavior:
- Router output columns are appended to CSV schema when routing is enabled.
- Shadow mode computes and logs routing fields but executes baseline profile.
- Active routing mode chooses canonical C1 or C3 prompt/input profiles.
- If selected profile input is missing, a fallback to the other profile is attempted and logged.
- Route metadata is written per row:
  - route_intent
  - route_model
  - route_confidence
  - route_reason
  - route_policy_version
  - profile selection and fallback diagnostics

Operational flags are defined in [run_experiment_csv.py](run_experiment_csv.py), including:
- --enable-intent-routing
- --mh-conf-threshold
- --route-policy-version
- --shadow-mode

## Test Coverage Summary
Tests in [tests/test_intent_router.py](tests/test_intent_router.py) verify:
- Ranking override beats counting when both cues appear.
- Non-ranking counting stays in C1 with base reason.
- Multi-hop promotion can escalate non-multi-hop base intents to C3.
- Low-confidence comparison stays base C1.
- Threshold sensitivity: 0.45 promotes while 0.55 may not.
- Determinism: repeated runs produce identical intent, route, confidence, and reason.

## Determinism And Auditability
The component is deterministic because:
- Rule order is explicit.
- Cue lists and precedence are static.
- No randomness or model calls occur in routing.

It is auditable because each decision includes:
- policy_version
- reason string with matched cues or promotion rationale
- optional diagnostics for trigger counts and multi-hop feature values

## Risks And Limitations
- Trigger-list approach can miss semantic variants not present in dictionaries.
- Substring matching may introduce occasional false positives.
- subqtype_hint is currently unused.
- Fixed feature weights and threshold may need recalibration for new data domains.

## Suggested Improvements
1. Use subqtype_hint as a secondary prior in tie or borderline cases.
2. Add confusion-matrix style evaluation against labeled intent data.
3. Expand trigger lexicons using real error analysis.
4. Add tests for negation and ambiguous comparative phrasing.
5. Expose calibrated threshold presets by domain.

## Quick Reference
- Router code: [utils/intent_router.py](utils/intent_router.py)
- Runner integration: [run_experiment_csv.py](run_experiment_csv.py)
- Router tests: [tests/test_intent_router.py](tests/test_intent_router.py)
- Existing router analysis notes: [run_doc/score/minimax/router_eda/router_executive_summary.md](run_doc/score/minimax/router_eda/router_executive_summary.md)
