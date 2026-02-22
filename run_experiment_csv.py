"""
run_experiment_csv.py -- Stage 2: Call Gemini API and record results to CSV

Reads:
  - tests/questions.jsonl          (questions + labels)
  - table_inputs/<table_id>.txt    (col structure, row structure, HTML)

Calls Gemini API for each question using the structured prompt from CURRENT_PROMPT.md
Writes one CSV row per question immediately (safe against crashes).

CSV columns:
  id | question | correct_answer | model_answer | full_response | full_prompt | filename | EM

Usage:
  set GEMINI_API_KEY=your_key
  python run_experiment_csv.py
  python run_experiment_csv.py --limit 5 --delay 1.5 --model gemini-2.0-flash
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT   = Path(__file__).resolve().parent
QUESTIONS_PATH = PROJECT_ROOT / "tests" / "questions.jsonl"
TABLE_INPUTS   = PROJECT_ROOT / "table_inputs"
OUTPUT_CSV     = PROJECT_ROOT / "experiment_results.csv"

CSV_COLUMNS = ["id", "question", "correct_answer", "model_answer",
               "full_response", "full_prompt", "filename", "EM"]


# ---------------------------------------------------------------------------
# Prompt builder  (follows CURRENT_PROMPT.md structure)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """\
# 1. TASK CONTEXT
You are a precise table reasoning system. You are given a structured table with explicit column and row hierarchies, and you must answer a question strictly from the table data.

---

# 2. TONE CONTEXT
Be analytical, careful, and deterministic. Avoid speculation. Do not hallucinate values. The table is the ONLY source of truth.

---

# 3. BACKGROUND DATA

## How to Read the Table Structure

**[COLUMN STRUCTURE]** lists all column headers as an indented tree.
Each level of indentation (2 spaces) means a sub-column under the parent above it.
Full column path example: `Average hours per day > Married mothers > Employed full time`

**[ROW STRUCTURE]** lists all row labels as an indented tree.
Same indentation rules apply. Deeper-indented rows are sub-categories of the row above.
Full row path example: `Household activities > Housework`

**[TABLE HTML]** is the raw HTML. Use it to look up actual cell values after you identify the correct row and column from the structures above.

---

# 4. DETAILED TASK DESCRIPTION & RULES

Step-by-step:
1. Read [COLUMN STRUCTURE] to find the column(s) relevant to the question. Note the full path.
2. Read [ROW STRUCTURE] to find the row(s) relevant to the question. Note the full path.
3. Locate the cell at the intersection in the HTML table.
4. Perform any required calculation (average, sum, difference, percentage, etc.).
5. Output the final answer.

Strict Rules:
- Do NOT use external knowledge.
- Do NOT assume or interpolate missing values. If a cell is empty or "No contacts" treat it as unavailable.
- If the answer is not derivable from the table, respond: [Final Answer]: Not answerable
- Numbers: output only the number. No units unless explicitly shown in table.
- Text: match table wording exactly when possible.
- Do NOT add any explanation after [Final Answer]:.

---

# 5. EXAMPLES

Example 1 — Multi-level column lookup:
Column: `Average hours per day > Married mothers > Employed full time`
Row: `Household activities > Housework`
Question: How many hours do employed full-time married mothers spend on Housework?
[Final Answer]: 0.81

Example 2 — Percentage calculation:
Question: What percentage of total holiday spending in North America came from air travel?
Air Spending = 4138, Total Spending = 4144 → 4138/4144*100 = 99.86%
[Final Answer]: 99.86

Example 3 — Not answerable:
Question: What is the GDP growth for North America in 2020?
[Final Answer]: Not answerable

---

# 6. CONVERSATION HISTORY
This is an isolated question. No prior conversation context applies.

---

# 7. IMMEDIATE TASK

{col_structure_section}

{row_structure_section}

{html_section}

**Question:**
{question}

---

# 8. THINKING (Scratchpad)
Before answering, work through these steps:
- Step 1: Identify the target row using [ROW STRUCTURE] or row labels in the HTML
- Step 2: Identify the target column using [COLUMN STRUCTURE]
- Step 3: Look up the exact value(s) from [TABLE HTML]
- Step 4: Perform any required calculation
- Step 5: Verify the result is fully supported by the table

Then output ONLY:

