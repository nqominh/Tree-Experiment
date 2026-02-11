# Prompt for Coding Agent: Write a McNemar Test Script (Two CSV Inputs)

You are a coding agent. Write a **single Python script** that runs a **paired McNemar test** to compare **Exact Match (EM)** between two model runs (baseline vs improved) on the **same questions**.

---

## Goal
Given two CSV files with identical questions (paired by `id`), compute:
- EM rate for baseline and improved
- Discordant counts (n01, n10)
- McNemar test p-value (prefer **exact** McNemar)
- A short interpretation (“improved significantly better” / not)

---

## Inputs
Two CSV paths:
- `--baseline <path>`
- `--improved <path>`

### Required pairing key
Default key column: `id`  
Allow override: `--key_col <name>`

### Two supported file formats
Your script must support either format:

#### Format A (already scored)
Each CSV has:
- `id`
- `em` (0/1)

Allow override: `--em_col <name>`

#### Format B (raw answers)
Each CSV has:
- `id`
- `correct_answer` (gold)
- `model_answer` (prediction)

Allow overrides:
- `--gold_col <name>` (default `correct_answer`)
- `--pred_col <name>` (default `model_answer`)

If EM is not present, compute EM using the scoring rules below.

---

## EM scoring rules (only if needed)
1) Extract a clean final prediction `pred_extracted` from `model_answer`:
   - Prefer content after markers like `Final Answer:` / `[Final Answer]:`
   - Otherwise take the **first non-empty line** before any sections like `# Thought`, `Thought`, `# Solution`, or code fences ```.

2) Normalize strings for EM:
   - lowercase
   - remove commas inside numbers: `101,529 -> 101529`
   - remove `%`
   - normalize unicode dashes to `-`
   - canonicalize numbers so `543` == `543.00` and `6.60` == `6.6`
     - use Python `decimal.Decimal` (avoid float rounding)

3) EM = 1 if normalized pred == normalized gold else 0.

---

## McNemar computation (paired binary test)
After merging baseline and improved on `id`:

Define:
- n01 = count(baseline_em == 0 AND improved_em == 1)
- n10 = count(baseline_em == 1 AND improved_em == 0)
- n00, n11 optional

### Primary test (required)
Use **exact McNemar** via binomial test on discordant pairs:
- n = n01 + n10
- Under H0: P(improve) = P(worsen) = 0.5
- p-value = `scipy.stats.binomtest(min(n01,n10), n, 0.5, alternative="two-sided").pvalue`

Also support one-sided option:
- `--alternative` in `{two-sided, greater, less}`
  - `greater` means improved better: test whether n01 > n10
  - Map to binomtest alternative appropriately

### Secondary output (nice-to-have)
Also report the continuity-corrected chi-square McNemar statistic for reference (optional), but **exact p-value is the main result**.

---

## Outputs
Print to stdout a clear report:

- N baseline rows, N improved rows, N merged
- EM_baseline = mean(em_base)
- EM_improved = mean(em_new)
- Delta_EM = EM_improved - EM_baseline
- n01, n10, discordant total n
- McNemar p-value (exact), alternative, and a short conclusion at alpha=0.05

Also save a machine-readable JSON if user provides:
- `--out_json results.json`

Optional: save merged file with em columns:
- `--out_merged merged.csv`

---

## CLI requirements
Use argparse. Minimum CLI:

- `python mcnemar_test.py --baseline baseline.csv --improved improved.csv`
Optional flags:
- `--key_col id`
- `--em_col em` (Format A)
- `--gold_col correct_answer` (Format B)
- `--pred_col model_answer` (Format B)
- `--alternative two-sided|greater|less` (default two-sided)
- `--alpha 0.05`
- `--out_json <path>` (optional)
- `--out_merged <path>` (optional)

Script should auto-detect:
- If both files contain `em_col`, use Format A
- Else compute EM from gold/pred columns (Format B)
- If required columns missing, raise a helpful error message listing expected columns.

---

## Edge cases & robustness
- If duplicate `id`s exist, keep the first occurrence and warn.
- If merged N is smaller than either input, report how many dropped from each side.
- If n01 + n10 == 0 (no disagreements), report: “McNemar not applicable; outputs identical on EM.”

---

## Dependencies
- pandas
- numpy
- scipy

---

## Quality bar
- Clean, readable code
- Functions: load_and_prepare(), compute_em_if_needed(), mcnemar_exact()
- Clear logging/prints
- No notebooks; must be a runnable `.py`

Deliver exactly one Python file: `mcnemar_test.py`.
