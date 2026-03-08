from __future__ import annotations

import csv
import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

import requests

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent  # directory containing this script
DATASET_DIR = os.environ.get("DATASET_DIR", str(SCRIPT_DIR / "RealHiTBench"))  # RealHiTBench path
QA_PATH = Path(DATASET_DIR) / "QA_final.json"  # main QA file for the dataset

# Only run questions whose id is in this list
RUN_IDS: List[int] = [
    99, 108, 217
]

# Gemini API (can be overridden via GEMINI_API_KEY env var)
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
)
GEMINI_MODEL_NAME = "gemini-3-pro-preview"  # model name for API (see ai.google.dev/gemini-api/docs/models)
RPM_LIMIT = 25  # requests per minute (to stay within quota)
SLEEP_TIME = (60 / RPM_LIMIT) + 0.5  # delay between requests (seconds)

# Output file paths
OUTPUT_TSV = str(SCRIPT_DIR / "gemini_html_batch_results_remain.tsv")   # TSV table (e.g. open in Excel)
OUTPUT_CSV = str(SCRIPT_DIR / "gemini_html_batch_results_remain.csv")   # CSV (proper quoting for commas/newlines)
OUTPUT_JSONL = str(SCRIPT_DIR / "gemini_html_batch_results_remain.jsonl")  # one JSON per line (for resume)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set.")
print("✅ Gemini configured:", GEMINI_MODEL_NAME)


# -----------------------------------------------------------------------------
# HTML: keep only <table> + <caption>, strip everything else (matches prepare_tables.py)
# -----------------------------------------------------------------------------
def clean_html(raw_html: str) -> str:
    """Extract only <table> and any sibling <caption> from an HTML document.

    Strips <head>, <style>, <meta>, scripts, and all body content outside the table.
    Matches the clean_html() logic in prepare_tables.py exactly.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_html, "html.parser")
    table = soup.find("table")
    if table is None:
        return raw_html  # fallback: return as-is
    caption = soup.find("caption")
    parts = []
    if caption and caption.find_parent("table") is None:
        parts.append(str(caption))
    parts.append(str(table))
    return "\n".join(parts)


def load_html_table(file_name: str) -> str:
    """Read HTML file from RealHiTBench/html and return cleaned table HTML only."""
    base = (file_name or "").strip()
    if base.endswith(".html"):
        base = base[:-5]
    path = Path(DATASET_DIR) / "html" / f"{base}.html"
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        return clean_html(raw)
    except FileNotFoundError:
        return ""


# -----------------------------------------------------------------------------
# Extract answer from full_response (Final Answer / # Output)
# -----------------------------------------------------------------------------
_FINAL_ANSWER_RE = re.compile(
    r"(\[final answer\]\s*:|final answer\s*:|\#\s*output\s*)",
    re.IGNORECASE,
)


def extract_model_answer(full_response: str) -> str:
    """Extract the answer from full_response; prefer [Final Answer]: or # Output.

    Captures all content after the marker up to the next blank line or end of
    string, so multi-line answers (e.g. ranked lists) are preserved in full.
    """
    s = (full_response or "").strip()
    if not s:
        return ""

    def _collect(after: str) -> str:
        """Return all non-empty lines after the marker until a blank line."""
        after = after.strip()
        # Drop code fences
        after = after.split("```", 1)[0].strip()
        lines = []
        for ln in after.split("\n"):
            stripped = ln.strip()
            if not stripped:
                if lines:   # stop at first blank line after content
                    break
                continue    # skip leading blank lines
            if "the final answer is" in stripped.lower() and not lines:
                continue    # skip redundant preamble phrases
            lines.append(stripped)
        return " ".join(lines)

    # Prefer last occurrence (models sometimes self-correct at the end)
    matches = list(_FINAL_ANSWER_RE.finditer(s))
    if matches:
        after = s[matches[-1].end():]
        result = _collect(after)
        if result:
            return result

    return ""


# -----------------------------------------------------------------------------
# EM (normalize same as RealHiTBench)
# -----------------------------------------------------------------------------
def _normalize_answer(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    s = re.sub(r"\b(a|an|the)\b", " ", s, flags=re.IGNORECASE)
    exclude = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
    no_punc = "".join(c for c in s if c not in exclude)
    return " ".join(no_punc.lower().split())


def _process_decimal(s: str) -> str:
    def round_match(m):
        try:
            return str(round(float(m.group()), 1))
        except Exception:
            return m.group()
    return re.sub(r"\b\d+\.\d+\b", round_match, s)


def compute_em_one(pred: str, ref: str) -> bool:
    """Exact match (True/False) after normalization."""
    ref_n = _normalize_answer(_process_decimal(ref))
    pred_n = _normalize_answer(_process_decimal(pred))
    if not pred_n:
        pred_n = "#"
    return ref_n == pred_n

# -----------------------------------------------------------------------------
# Prompt (adapted from EVIDENCE_PROMPT.md for HTML-only input, no pre-built tree)
# -----------------------------------------------------------------------------
EVIDENCE_HTML_PROMPT = """\
# 1. TASK CONTEXT
You are a precise table reasoning system. You are given a structured table as HTML and must answer a question strictly from the table data.

