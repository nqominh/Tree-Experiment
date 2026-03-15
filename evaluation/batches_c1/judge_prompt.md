# LLM Judge Prompt

You are grading free-form numerical reasoning answers.

For each item independently, read `question`, `gold_answer`, and `model_answer` from the batch CSV.
Write your decision in the `judgement` column using one label per row:
- CORRECT
- INCORRECT
- UNCERTAIN

## Rules
1. Judge each item independently; do not let one item influence another.
2. CORRECT if mathematically equivalent: 62.6 = 62.60 = 62.6%.
3. CORRECT if same value, different format: 1,000 = 1000, $7.50 = 7.5.
4. CORRECT if rounded to 2 decimal places and matches gold.
   For 2-decimal checks, treat absolute difference < 0.005 as equivalent after rounding.
5. CORRECT if answer contains the right value even with extra explanation.
6. INCORRECT if the number is wrong.
7. INCORRECT if partial answer when full answer is required.
8. UNCERTAIN only if correctness genuinely cannot be determined from the gold answer.

## How To Use
1. Open one `batch_XX_items.csv` file.
2. Paste this prompt into the LLM and provide the CSV content.
3. Ask the LLM to return the same CSV with `judgement` filled.
4. Save the LLM output CSV to your judge output folder.
