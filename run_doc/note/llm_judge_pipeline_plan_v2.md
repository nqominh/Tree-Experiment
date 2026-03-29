# LLM-as-Judge Evaluation Pipeline — Script Generation Plan (v2)

## Context

Preprocessing and normalization are already done externally.
The input xlsx files already have an `EM` column where:
- `EM == 1` or `EM == True` → already marked correct, skip
- `EM == 0` or `EM == False` → needs judge evaluation

This pipeline starts from extracting `EM == 0` rows and sends them
to two independent LLM judges via manual chatbot UI (Claude + ChatGPT).

Expected volume after extraction: **< 100 items** → use 2 batches of ~50.

---

## Input File Specification

**File:** one or more `.xlsx` files, each with multiple sheets.

**Relevant columns per sheet (column names are exact):**

| Column | Type | Description |
|---|---|---|
| `id` | float/int | Question ID (cast to int) |
| `question` | str | The question asked |
| `correct_answer` | str | Gold label answer |
| `model_answer` | str | Model's free-form answer |
| `EM` | bool/float/int | Exact match flag — `1`/`True` = correct, `0`/`False` = needs judge |

Other columns (`full_response`, `full_prompt`, `filename`, `EM_base`, `EM_sem`, etc.)
should be **ignored** — not written to the master CSV.

**Note:** Some sheets may not have all required columns. Skip those sheets with a warning.

---

## Output File Specification

All scripts write to or read from a **master evaluation CSV**:
`evaluation_master.csv`

Columns:

| Column | Type | Description |
|---|---|---|
| `item_id` | int | From `id` column |
| `sheet_name` | str | Source sheet name |
| `source_file` | str | Source xlsx filename |
| `question` | str | Question text |
| `gold_answer` | str | From `correct_answer` |
| `model_answer` | str | From `model_answer` |
| `batch_id` | str | e.g. `batch_01` — filled by Script 2 |
| `judge1_label` | str | `CORRECT` / `INCORRECT` / `UNCERTAIN` / empty |
| `judge2_label` | str | same |
| `final_label` | str | `CORRECT` / `INCORRECT` / `HUMAN_REVIEW` — filled by Script 3 |
| `adjudication_source` | str | `majority_vote` / `human_review` — filled by Script 3 |

---

## Script 1 — `01_extract.py` (EM==0 Extractor)

### Purpose
Read all sheets from input xlsx files, extract only rows where `EM == 0`,
and write them to `evaluation_master.csv` for judge evaluation.

### CLI
```
python 01_extract.py --input results/*.xlsx --output evaluation_master.csv
```

### Logic

1. For each xlsx file, iterate over all sheets
2. For each sheet, check that required columns exist: `id`, `question`, `correct_answer`, `model_answer`, `EM`
   - If any required column is missing: skip sheet, print warning
3. Filter rows where `EM` is falsy:
   - `EM == 0`, `EM == 0.0`, `EM == False`, `EM == "False"`, `EM == "0"`
   - Cast to comparable type before checking — do not assume dtype
4. For each extracted row, write to master CSV with columns:
   `item_id`, `sheet_name`, `source_file`, `question`, `gold_answer`, `model_answer`
   Leave `batch_id`, `judge1_label`, `judge2_label`, `final_label`, `adjudication_source` empty
5. Cast `id` to int (source may be float like `20.0`)
6. Deduplicate by `item_id` — if same `item_id` appears in multiple sheets, keep first and warn

### Output
- Write `evaluation_master.csv`
- Print summary:
  ```
  === EXTRACTION SUMMARY ===
  Files processed:    N
  Sheets processed:   N
  Sheets skipped:     N  (missing columns)
  EM==1 rows skipped: N
  EM==0 rows extracted: N  ← these go to judges
  Duplicates removed: N
  Output: evaluation_master.csv
  ```

---

## Script 2 — `02_format_batches.py` (Batch Formatter)

### Purpose
Read `evaluation_master.csv`, split all rows into batches of 50,
and write numbered text files ready to paste into a chatbot UI.

### CLI
```
python 02_format_batches.py --input evaluation_master.csv --batch-size 50 --output-dir batches/
```

### Logic