---

# 2. TONE CONTEXT
Be analytical, careful, and deterministic. Avoid speculation. Do not hallucinate values. The table is the ONLY source of truth.

---

# 3. BACKGROUND DATA

## How to Read the Table

You are given **[TABLE HTML]** only. You must infer the full column and row structure directly from the HTML:

- **Column headers**: Rows of `<th>` cells (usually in `<thead>`). `colspan`/`rowspan` indicate merged or hierarchical headers — a parent header spanning multiple columns means those columns are sub-columns under it.
- **Row labels**: The first `<td>` or `<th>` in each `<tbody>` row is often a row label. Indentation (leading spaces or `&nbsp;`) signals sub-rows under the row above.
- **Cell values**: Text inside `<td>`/`<th>`. Empty cells or "—" mean the value is unavailable.
- **Full column path**: Read top-down through all header rows for a column, e.g. `Average hours per day > Married mothers > Employed full time`.
- **Full row path**: Read through row labels top-to-bottom using indentation, e.g. `Household activities > Housework`.

---

# 4. DETAILED TASK DESCRIPTION & RULES

You must follow this 6-step reasoning pipeline strictly:

**[Step 1 - Query Parsing]**
Identify the target metric, entity constraints, and conditions.
→ Output: "Target: [metric]. Constraints: [filters]. Conditions: [if any]."

**[Step 2 - Execution Plan]**
Define the operation sequence. For multi-step questions, list sub-goals.
→ Output: "Plan: (1) [first operation], (2) [second operation], ..."
→ Output: "Operation type: Lookup | Arithmetic | Comparison | Aggregation"

**[Step 3 - Schema Orientation]**
Map question terms to exact table labels by reading the HTML headers. Cite full hierarchical paths.
→ Output: "Target Columns: [Path]. Target Rows: [Path]."
→ Output: "Term mapping: '<question term>' → '<exact table label>'"

**[Step 4 - Data Extraction]**
Retrieve values at intersections. Cite every value as [Row: <path>, Col: <path>]. If multi-row, enumerate all.
→ Output: "Extracted: val1 [Row: ..., Col: ...], val2 [Row: ..., Col: ...]"

**[Step 5 - Execution]**
Perform operations from Step 2 using only Step 4 data.
For non-Lookup: show exact arithmetic expression.
→ Output: "Calculation: val1 / val2 = result" OR "Calculation: None required."

**[Step 6 - Validation]**
Check: (a) answer unit matches question, (b) precision is correct, (c) all required rows/columns were used, (d) no data was fabricated.
→ Output: "Validation: Pass" OR "Validation: Flag: [issue + correction]."

**[Final Answer]**: State the final value concisely.

Strict Rules:
- Do NOT use external knowledge.
- Do NOT assume or interpolate missing values. If a cell is empty or unavailable, treat it as unavailable.
- If the answer is not derivable from the table, respond: `[Final Answer]: Not answerable`
- Numbers: output only the number, rounded as specified in the question. No units unless shown in the table.
- Text: match table wording exactly.
- Never use free-form table references such as "from the table" or "according to the data." Always cite as [Row: <path>, Col: <path>]. If you cannot cite a specific path, output "Data not found."
- If operation ≠ Lookup, you MUST show the exact arithmetic expression exactly once in Step 5. If no expression is shown, your answer is considered invalid.
- You MUST show all 6 steps in plain text. Do NOT write code to calculate.

---

# 5. EXAMPLES

**Example 1 — Simple Lookup (multi-level hierarchy):**
Question: How many hours do employed full-time married mothers spend on Housework?