[Final Answer]: <short answer>
"""


def build_prompt(table_txt: str, question: str) -> str:
    """Parse the table .txt file and inject into structured prompt."""
    # Split into sections
    col_start  = table_txt.find("[COLUMN STRUCTURE]")
    row_start  = table_txt.find("[ROW STRUCTURE]")
    html_start = table_txt.find("[TABLE HTML]")

    col_section  = table_txt[col_start:row_start].strip()  if col_start  >= 0 else "[COLUMN STRUCTURE]\n(none)"
    row_section  = table_txt[row_start:html_start].strip() if row_start  >= 0 else "[ROW STRUCTURE]\n(none)"
    html_section = table_txt[html_start:].strip()          if html_start >= 0 else "[TABLE HTML]\n(unavailable)"

    return PROMPT_TEMPLATE.format(
        col_structure_section=col_section,
        row_structure_section=row_section,
        html_section=html_section,
        question=question,
    )


# ---------------------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, api_key: str, model: str = "gemini-3.1-pro",
                temperature: float = 0.0, max_tokens: int = 8192) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta"
           f"/models/{model}:generateContent")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "maxOutputTokens": max_tokens},
    }
    resp = requests.post(url, params={"key": api_key}, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected response shape: {json.dumps(data)[:200]}")


# ---------------------------------------------------------------------------
# Answer extraction & EM
# ---------------------------------------------------------------------------

def extract_answer(response: str) -> str:
    """Extract text after [Final Answer]:"""
    for line in reversed(response.strip().split("\n")):
        m = re.search(r'\[Final Answer\]\s*:\s*(.+)', line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # fallback: last non-empty line
    for line in reversed(response.strip().split("\n")):
        if line.strip():
            return line.strip()
    return ""


def normalize(s: str) -> str:
    s = s.strip().strip('"').strip("'").rstrip(".").strip()
    s = s.replace("$", "").replace("%", "").replace(",", "")
    return " ".join(s.lower().split())


def exact_match(predicted: str, label: str) -> int:
    """Strict EM: 1 if normalized strings are equal, else 0."""
    return 1 if normalize(predicted) == normalize(label) else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_questions(path: Path) -> list[dict]:
    qs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                qs.append(json.loads(line))
    return qs


def run(questions_path: Path, output_csv: Path, api_key: str,
        model: str, limit: int, delay: float):

    questions = load_questions(questions_path)
    if limit:
        questions = questions[:limit]

    total   = len(questions)
    em_hits = 0
    errors  = 0

    # Open CSV — write header, then flush rows immediately
    already_done = set()
    write_header = True

    if output_csv.exists():
        with open(output_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                already_done.add(row["id"])
        write_header = False
        print(f"Resuming — {len(already_done)} questions already done.")

    with open(output_csv, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()

        for i, q in enumerate(questions, 1):
            qid = str(q["id"])
            if qid in already_done:
                print(f"[{i:3d}/{total}] Q{qid} SKIP (already done)")
                continue

            tid      = q["table_id"]
            txt_path = TABLE_INPUTS / f"{tid}.txt"
            filename = str(txt_path.relative_to(PROJECT_ROOT))

            print(f"[{i:3d}/{total}] Q{qid} ({tid}) ... ", end="", flush=True)

            # Load table input
            if not txt_path.exists():
                print("SKIP (table file missing)")
                errors += 1
                continue

            table_txt = txt_path.read_text(encoding="utf-8")

            # Build prompt
            full_prompt = build_prompt(table_txt, q["query"])

            # Call API
            try:
                full_response = call_gemini(full_prompt, api_key, model=model)
                model_answer  = extract_answer(full_response)
                em            = exact_match(model_answer, q["label"])
                em_hits      += em
                status        = "CORRECT" if em else "WRONG"
                print(f"{status}  pred={model_answer[:40]!r}  label={q['label'][:40]!r}")
            except Exception as e:
                full_response = f"ERROR: {e}"
                model_answer  = ""
                em            = 0
                errors       += 1
                print(f"ERROR: {e}")

            writer.writerow({
                "id":             qid,
                "question":       q["query"],
                "correct_answer": q["label"],
                "model_answer":   model_answer,
                "full_response":  full_response[:1000],
                "full_prompt":    full_prompt[:3000],
                "filename":       filename,
                "EM":             em,
            })
            csvfile.flush()

            time.sleep(delay)

    # Final summary
    done = total - errors
    acc  = em_hits / done * 100 if done else 0
    print(f"\n{'='*60}")
    print(f"DONE  |  {em_hits}/{done} correct  |  EM = {acc:.1f}%")
    if errors:
        print(f"Errors/skips: {errors}")
    print(f"Results saved to: {output_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini Table QA — CSV output")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH))
    parser.add_argument("--output",    default=str(OUTPUT_CSV))
    parser.add_argument("--model",     default="gemini-3.1-pro-preview")
    parser.add_argument("--limit",     type=int, default=0,
                        help="0 = all questions")
    parser.add_argument("--delay",     type=float, default=1.0,
                        help="Seconds between API calls")
    parser.add_argument("--api-key",   default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY env var or pass --api-key")
        sys.exit(1)

    run(
        questions_path = Path(args.questions),
        output_csv     = Path(args.output),
        api_key        = api_key,
        model          = args.model,
        limit          = args.limit,
        delay          = args.delay,
    )
