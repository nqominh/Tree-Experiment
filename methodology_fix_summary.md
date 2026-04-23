# Methodology Fix Summary

## Goal
Push the methodology section from "strong" to "fully defensible" by fixing the last high-impact issues without expanding the study scope.

## Core focus
The section is already much better. The remaining work is not to redesign the study, but to tighten the evaluation and audit logic so the chapter becomes fully auditable and harder to challenge in defense.

## Highest-priority fixes

### 1. Give judges access to table evidence
The current text says judges receive the question, gold answer, and model answer. That is not enough for semantic adjudication in TableQA, because judges need access to the relevant table evidence to verify whether a non-exact-match answer is still correct.

**Fix**
State explicitly that each judge receives:
- the question
- the relevant cleaned table evidence
- the gold reference answer
- the model answer
- a fixed judge prompt

**Why this matters**
Without table evidence, the judge stage looks like answer-to-answer comparison rather than evidence-based correctness checking.

---

### 2. Make exact-match normalization more conservative
The current normalization removes symbols such as `%`, `$`, punctuation, and articles. That is too aggressive because it can collapse semantically different answers into the same normalized form.

**Fix**
Keep only safe formatting normalization:
- trim leading/trailing whitespace
- lowercase
- remove outer quotes
- remove a trailing sentence period
- collapse repeated whitespace
- remove thousands separators within numeric strings
- canonicalize numerically equivalent forms such as `7.0` and `7`

Preserve symbols that may affect meaning, including:
- decimal points
- minus signs
- percent markers
- currency symbols
- date separators
- range markers

**Why this matters**
Exact Match should normalize surface form only, not alter answer meaning.

---

### 3. Specify what happens after a schema audit flag
The section now says tables failing width, leaf-count, or path-uniqueness checks are flagged for audit. That is better, but it still does not say what happens next.

**Fix**
Add a disposition rule, for example:
- flagged items are manually inspected before final scoring
- repaired or excluded items are counted and reported explicitly
- if no items were excluded, say so

**Why this matters**
A reviewer will want to know whether flagged items were repaired, excluded, or kept unchanged.

---

## Recommended wording direction

### Evaluation rationale
Keep the current story:
- preliminary audit showed EM and F1 were informative but insufficient alone
- therefore the final protocol uses lexical metrics first, then semantic adjudication
- after that decision, the same finalized protocol was applied consistently across all conditions

This is a strong and honest methodological story.

### Metric framing
Keep EM and F1 as:
- automatic lexical diagnostics
- not complete correctness criteria

Keep corrected accuracy as:
- EM first-stage scoring
- judge adjudication for EM-failed cases

---

## Minimal patch set
If you want the smallest set of edits with the highest impact, do these three only:

1. revise judge inputs so they include table evidence
2. replace aggressive EM normalization with conservative normalization
3. add one sentence stating the audit disposition rule for flagged tables

---

## What not to change
Do not reopen the whole methodology. The following parts are now already in good shape:
- RQ1 and RQ2 alignment
- executed-condition framing
- C0 as external reference only
- C1 vs C3 and C3 vs C5 contrast logic
- McNemar + paired bootstrap plan
- claim boundary statement

---

## Practical target
The focus is not to satisfy every minor wording preference. The focus is to remove the last issues that could seriously weaken:
- validity of corrected accuracy
- reproducibility of scoring
- auditability of the schema pipeline

Addressing those remaining concerns should be enough to make the section feel thesis-defense ready.