[Step 1 - Query Parsing]: Target: hours spent. Constraints: Married mothers, Employed full time, Housework. Conditions: none.
[Step 2 - Execution Plan]: Plan: (1) Look up single cell value. Operation type: Lookup.
[Step 3 - Schema Orientation]: Target Columns: Average hours per day > Married mothers > Employed full time. Target Rows: Household activities > Housework. Term mapping: 'employed full-time married mothers' → 'Married mothers > Employed full time', 'Housework' → 'Household activities > Housework'.
[Step 4 - Data Extraction]: Extracted: 0.81 [Row: Household activities > Housework, Col: Average hours per day > Married mothers > Employed full time]
[Step 5 - Execution]: Calculation: None required.
[Step 6 - Validation]: Validation: Pass. Unit: hours (matches question). Single value lookup, no aggregation needed.
[Final Answer]: 0.81

---

**Example 2 — Percentage calculation:**
Question: What percentage of total holiday spending in North America came from air travel?

[Step 1 - Query Parsing]: Target: percentage of spending from air travel. Constraints: North America, Holiday - All. Conditions: none.
[Step 2 - Execution Plan]: Plan: (1) Extract Air Spending and Total Spending, (2) Divide, (3) Multiply by 100. Operation type: Arithmetic.
[Step 3 - Schema Orientation]: Target Columns: Air Spending, Total Spending. Target Rows: North America × Holiday - All. Term mapping: 'air travel' → 'Air Spending', 'total holiday spending' → 'Total Spending', 'North America' → 'North America', 'holiday' → 'Holiday - All'.
[Step 4 - Data Extraction]: Extracted: 4,138 [Row: North America > Holiday - All, Col: Air Spending], 4,144 [Row: North America > Holiday - All, Col: Total Spending]
[Step 5 - Execution]: Calculation: 4138 / 4144 × 100 = 99.86%.
[Step 6 - Validation]: Validation: Pass. Percentage requested, percentage given. Both values from same row, no data fabricated.
[Final Answer]: 99.86

---

**Example 3 — Not answerable:**
Question: What is the GDP growth for North America in 2020?

[Step 1 - Query Parsing]: Target: GDP growth. Constraints: North America, 2020.
[Step 2 - Execution Plan]: Plan: (1) Look up GDP growth value. Operation type: Lookup.
[Step 3 - Schema Orientation]: Target Columns: No column matches 'GDP growth'. Target Rows: N/A. Term mapping: 'GDP growth' → Data not found.
[Step 4 - Data Extraction]: Data not found. No column for GDP growth exists in this table.
[Step 5 - Execution]: Calculation: N/A.
[Step 6 - Validation]: Validation: Flag: Target metric does not exist in table.
[Final Answer]: Not answerable

---

# 6. CONVERSATION HISTORY
This is an isolated question. No prior conversation context applies.

---

# 7. IMMEDIATE TASK

[TABLE HTML]
{table_html}

**Question:**
{question}

---

# 8. REASONING (follow the 6-step pipeline)

Before answering, work through all six steps:
- Step 1: Parse the question — what metric, what constraints, what conditions?
- Step 2: Plan the operations — what sequence of steps do I need?
- Step 3: Orient to schema — map question terms to exact table paths
- Step 4: Extract data — look up all values, cite each as [Row: ..., Col: ...]
- Step 5: Execute — perform arithmetic using only extracted data
- Step 6: Validate — check units, precision, completeness, no fabrication

Then output your process clearly using these tags:

