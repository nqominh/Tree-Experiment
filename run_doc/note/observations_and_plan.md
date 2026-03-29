# Code Review: Schema Injection Pipeline — Observations & Improvement Plan

## Pipeline Overview

```
HTML table → openpyxl Workbook → Merge expansion → Schema/Data split
    → IndexTree (col headers) + BodyTree (data rows)
    → FeatureTree → Prompt (indented schema + HTML) → Gemini API → Extract answer → EM score
```

---

## Observations & Flaws

### 1. Schema Extraction is Fragile

#### 1a. Header/Data Split Heuristics Break on Complex Tables

[split_utils.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/utils/split_utils.py) uses two detection modes:

- **Merge-based**: only looks at row 1 merges — misses tables where merges start on row 2+
- **Content-based fallback**: uses hardcoded thresholds (80% same value = title row, ≥3 numeric cells = data row) that fail on:
  - Tables with text-heavy data columns (e.g., category names as answers)
  - Tables where header rows contain numbers (e.g., year headers like "2020", "2021")
  - Tables with mixed numeric/text data rows

The [_find_schema_height_by_content](file:///c:/Users/nqmi/Downloads/Tree-Experiment/utils/split_utils.py#87-104) only scans up to row 15 — exotic tables with many header rows will be misclassified.

#### 1b. Row Structure Detection Uses Only Column Width

[split_schema_column](file:///c:/Users/nqmi/Downloads/Tree-Experiment/utils/split_utils.py#L166-L197) detects row headers by finding the first numeric column. This fails when:
- Row labels contain numbers (e.g., years as row headers)
- The first data column has non-numeric values

#### 1c. Three-Strategy Fallback Silently Swallows Errors

[tree_builder.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py#L126-L138) catches **all** exceptions with bare `except Exception: pass`. If the "direct" strategy produces a *wrong* tree (not an error, just incorrect headers), the pipeline happily proceeds with garbage. There's no validation that the extracted schema actually matches the HTML table.

#### 1d. Temp Files Are Never Cleaned Up

`tempfile.mktemp()` creates filenames but doesn't clean them up. Every table processed leaks a `.xlsx` file on disk.

---

### 2. Prompt Design Issues

#### 2a. Information Redundancy — Schema + Full HTML

The EVIDENCE_PROMPT sends **three representations** of the same table:
1. `[COLUMN STRUCTURE]` — indented tree
2. `[ROW STRUCTURE]` — indented tree  
3. `[TABLE HTML]` — the entire raw HTML

This means the LLM receives the header information **twice** (once in the schema, once in the HTML). This wastes tokens and can cause confusion when the extracted schema doesn't perfectly match the HTML (which happens often due to extraction bugs).

> [!IMPORTANT]
> The schema extraction only adds value if it's **correct**. When it's wrong, it actively misleads the model. A wrong schema is worse than no schema at all.

#### 2b. No Subtype-Aware Prompting

All five subtypes (Calculation, Counting, Comparison, Ranking, Multi-hop NR) use the exact same prompt template. But these subtypes require very different reasoning strategies:
- **Counting** needs scanning and enumeration — the prompt examples never show this
- **Ranking** needs sorting — the prompt has no ranking example
- **Multi-hop** needs chained lookups across multiple cells — the examples only show single-hop or simple arithmetic

#### 2c. Examples Don't Use Real Tables

The prompt examples in sections 5 are abstract (they reference "Average hours per day" without an actual HTML table). The model never sees a worked example with **real HTML** → **correct answer**. This means it doesn't learn the mapping from messy HTML structure to correct cell extraction.

#### 2d. Fixed 6-Step Pipeline is Overkill for Simple Lookups

For a simple "What is the value of X?" question, forcing 6 steps of reasoning adds unnecessary output tokens and can cause the model to overthink and make errors. The BASE_PROMPT_TEMPLATE with 5 simpler steps might actually be better for lookup questions.

---

### 3. Answer Extraction & Scoring Issues

#### 3a. Normalization is Lossy

[normalize()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py#L233-L241) strips `$`, `%`, `,` and removes all punctuation. This causes false negatives:
- **"$1,234"** and **"1234"** match (good)
- But **"1,234.56"** rounds to **"1234.56"** while the label might be **"1234.6"** — mismatch due to rounding policy  
- **"North America"** and **"north america"** match — but **"N. America"** won't match because punctuation is stripped differently

#### 3b. [_process_decimal](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py#225-231) Rounds to 2 Decimals Always

This is problematic when the question asks for a different precision (e.g., "round to 1 decimal place" or "to the nearest integer"). The normalization shouldn't impose a fixed rounding.

#### 3c. [extract_answer](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py#192-223) Fallback is Dangerous

If no `[Final Answer]` marker is found, it falls back to the **last non-empty line** of the entire response. This means any trailing text (e.g., a validation note) gets treated as the answer.

---

### 4. Engineering Quality Issues

#### 4a. Silent Error Swallowing Everywhere

- [tree_output.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_output.py): every function wraps in `try/except: return ""` or `return {}`
- [tree_builder.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py): `except Exception: pass` on each strategy
- Result: bugs in the tree-building code are invisible. You'll see wrong outputs but never know why.

#### 4b. No Experiment Tracking

- Results go to a single CSV with no run metadata (which prompt template, model, temperature, strategy used, token count)
- No way to A/B test different prompts or schemas without manually renaming files
- Can't easily compare "schema+HTML" vs "HTML-only" vs "JSON" results side by side

#### 4c. [html2workbook](file:///c:/Users/nqmi/Downloads/Tree-Experiment/utils/sheet_utils.py#37-94) → Save to disk → Reload → Process

The pipeline saves to a temp `.xlsx` file, then reloads it from disk, just to get an openpyxl sheet with expanded merges. This intermediate I/O is unnecessary — the merge expansion could work directly on the in-memory workbook.

#### 4d. No Logging of Which Strategy Succeeded

[prepare_tables.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/prepare_tables.py) prints the strategy name, but [run_experiment_csv.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py) doesn't record it in the CSV. You can't analyze whether "direct" vs "fixed" vs "structured" correlates with accuracy.

---

### 5. Experimental Design Gaps

#### 5a. No Ablation Study

You have 4 prompt variants (BASE, EVIDENCE, JSON, HTML) but no systematic comparison. Without ablation, you can't answer:
- Does schema injection actually help vs. raw HTML alone?
- Does the 6-step pipeline help vs. the simpler BASE template?
- Does JSON format help vs. indented text?

#### 5b. No Error Analysis Pipeline

When questions are answered wrong, there's no tool to categorize WHY:
- Schema extraction error (wrong headers)?
- Cell lookup error (right headers, wrong cell)?
- Arithmetic error (right values, wrong calculation)?
- Normalization mismatch (right answer, wrong format)?

---

## Improvement Plan

### Priority 1: Quick Wins (Low effort, high impact)

| # | Change | Expected Impact |
|---|--------|-----------------|
| 1 | **Add schema validation**: After extracting the tree, verify that leaf column count matches actual HTML column count. Log mismatches. | Catch silent extraction errors |
| 2 | **Record strategy + token count in CSV**: Add `strategy` and `prompt_tokens` columns to output | Enable strategy-accuracy analysis |
| 3 | **Fix answer normalization**: Don't force 2-decimal rounding; instead, try exact match first, then normalized match | Reduce false negatives |
| 4 | **Clean up temp files**: Use `tempfile.NamedTemporaryFile(delete=True)` or a context manager | Prevent disk leak |

### Priority 2: Prompt Engineering (Medium effort, high impact)

| # | Change | Expected Impact |
|---|--------|-----------------|
| 5 | **Ablation: HTML-only baseline** — Run the SIMPLE_PROMPT + raw HTML (no schema injection) on same 100 questions to establish a baseline. If HTML-only matches schema+HTML accuracy, the schema extraction adds complexity for no benefit. | Critical data point for deciding the whole approach |
| 6 | **Subtype-specific examples** — Add 1 example each for Counting, Ranking, and Multi-hop in the prompt. These subtypes likely have lower accuracy due to no demonstration. | Improve worst-performing subtypes |
| 7 | **Remove redundant schema when HTML is present** — Either use schema+JSON (no HTML) OR HTML-only (no schema). Sending both wastes tokens and risks schema/HTML disagreement. | Save ~30% prompt tokens, reduce confusion |

### Priority 3: Robust Schema Extraction (Higher effort)

| # | Change | Expected Impact |
|---|--------|-----------------|
| 8 | **Use `<th>` tag semantics for split**: [html2workbook](file:///c:/Users/nqmi/Downloads/Tree-Experiment/utils/sheet_utils.py#37-94) already tracks which cells came from `<th>` via `th_map`. Use this directly instead of heuristic detection. | Much more reliable header detection |
| 9 | **Validate tree against HTML**: After building the tree, compare [get_flatten_schema()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/table2tree/feature_tree.py#114-138) leaf count against actual `<th>` count in the last header row | Catch structural mismatches |
| 10 | **Add error categorization script**: For each wrong answer, classify as schema_error / lookup_error / arithmetic_error / format_error | Guide future improvements to highest-impact area |

### Priority 4: Infrastructure (Ongoing)

| # | Change | Expected Impact |
|---|--------|-----------------|
| 11 | **Experiment tracker**: Add a `runs.jsonl` that records each run's config (prompt, model, temperature, strategy, date, accuracy) | Enable systematic comparisons |
| 12 | **Remove bare except blocks**: Replace `except Exception: pass` with proper logging | Catch bugs early |

---

## Recommended Next Steps

1. **Run ablation first** (Priority 2, #5) — this answers the fundamental question: *does schema injection help at all?*  
2. Based on the result:
   - If HTML-only ≈ schema+HTML → simplify the pipeline, drop tree-building complexity
   - If schema+HTML >> HTML-only → invest in robust extraction (Priority 3)
3. Either way, implement Priority 1 fixes immediately — they're low-risk and improve observability