1. Read all rows from `evaluation_master.csv`
2. Sort by `item_id`
3. Split into chunks of `--batch-size` (default 50)
4. For each chunk:
   - Write `batches/batch_01.txt`, `batches/batch_02.txt`, etc.
   - Update `batch_id` column in `evaluation_master.csv` for those rows
5. Write `batches/batch_index.csv` with columns: `item_id`, `batch_id`
   (used by Script 3 to validate outputs)

### Batch File Format (exact)

Each `.txt` file must contain:

```
===== JUDGE PROMPT — BATCH 01 of 02 =====

You are grading free-form numerical reasoning answers.

For each item independently, read the question, gold_answer, and model_answer.
Return one label per item: CORRECT, INCORRECT, or UNCERTAIN.

Rules:
1. Judge each item independently — do not let one item influence another.
2. CORRECT if mathematically equivalent: 62.6 = 62.60 = 62.6%.
3. CORRECT if same value, different format: 1,000 = 1000, $7.50 = 7.5.
4. CORRECT if rounded to 2 decimal places and matches gold.
5. CORRECT if answer contains the right value even with extra explanation.
6. INCORRECT if the number is wrong.
7. INCORRECT if partial answer when full answer is required.
8. UNCERTAIN only if correctness genuinely cannot be determined from the gold answer.

Output format — one line per item, nothing else:
<item_id> | <CORRECT or INCORRECT or UNCERTAIN>

Example output:
20 | INCORRECT
22 | INCORRECT
25 | CORRECT

=== ITEMS ===

--- Item 20 ---
Question: Rank the age groups by the percentage of their population employed, starting from the highest percentage. Provide the top two age groups.
Gold Answer: 35 to 39 years, 35 to 44 years
Model Answer: 45 to 49 years (81.7%) and 35 to 39 years (81.6%)

--- Item 22 ---
Question: Considering individuals aged 16 years and over, calculate the total percentage of the civilian non-institutional population either employed or unemployed.
Gold Answer: 63.90
Model Answer: 62.6

[... continue for all items in batch ...]
```

### Print on Completion

```
=== BATCH SUMMARY ===
Total items:    N
Batches created: N  (batch size: 50)
Output dir: batches/

Next steps:
  Judge 1 (Claude):
    1. Open batches/batch_01.txt — copy full content
    2. Paste into a NEW conversation at claude.ai
    3. Save response as: judge_outputs/claude/batch_01.txt
    4. Repeat for batch_02.txt in a NEW conversation

  Judge 2 (ChatGPT):
    1. Open batches/batch_01.txt — copy full content
    2. Paste into a NEW conversation at chatgpt.com
    3. Save response as: judge_outputs/gpt/batch_01.txt
    4. Repeat for batch_02.txt in a NEW conversation

  Then run: python 03_parse_outputs.py
```

Also update `batch_id` column in `evaluation_master.csv` before exiting.

---

## Script 3 — `03_parse_outputs.py` (Output Parser + Aggregator)

### Purpose
Parse raw chatbot output text files, write verdicts back into `evaluation_master.csv`,
apply the aggregation rule, compute Cohen's Kappa, and output final results.

This script combines parsing AND aggregation into one step since the volume is small.

### CLI
```
python 03_parse_outputs.py \
  --judge1-dir judge_outputs/claude/ \
  --judge2-dir judge_outputs/gpt/ \
  --master evaluation_master.csv \
  --output final_results.csv
```

### Parsing Logic

For each `.txt` file in `--judge1-dir` and `--judge2-dir`:

1. Read file line by line
2. For each line, attempt to match these patterns in order:
   - `<int> | <LABEL>` (primary format)
   - `<int>: <LABEL>`
   - `Item <int> — <LABEL>`
   - `Item <int>: <LABEL>`
   - `<int>. <LABEL>`
   - where LABEL is one of `CORRECT`, `INCORRECT`, `UNCERTAIN` (case-insensitive)
3. If no pattern matches: skip line, log warning
4. Write matched `item_id` → `judge1_label` or `judge2_label` in `evaluation_master.csv`
5. Do not overwrite existing non-empty labels unless `--overwrite` flag is passed

**Validation per batch file:**
- Load `batches/batch_index.csv` to know which `item_id`s belong to which batch
- After parsing each batch file, check all expected `item_id`s are present
- If any are missing: print warning with the missing IDs — do NOT fill a default
- Missing items → leave label empty → they will go to `HUMAN_REVIEW`