[Step 1 - Query Parsing]: <target, constraints, conditions>
[Step 2 - Execution Plan]: <plan and operation type>
[Step 3 - Schema Orientation]: <column paths, row paths, term mapping>
[Step 4 - Data Extraction]: <values with citations>
[Step 5 - Execution]: <arithmetic expression or "None required">
[Step 6 - Validation]: <pass or flag with correction>
[Final Answer]: <value>
"""


def create_prompt(table_html: str, question: str) -> str:
    return EVIDENCE_HTML_PROMPT.format(
        table_html=table_html,
        question=question,
    )


def gemini_generate(prompt: str, qid: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta"
        f"/models/{GEMINI_MODEL_NAME}:generateContent"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": 65536},
    }
    resp = requests.post(url, params={"key": GEMINI_API_KEY}, json=payload, timeout=300)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected response shape: {json.dumps(data)[:200]}")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def load_qa_by_id() -> dict:
    """Return dict id -> query from QA_final.json."""
    if not QA_PATH.exists():
        raise FileNotFoundError(f"QA_final.json not found: {QA_PATH}")
    with open(QA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    queries = data.get("queries", [])
    return {int(q["id"]): q for q in queries}


def main() -> None:
    qa_by_id = load_qa_by_id()
    missing = [i for i in RUN_IDS if i not in qa_by_id]
    if missing:
        print(f"⚠️ Missing IDs in QA_final.json: {missing[:20]}{'...' if len(missing) > 20 else ''}")
    to_run = [i for i in RUN_IDS if i in qa_by_id]
    print(f"📋 Will run {len(to_run)} questions (IDs: {RUN_IDS[:5]}...{RUN_IDS[-3:]})")

    # Load existing results for resume (by id)
    done_ids: set = set()
    if Path(OUTPUT_JSONL).exists():
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        done_ids.add(int(rec["id"]))
                    except Exception:
                        pass
        print(f"   Resume: {len(done_ids)} already in {OUTPUT_JSONL}")
    to_run = [i for i in to_run if i not in done_ids]
    if not to_run:
        print("✅ All requested IDs already processed.")
        return

    rows: List[dict] = []
    # Load existing rows from JSONL to keep order and merge
    if Path(OUTPUT_JSONL).exists():
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass

    for idx, qid in enumerate(to_run):
        q = qa_by_id[qid]
        file_name = q.get("FileName", "")
        question = q.get("Question", "")
        correct_answer = q.get("FinalAnswer", "") or q.get("ProcessedAnswer", "")

        table_html = load_html_table(file_name)
        if not table_html:
            print(f"⚠️ Skip id={qid}: no HTML table for {file_name}")
            continue

        prompt = create_prompt(table_html, question)
        q_preview = question[:80] + "..." if len(question) > 80 else question
        print(f"  [{idx+1}/{len(to_run)}] id={qid} | {file_name} | {q_preview}")
        print(f"         → calling API...", end="", flush=True)
        t0 = time.perf_counter()
        try:
            full_response = gemini_generate(prompt=prompt, qid=str(qid))
        except Exception as e:
            elapsed = time.perf_counter() - t0
            print(f" ERROR ({elapsed:.1f}s): {e}")
            full_response = ""
        else:
            elapsed = time.perf_counter() - t0
            print(f" done ({elapsed:.1f}s)")

        model_answer = extract_model_answer(full_response)
        em = compute_em_one(model_answer, correct_answer)
        em_base = 0  # per output format spec

        record = {
            "id": qid,
            "question": question,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "full_response": full_response,
            "full_prompt": prompt,
            "filename": file_name,
            "EM": em,
            "EM_base": em_base,
        }
        rows.append(record)

        with open(OUTPUT_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        em_so_far = sum(1 for r in rows if r.get("EM") is True)
        pct = 100 * em_so_far / len(rows) if rows else 0.0
        status = "✅" if em else "❌"
        print(f"         {status} EM={em} | pred: {model_answer!r:40s} | gold: {correct_answer!r}")
        print(f"         running score: {em_so_far}/{len(rows)} ({pct:.1f}%)")

        time.sleep(SLEEP_TIME)

    # Write TSV (columns: id, question, correct_answer, model_answer, full_response, full_prompt, filename, EM, EM_base)
    def _escape_tsv(s: str) -> str:
        s = str(s).replace("\t", " ").replace("\n", " ").replace("\r", " ")
        return s

    with open(OUTPUT_TSV, "w", encoding="utf-8") as f:
        f.write("id\tquestion\tcorrect_answer\tmodel_answer\tfull_response\tfull_prompt\tfilename\tEM\tEM_base\n")
        for r in rows:
            f.write(
                "\t".join([
                    str(r["id"]),
                    _escape_tsv(r["question"]),
                    _escape_tsv(r["correct_answer"]),
                    _escape_tsv(r["model_answer"]),
                    _escape_tsv(r["full_response"]),
                    _escape_tsv(r.get("full_prompt", "")),
                    _escape_tsv(r["filename"]),
                    str(r["EM"]).upper(),
                    str(r["EM_base"]),
                ]) + "\n"
            )

    # Write CSV (proper quoting for fields with commas/newlines)
    CSV_COLUMNS = ["id", "question", "correct_answer", "model_answer", "full_response", "full_prompt", "filename", "EM", "EM_base"]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in rows:
            row_dict = {k: r.get(k, "") for k in CSV_COLUMNS}
            row_dict["EM"] = str(r["EM"]).upper()
            row_dict["EM_base"] = str(r["EM_base"])
            writer.writerow(row_dict)

    print(f"\n💾 Results: {OUTPUT_JSONL}, {OUTPUT_TSV}, {OUTPUT_CSV}")
    em_count = sum(1 for r in rows if r.get("EM") is True)
    print(f"   EM: {em_count}/{len(rows)} ({100*em_count/len(rows):.1f}%)")


if __name__ == "__main__":
    main()
