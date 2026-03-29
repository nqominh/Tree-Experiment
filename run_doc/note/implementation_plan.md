# SubQType Router: Classification Heuristics & Pipeline Proposal

## 1. SubQType Distribution (625 questions)

| SubQType | Count | % | Handler |
|---|---|---|---|
| Calculation | 201 | 32.2% | **Process** |
| Counting | 185 | 29.6% | **Process** |
| Comparison | 95 | 15.2% | **Process** |
| Ranking | 84 | 13.4% | **Process** |
| Multi-hop Numerical Reasoning | 60 | 9.6% | **Process** |

> [!IMPORTANT]
> All 5 SubQTypes are "Numerical Reasoning" questions that require computation on table data. However, their computational complexity and answer formats differ significantly, which affects prompt design and evaluation.

---

## 2. Classification Heuristics (Keyword-Based)

Analysis of keyword patterns reveals that 4 out of 5 subtypes have near-perfect keyword signals:

### Tier 1 — High-confidence keyword match (≥95%)

| SubQType | Primary Keywords | Hit Rate | Answer Format |
|---|---|---|---|
| **Counting** | `how many`, `count`, `number of` | 98% | Single integer |
| **Ranking** | `rank`, `top`, `highest`, `lowest`, `order`, `descending`, `ascending` | 98% | Comma-separated list |

### Tier 2 — Strong keyword match (~80%)

| SubQType | Primary Keywords | Hit Rate | Answer Format |
|---|---|---|---|
| **Comparison** | `compare`, `higher`, `lower`, `greater`, `which` | 80% | Entity + optional delta |

### Tier 3 — Moderate keyword match, requires disambiguation

| SubQType | Primary Keywords | Hit Rate | Confusion With | Answer Format |
|---|---|---|---|---|
| **Calculation** | `calculate`, `total`, `sum`, `average`, `mean`, `difference`, `what is the` | 92% | Multi-hop, Counting | Single number |
| **Multi-hop** | `combined`, `if …, what would`, `new percentage`, `identify the year when` | 53% | Calculation | Varies (number, entity, mixed) |

### Key Disambiguation Rules

```
1. "How many" / "Count" → COUNTING  (even if it also says "total")
2. "Rank" / "Top N" / "ascending/descending order" → RANKING
3. "Compare" / "Which is higher/lower" → COMPARISON
4. "If X happens, what would Y" / conditional language → MULTI-HOP
5. Otherwise → CALCULATION (default for "total", "sum", "average", "difference")
```

### Multi-hop vs Calculation disambiguation:
Multi-hop questions have a **chained reasoning** structure: they require completing one intermediate computation before the final answer. Keyword signals:
- Conditional/hypothetical: `"if"`, `"what would"`, `"new percentage"`
- Cross-entity aggregation: `"combined"`, `"across all"`, `"total ... and ..."`
- Temporal comparisons requiring calculation: `"increase between X and Y"`

---

## 3. Handler Assignment: Process vs Baseline Table

> [!NOTE]
> The concept of "handler" here means: does this SubQType need a **processing pipeline** (code-generated answer via pandas/computation), or can it be handled by a **baseline table lookup** (direct LLM prompting on the flat table)?

### Recommendation: All subtypes need **Process** handler

Every SubQType involves numerical reasoning that requires:
1. **Cell retrieval** from the hierarchical table
2. **Arithmetic operations** (sum, average, compare, count, sort)
3. **Multi-step logic** (filter → aggregate → format)

A "baseline table" approach (just showing the raw table to an LLM) would work poorly because the LLM must perform arithmetic, and LLMs are unreliable at exact computation over large tables.

### However, the **prompt strategy** should differ by subtype:

| SubQType | Prompt Strategy | Post-processing |
|---|---|---|
| **Counting** | Emphasize: "Count rows matching condition X" | Parse single integer |
| **Calculation** | Emphasize: "Compute sum/avg/diff of column Y" | Parse single number |
| **Comparison** | Emphasize: "Compare A vs B, return winner + delta" | Parse entity, optional number |
| **Ranking** | Emphasize: "Sort by column Y, return top N" | Parse comma-separated list |
| **Multi-hop** | Emphasize: "Step 1: compute X, Step 2: use X to compute Y" | Parse varies |

---

## 4. Proposed Router Pipeline

### Option A: Keyword-Rule Router (Recommended)
**Cost: Free | Feasibility: High | Simplicity: High**

```
Question text
    │
    ├─ regex: "how many|count|number of" → Counting handler
    ├─ regex: "rank|top \d|ascending|descending|order" → Ranking handler  
    ├─ regex: "compare|higher|lower|greater|which.*more" → Comparison handler
    ├─ regex: "if.*what would|new percentage|combined.*and" → Multi-hop handler
    └─ default → Calculation handler
```

**Priority Order** (first match wins):
1. Counting (most distinctive keywords)
2. Ranking (most distinctive keywords)
3. Comparison (fairly distinctive)
4. Multi-hop (conditional/hypothetical patterns)
5. Calculation (catch-all default)

**Estimated accuracy**: ~90-95% based on keyword analysis.

### Option B: LLM Classifier Router
**Cost: ~$0.001/question | Feasibility: Medium | Simplicity: Medium**

Use a lightweight LLM call (e.g., Gemini Flash) with a system prompt:
```
Classify this table question into one of: Counting, Calculation, Comparison, Ranking, Multi-hop.
Only respond with the category name.
Question: {question}
```

**Estimated accuracy**: ~95-98%, but adds latency + cost per question.

### Option C: Hybrid (Recommended for production)
**Cost: ~$0.0005 avg | Feasibility: High | Simplicity: High**

1. Apply keyword rules first (Option A)
2. If confidence is low (e.g., no strong keyword match), fall back to LLM classifier (Option B)
3. In practice, ~85% of questions would be routed by keywords alone, saving LLM calls

---

## 5. Proposed Changes

### Router Module

#### [NEW] [question_router.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/question_router.py)

A Python module implementing the keyword-rule router with an optional LLM fallback:

- `classify_subqtype(question: str) -> str` — main classification function
- `_keyword_classify(question: str) -> tuple[str, float]` — rule-based with confidence
- `_llm_classify(question: str) -> str` — optional LLM fallback
- `get_handler(subqtype: str) -> callable` — map subtype to handler function

---

## 6. Verification Plan

### Automated Test
Run the router against all 625 labeled questions and measure classification accuracy:

```bash
python -m pytest tests/test_question_router.py -v
```

The test will:
1. Load all questions from [tests/questions_clean_audit copy.jsonl](file:///c:/Users/nqmi/Downloads/Tree-Experiment/tests/questions_clean_audit%20copy.jsonl)
2. Run each through `classify_subqtype()`
3. Compare against the ground-truth `SubQType` field
4. Assert overall accuracy ≥ 90%
5. Print per-subtype precision/recall