### Aggregation Rule (applied after parsing both judges)

For each row in `evaluation_master.csv`:

```
1. Both judge1 and judge2 are CORRECT
   → final_label = CORRECT
   → adjudication_source = majority_vote

2. Both judge1 and judge2 are INCORRECT
   → final_label = INCORRECT
   → adjudication_source = majority_vote

3. All other cases (disagreement, any UNCERTAIN, any missing label)
   → final_label = HUMAN_REVIEW
   → adjudication_source = human_review
```

### Cohen's Kappa

- Compute only on rows where both `judge1_label` and `judge2_label` are non-empty
- Use `sklearn.metrics.cohen_kappa_score`
- Labels treated as categorical: `CORRECT`, `INCORRECT`, `UNCERTAIN`
- Interpretation:
  - κ < 0.40 → "Fair — consider reviewing judge prompt"
  - κ 0.41–0.60 → "Moderate"
  - κ 0.61–0.80 → "Substantial — acceptable for thesis"
  - κ > 0.80 → "Almost perfect"

### Outputs

**1. `final_results.csv`**
Full master CSV with all columns filled in.

**2. `human_review_list.csv`**
Only `HUMAN_REVIEW` rows, columns:
`item_id`, `question`, `gold_answer`, `model_answer`, `judge1_label`, `judge2_label`
Sorted by `item_id`.

**3. `summary_report.txt`**
```
=== EVALUATION SUMMARY ===

Total EM==0 items evaluated:   N

Judge parsing:
  Judge 1 (Claude) parsed:     N  items  (N missing → HUMAN_REVIEW)
  Judge 2 (GPT) parsed:        N  items  (N missing → HUMAN_REVIEW)

Cohen's Kappa (J1 vs J2):      X.XX  [interpretation]

Agreement breakdown:
  Both CORRECT:                N
  Both INCORRECT:              N
  Disagreed / Uncertain:       N  → HUMAN_REVIEW

Final labels:
  CORRECT  (majority vote):    N  (X%)
  INCORRECT (majority vote):   N  (X%)
  HUMAN_REVIEW:                N  (X%)

Human review list saved to: human_review_list.csv
Final results saved to:     final_results.csv
```

---

## File Structure Expected

```
project/
├── 01_extract.py
├── 02_format_batches.py
├── 03_parse_outputs.py
├── results/
│   └── gemini-3_1.xlsx            ← input result files
├── evaluation_master.csv          ← created by script 1, updated by 2 and 3
├── batches/
│   ├── batch_index.csv            ← created by script 2
│   ├── batch_01.txt               ← paste into chatbot
│   └── batch_02.txt
├── judge_outputs/
│   ├── claude/
│   │   ├── batch_01.txt           ← paste Claude's response here
│   │   └── batch_02.txt
│   └── gpt/
│       ├── batch_01.txt           ← paste ChatGPT's response here
│       └── batch_02.txt
├── final_results.csv              ← created by script 3
├── human_review_list.csv          ← created by script 3
└── summary_report.txt             ← created by script 3
```

---

## Dependencies

```
pandas
openpyxl
scikit-learn
argparse
pathlib
re
```

Install: `pip install pandas openpyxl scikit-learn`

---

## Error Handling Requirements

All scripts must:
- Handle missing required columns: skip sheet, print warning, continue
- Handle sheets with 0 or 1 data rows: skip, print warning
- Cast `id` column from float to int safely (`int(float(val))`)
- Handle `None` / `NaN` in any column: treat as empty string
- Never crash on a single bad row — skip and log
- Print clear per-file, per-sheet progress messages

---

## Notes For The Agent

- Scripts run in order: `01` → `02` → `03`
- Script `02` both reads AND updates `evaluation_master.csv` (adds `batch_id` column)
- Script `03` both reads AND updates `evaluation_master.csv` (adds judge labels + final labels)
- Script `03` can be run incrementally:
  - run once with only `--judge1-dir` to fill judge1 labels
  - run again with `--judge2-dir` to fill judge2 labels and trigger aggregation
  - aggregation only runs when both judge columns are sufficiently populated
- Use `argparse` for all CLI arguments with sensible defaults
- Use f-strings and clear variable names
- Add `if __name__ == "__main__":` block to each script
- Target Python 3.10+
- Default batch size is 50
