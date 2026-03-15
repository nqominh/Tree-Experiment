# Evaluation Metrics Reference — Thesis Notes

## 1. Cohen's Kappa (κ)

### What it is
A chance-corrected measure of agreement between **exactly 2 raters**. It asks:

> *"How much better are two reviewers agreeing compared to if they just randomly guessed?"*

### Formula
```
κ = (P_observed - P_expected) / (1 - P_expected)
```

- **P_observed** — Actual % agreement between the two reviewers  
- **P_expected** — % agreement we'd expect purely by chance, given each reviewer's class distribution

### Why not just use % agreement?
If 90% of items are "Match", both reviewers could blindly label everything "Match" and achieve 90% agreement by accident. Kappa corrects for this inflation.

### Landis-Koch Scale
| κ | Strength | Example uses |
|---|---|---|
| < 0.20 | Slight | |
| 0.21–0.40 | Fair | |
| 0.41–0.60 | **Moderate** | ← **You are here (κ = 0.4762)** |
| 0.61–0.80 | Substantial | Medical diagnosis |
| 0.81–1.00 | Almost perfect | |

### Your Application
- **Raters:** Reviewer 1 (R1) and Reviewer 2 (R2)  
- **Label space:** 3 classes — `Match`, `Correction`, `No Info`  
- **N:** 299 annotations (filtered up to ID 1258)  
- **Result: κ = 0.4762 (Moderate)**

**Why "Moderate" is acceptable here:**  
Your task requires free-text judgment (is this answer correct or not?). Unlike binary tasks, free-text assessment inherently produces lower Kappa scores. Published NLP annotation papers routinely report and accept κ in the 0.4–0.6 range for this reason.

---

## 2. Fleiss' Kappa

### What it is
An extension of Cohen's Kappa for **3 or more raters**. Cohen's is pairwise only — you *cannot* use it with 3+ reviewers.

Fleiss' Kappa aggregates agreement across all rater pairs simultaneously.

### When you need it
Once **Reviewer 3** finishes:
- Switch from Cohen's Kappa (2 raters) to Fleiss' Kappa (3 raters)
- Using Cohen's with 3 raters is a **methodological error** reviewers will catch

### How it differs from Cohen's
| | Cohen's | Fleiss' |
|---|---|---|
| Raters | Exactly 2 | 3 or more |
| Method | Pairwise | Aggregated across all raters |
| Your status | ✅ Calculated (κ = 0.4762) | ⏳ Pending Reviewer 3 |

---

## 3. Agreement Rate (P_observed)

Your raw agreement before chance correction:

```
P_observed = agreements / total = 254 / 299 = 84.95%
```

Report alongside Kappa — reviewers expect to see both.

---

## 4. Confusion Matrix (Reviewer 1 × Reviewer 2)

```
                    Reviewer 2
                 MATCH  CORR  NO_INFO
R1     MATCH     233    19    2
       CORR       20    22    0
       NO_INFO     0     0    3
```

**How to read it:**
- Diagonal cells (233, 22, 3) = exact agreements
- Off-diagonal = disagreements
- Biggest source of disagreement: **Match ↔ Correction** (19 + 20 = 39 cases)

---

## 5. Experiment Metrics

### Exact Match (EM)
Your primary metric for model evaluation.

```
EM = 1   if model_answer == correct_label (exact string)
EM = 0   otherwise
```

**Known limitations:**
- "1,234" ≠ "1234" — same value, counted as wrong
- "99.86%" ≠ "99.86" — units cause false failures
- The 6-step C5 prompt is especially prone to this because the model's verbose output may format answers differently

**Fix coming:** Relaxed EM with numerical tolerance and unit stripping.

### Accuracy
```
Accuracy = sum(EM) / total_questions * 100
```

Current results:
| Condition | Accuracy |
|---|---|
| C1 (Vanilla) | **66.9%** |
| C3 (Schema Only) | **66.1%** |
| C5 (Full Method) | ~58% (may be EM metric artifact) |

### McNemar's Test
- A **paired** statistical test for comparing two binary classifiers on the same test set
- Tests whether the *pattern* of errors differs between two conditions, not just the overall numbers
- Required to prove statistical significance of accuracy differences
- p < 0.05 means the difference is not by chance

```python
# Command:
.venv\Scripts\python.exe score/mcnemar_test.py --file1 score/C1_vanilla.csv --file2 score/C5_full.csv
```

---

## 6. Questions for Tomorrow's Meeting

These are questions that came up today during our conversation. Bring these to your supervisor.

### On Methodology
1. **Is κ = 0.4762 acceptable?** Do you need to justify this number in a footnote, or is it expected for free-text annotation tasks?
2. **Can you publish with only 2 reviewers, or do you need Reviewer 3 before submission?** What is the minimum for Fleiss' Kappa to be required?
3. **Is your 251-question subset biased?** By filtering to only questions where both reviewers agree, are you inadvertently selecting "easier" questions (the ones with unambiguous answers)?

### On Experiment Design
4. **Is "Cleaned HTML" a valid baseline?** You are stripping `<head>`, `<style>`, and all non-table content before feeding to Gemini. Is HTML preprocessing a confound or a justified pre-step?
5. **If C3 (Schema) ≈ C1 (Vanilla), is your thesis dead?** Or is a null result still publishable in the benchmarking framing?
6. **Should Gemini's internal CoT (chain-of-thought thinking tokens) count as a confound in your baseline?** Since Gemini 2.5 Pro reasons internally, your "zero-shot" baseline is already doing implicit reasoning — what does your C2 (explicit CoT) actually test?

### On Results
7. **How do you handle the EM metric failure for C5?** If the 6-step pipeline formats the answer differently (e.g., includes a unit or uses commas), should you manually inspect these failures and exclude formatting errors from the score?
8. **What is the expected accuracy range for this task?** Is 66% good, average, or poor for RealHiTBench?

### On Publication Direction
9. **Is "Benchmarking Gemini on RealHiTBench" a sufficient contribution for a workshop paper?** Do you need to add another model (e.g., GPT-4o) for comparison?
10. **What is the target venue?** ACL SRW, EMNLP workshop, or a local/regional conference?
