# Priority 1 Changes Summary

4 changes across 4 files (1 new, 3 modified).

---

## 1. [NEW] [schema_validator.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/schema_validator.py)

New module that validates extracted tree schema against source HTML.

- [_count_html_data_columns(html)](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/schema_validator.py#12-49) — Parses HTML, finds first data row, counts `<td>`/`<th>` cells accounting for `colspan`
- [validate_schema(tree, html)](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/schema_validator.py#51-72) — Compares `len(tree.index_tree.leaf_nodes)` against actual HTML column count
- Returns `{"expected_cols": N, "extracted_cols": M, "match": bool}`

---

## 2. [MODIFY] [prepare_tables.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/prepare_tables.py)

```diff:prepare_tables.py
"""
prepare_tables.py -- Stage 1: Build table input files for the experiment

For each unique table in tests/questions.jsonl, generates:
    table_inputs/<table_id>.txt

Each .txt file contains:
    [COLUMN STRUCTURE]   (indented hierarchy)
    [ROW STRUCTURE]      (indented hierarchy)
    [TABLE HTML]         (cleaned: <table> + <caption> only)

Usage:
    python prepare_tables.py
"""

import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.tree_builder import html_to_tree
from experiment.tree_output import tree_to_schema, tree_to_row_schema
from table2tree.feature_tree import IndexTree, IndexNode

QUESTIONS_PATH = PROJECT_ROOT / "tests" / "questions.jsonl"
HTML_DIR       = PROJECT_ROOT / "RealHiTBench" / "html"
OUTPUT_DIR     = PROJECT_ROOT / "table_inputs"
INDENT         = "  "  # 2-space indent per level


# ---------------------------------------------------------------------------
# Indent-based hierarchy builder
# ---------------------------------------------------------------------------

def tree_to_indented(index_tree: IndexTree | None) -> str:
    """Convert an IndexTree to indented text representation.

    Example output:
        Average hours per day
          Married mothers
            Employed full time
            Employed part time
          Married fathers
            Employed full time
    """
    if index_tree is None:
        return "(none)"

    lines = []

    def _walk(node: IndexNode, depth: int):
        if node.value is not None:
            label = str(node.value).strip()
            if label:
                lines.append(f"{INDENT * depth}{label}")
        for child in node.children:
            _walk(child, depth + (0 if node.value is None else 1))

    _walk(index_tree.root, 0)
    return "\n".join(lines) if lines else "(none)"


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

def clean_html(raw_html: str) -> str:
    """Extract only <table> and <caption> from an HTML document.

    Strips <head>, <style>, <meta>, and all body content outside the table.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    table = soup.find("table")
    if table is None:
        return raw_html  # fallback: return as-is

    # Also capture any <caption> that may be a sibling
    caption = soup.find("caption")

    parts = []
    if caption and caption.find_parent("table") is None:
        parts.append(str(caption))
    parts.append(str(table))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# File builder
# ---------------------------------------------------------------------------

def load_unique_table_ids(path: Path) -> list[str]:
    seen = set()
    order = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if q["table_id"] not in seen:
                seen.add(q["table_id"])
                order.append(q["table_id"])
    return order


def build_table_txt(table_id: str, raw_html: str, tree) -> str:
    """Build the .txt content for a single table."""

    # Indent-based hierarchy
    col_indent = tree_to_indented(tree.index_tree)
    row_indent = tree_to_indented(getattr(tree, "row_index_tree", None))

    # Cleaned HTML
    cleaned = clean_html(raw_html)

    lines = [
        "[COLUMN STRUCTURE]",
        col_indent,
        "",
        "[ROW STRUCTURE]",
        row_indent,
        "",
        "[TABLE HTML]",
        cleaned,
    ]
    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    table_ids = load_unique_table_ids(QUESTIONS_PATH)
    print(f"Found {len(table_ids)} unique tables in {QUESTIONS_PATH.name}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    ok, failed = 0, 0
    total_saved = 0

    for i, tid in enumerate(table_ids, 1):
        html_path = HTML_DIR / f"{tid}.html"
        out_path  = OUTPUT_DIR / f"{tid}.txt"

        print(f"[{i:2d}/{len(table_ids)}] {tid} ... ", end="", flush=True)

        if not html_path.exists():
            print("SKIP (HTML not found)")
            failed += 1
            continue

        raw_html = html_path.read_text(encoding="utf-8")

        try:
            tree, strategy = html_to_tree(raw_html)

            if tree is None:
                raise RuntimeError("All strategies failed")

            content = build_table_txt(tid, raw_html, tree)
            out_path.write_text(content, encoding="utf-8")

            original_kb = len(raw_html) / 1024
            cleaned_kb  = len(content) / 1024
            savings_pct = (1 - cleaned_kb / original_kb) * 100

            col_schema = tree_to_schema(tree)
            row_schema = tree_to_row_schema(tree)
            total_saved += len(raw_html) - len(content)

            print(f"OK  ({strategy}) "
                  f"{len(col_schema)} cols, {len(row_schema)} rows  "
                  f"{original_kb:.0f}KB -> {cleaned_kb:.0f}KB ({savings_pct:.0f}% smaller)")
            ok += 1

        except Exception as e:
            print(f"FAIL  {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"DONE: {ok} tables prepared, {failed} failed")
    print(f"Total size saved by cleaning HTML: {total_saved/1024:.0f} KB")
    print(f"Files saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 1: Build table input files")
    parser.add_argument("--questions", type=str, default=str(QUESTIONS_PATH),
                        help="Path to questions JSONL file")
    args = parser.parse_args()
    QUESTIONS_PATH = Path(args.questions)
    main()
===
"""
prepare_tables.py -- Stage 1: Build table input files for the experiment

For each unique table in tests/questions.jsonl, generates:
    table_inputs/<table_id>.txt

Each .txt file contains:
    [COLUMN STRUCTURE]   (indented hierarchy)
    [ROW STRUCTURE]      (indented hierarchy)
    [TABLE HTML]         (cleaned: <table> + <caption> only)

Usage:
    python prepare_tables.py
"""

import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.tree_builder import html_to_tree
from experiment.tree_output import tree_to_schema, tree_to_row_schema
from experiment.schema_validator import validate_schema
from table2tree.feature_tree import IndexTree, IndexNode

QUESTIONS_PATH = PROJECT_ROOT / "tests" / "questions.jsonl"
HTML_DIR       = PROJECT_ROOT / "RealHiTBench" / "html"
OUTPUT_DIR     = PROJECT_ROOT / "table_inputs"
INDENT         = "  "  # 2-space indent per level


# ---------------------------------------------------------------------------
# Indent-based hierarchy builder
# ---------------------------------------------------------------------------

def tree_to_indented(index_tree: IndexTree | None) -> str:
    """Convert an IndexTree to indented text representation.

    Example output:
        Average hours per day
          Married mothers
            Employed full time
            Employed part time
          Married fathers
            Employed full time
    """
    if index_tree is None:
        return "(none)"

    lines = []

    def _walk(node: IndexNode, depth: int):
        if node.value is not None:
            label = str(node.value).strip()
            if label:
                lines.append(f"{INDENT * depth}{label}")
        for child in node.children:
            _walk(child, depth + (0 if node.value is None else 1))

    _walk(index_tree.root, 0)
    return "\n".join(lines) if lines else "(none)"


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

def clean_html(raw_html: str) -> str:
    """Extract only <table> and <caption> from an HTML document.

    Strips <head>, <style>, <meta>, and all body content outside the table.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    table = soup.find("table")
    if table is None:
        return raw_html  # fallback: return as-is

    # Also capture any <caption> that may be a sibling
    caption = soup.find("caption")

    parts = []
    if caption and caption.find_parent("table") is None:
        parts.append(str(caption))
    parts.append(str(table))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# File builder
# ---------------------------------------------------------------------------

def load_unique_table_ids(path: Path) -> list[str]:
    seen = set()
    order = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if q["table_id"] not in seen:
                seen.add(q["table_id"])
                order.append(q["table_id"])
    return order


def build_table_txt(table_id: str, raw_html: str, tree) -> str:
    """Build the .txt content for a single table."""

    # Indent-based hierarchy
    col_indent = tree_to_indented(tree.index_tree)
    row_indent = tree_to_indented(getattr(tree, "row_index_tree", None))

    # Cleaned HTML
    cleaned = clean_html(raw_html)

    lines = [
        "[COLUMN STRUCTURE]",
        col_indent,
        "",
        "[ROW STRUCTURE]",
        row_indent,
        "",
        "[TABLE HTML]",
        cleaned,
    ]
    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    table_ids = load_unique_table_ids(QUESTIONS_PATH)
    print(f"Found {len(table_ids)} unique tables in {QUESTIONS_PATH.name}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    ok, failed = 0, 0
    total_saved = 0
    schema_mismatches = 0
    table_metadata = {}

    for i, tid in enumerate(table_ids, 1):
        html_path = HTML_DIR / f"{tid}.html"
        out_path  = OUTPUT_DIR / f"{tid}.txt"

        print(f"[{i:2d}/{len(table_ids)}] {tid} ... ", end="", flush=True)

        if not html_path.exists():
            print("SKIP (HTML not found)")
            failed += 1
            continue

        raw_html = html_path.read_text(encoding="utf-8")

        try:
            tree, strategy = html_to_tree(raw_html)

            if tree is None:
                raise RuntimeError("All strategies failed")

            # Validate schema against HTML
            validation = validate_schema(tree, raw_html)
            schema_ok = validation["match"]
            if not schema_ok:
                schema_mismatches += 1

            content = build_table_txt(tid, raw_html, tree)
            out_path.write_text(content, encoding="utf-8")

            original_kb = len(raw_html) / 1024
            cleaned_kb  = len(content) / 1024
            savings_pct = (1 - cleaned_kb / original_kb) * 100

            col_schema = tree_to_schema(tree)
            row_schema = tree_to_row_schema(tree)
            total_saved += len(raw_html) - len(content)

            # Record metadata for downstream use
            table_metadata[tid] = {
                "strategy": strategy,
                "extracted_cols": validation["extracted_cols"],
                "expected_cols": validation["expected_cols"],
                "schema_match": schema_ok,
            }

            status = "OK" if schema_ok else "OK (SCHEMA MISMATCH)"
            print(f"{status}  ({strategy}) "
                  f"{len(col_schema)} cols, {len(row_schema)} rows  "
                  f"{original_kb:.0f}KB -> {cleaned_kb:.0f}KB ({savings_pct:.0f}% smaller)")
            if not schema_ok:
                print(f"    WARN: expected {validation['expected_cols']} cols, "
                      f"extracted {validation['extracted_cols']}")
            ok += 1

        except Exception as e:
            print(f"FAIL  {e}")
            failed += 1

    # Write table metadata for run_experiment_csv.py
    metadata_path = OUTPUT_DIR / "table_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(table_metadata, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE: {ok} tables prepared, {failed} failed")
    print(f"Schema mismatches: {schema_mismatches}/{ok}")
    print(f"Total size saved by cleaning HTML: {total_saved/1024:.0f} KB")
    print(f"Metadata saved to: {metadata_path}")
    print(f"Files saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 1: Build table input files")
    parser.add_argument("--questions", type=str, default=str(QUESTIONS_PATH),
                        help="Path to questions JSONL file")
    args = parser.parse_args()
    QUESTIONS_PATH = Path(args.questions)
    main()
```

**What changed:**
- Calls [validate_schema()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/schema_validator.py#51-72) after each tree build
- Prints `WARN: expected X cols, extracted Y` on mismatch
- Tracks `schema_mismatches` count in final summary
- Writes **`table_metadata.json`** to `table_inputs/` with per-table metadata:
  ```json
  {
    "table_id": {
      "strategy": "direct",
      "extracted_cols": 5,
      "expected_cols": 5,
      "schema_match": true
    }
  }
  ```

---

## 3. [MODIFY] [run_experiment_csv.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py)

```diff:run_experiment_csv.py
"""
run_experiment_csv.py -- Stage 2: Call Gemini API and record results to CSV

Reads:
  - tests/questions.jsonl          (questions + labels)
  - table_inputs/<table_id>.txt    (col structure, row structure, HTML)
  - OR trees_json/<table_id>.json  (flat JSON tables, with --json-dir)
  - OR <html-dir>/<table_id>.html  (raw HTML tables, with --html-dir)

Calls Gemini API for each question using the structured prompt from CURRENT_PROMPT.md
Writes one CSV row per question immediately (safe against crashes).

CSV columns:
  id | question | correct_answer | model_answer | full_response | full_prompt | filename | sub_type | EM

Usage:
  set GEMINI_API_KEY=your_key
  python run_experiment_csv.py
  python run_experiment_csv.py --limit 5 --delay 1.5 --model gemini-2.0-flash

  # JSON table input:
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md

  # Raw HTML input (cleaned automatically):
  python run_experiment_csv.py --html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md

  # Preview a fully-rendered prompt (no API call):
  python run_experiment_csv.py --demo
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --demo
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --demo --qid 22
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
TREES_JSON     = PROJECT_ROOT / "trees_json"
OUTPUT_CSV     = PROJECT_ROOT / "experiment_results.csv"
DEFAULT_PROMPT = PROJECT_ROOT / "EVIDENCE_PROMPT.md"

CSV_COLUMNS = ["id", "question", "correct_answer", "model_answer",
               "full_response", "full_prompt", "filename", "sub_type", "EM"]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def load_prompt_template(prompt_file: Path) -> str:
    """Load prompt template from an external .md file."""
    text = prompt_file.read_text(encoding="utf-8")
    # Strip the example table HTML from the template (everything in # 7 between
    # the placeholder markers should already use {placeholders})
    return text


def build_prompt(table_txt: str, question: str, template: str) -> str:
    """Parse the table .txt file and inject into the prompt template."""
    col_start  = table_txt.find("[COLUMN STRUCTURE]")
    row_start  = table_txt.find("[ROW STRUCTURE]")
    html_start = table_txt.find("[TABLE HTML]")

    col_section  = table_txt[col_start:row_start].strip()  if col_start  >= 0 else "[COLUMN STRUCTURE]\n(none)"
    row_section  = table_txt[row_start:html_start].strip() if row_start  >= 0 else "[ROW STRUCTURE]\n(none)"
    html_section = table_txt[html_start:].strip()          if html_start >= 0 else "[TABLE HTML]\n(unavailable)"

    return template.format(
        col_structure_section=col_section,
        row_structure_section=row_section,
        html_section=html_section,
        question=question,
    )


def build_prompt_json(json_path: Path, question: str, template: str) -> str:
    """Load a trees_json/*.json file and inject into the JSON prompt template."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    json_section = "[TABLE JSON]\n" + json.dumps(data, ensure_ascii=False, indent=2)
    return template.format(
        json_section=json_section,
        question=question,
    )


def clean_html(raw_html: str) -> str:
    """Extract only <table> and any sibling <caption> from an HTML document.

    Strips <head>, <style>, <meta>, scripts, and all body content outside the table.
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


def build_prompt_html(html_path: Path, question: str, template: str) -> str:
    """Load raw HTML, clean it, and inject into the prompt template."""
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_html(raw)
    html_section = "[TABLE HTML]\n" + cleaned
    return template.format(
        col_structure_section="",
        row_structure_section="",
        html_section=html_section,
        question=question,
    )


# ---------------------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------------------

RETRYABLE_STATUS_CODES = {503, 429, 500, 502, 504}
MAX_RETRIES = 3
RETRY_WAIT  = 30  # seconds


def call_gemini(prompt: str, api_key: str, model: str = "gemini-3-pro-preview",
                temperature: float = 1.0, max_tokens: int = 32000) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta"
           f"/models/{model}:generateContent")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "maxOutputTokens": max_tokens},
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, params={"key": api_key}, json=payload, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise RuntimeError(f"Unexpected response shape: {json.dumps(data)[:200]}")
            elif resp.status_code in RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                print(f"  [retry {attempt}/{MAX_RETRIES}] {last_error[:80]}... waiting {RETRY_WAIT}s")
                time.sleep(RETRY_WAIT)
            else:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout) as e:
            last_error = str(e)
            print(f"  [retry {attempt}/{MAX_RETRIES}] {type(e).__name__}: {str(e)[:80]}... waiting {RETRY_WAIT}s")
            time.sleep(RETRY_WAIT)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Answer extraction & EM
# ---------------------------------------------------------------------------

_FINAL_ANSWER_RE = re.compile(
    r'(?:\*?\*?\[?\s*Final\s+Answer\s*\]?\*?\*?\s*[:\-]\s*)(.*)',
    re.IGNORECASE,
)


def _strip_code_fences(text: str) -> str:
    """Remove leading/trailing triple-backtick fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```[^\n]*\n?', '', text)
    if text.endswith("```"):
        text = re.sub(r'\n?```$', '', text)
    return text.strip()


def extract_answer(response: str) -> str:
    """Extract the text following the *last* [Final Answer]: marker.

    Handles multi-line answers (collects until the next section header or end).
    Falls back to the last non-empty line if no marker is found.
    """
    lines = response.strip().splitlines()
    best_start = -1
    # find the LAST occurrence of the marker
    for i, line in enumerate(lines):
        if _FINAL_ANSWER_RE.search(line):
            best_start = i

    if best_start >= 0:
        m = _FINAL_ANSWER_RE.search(lines[best_start])
        first_part = m.group(1).strip() if m else ""
        collected = [first_part] if first_part else []
        for subsequent in lines[best_start + 1:]:
            # stop at next section header like [Step ...] or **Step ...**
            if re.match(r'^\s*(\[|\*\*\s*Step)', subsequent):
                break
            collected.append(subsequent.strip())
        answer = "\n".join(collected).strip()
        answer = _strip_code_fences(answer)
        return answer if answer else first_part

    # fallback: last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return ""


def _process_decimal(s: str) -> str:
    """Round to 2 decimals if the string looks like a number."""
    try:
        return str(round(float(s), 2))
    except (ValueError, OverflowError):
        return s


def normalize(s: str) -> str:
    s = s.strip().strip('"').strip("'").rstrip(".").strip()
    s = s.replace("$", "").replace("%", "").replace(",", "")
    # Remove articles
    s = re.sub(r'\b(a|an|the)\b', ' ', s, flags=re.IGNORECASE)
    # Remove all punctuation
    s = re.sub(r'[^\w\s]', ' ', s)
    s = " ".join(s.lower().split())
    return _process_decimal(s)


def exact_match(predicted: str, label: str) -> int:
    """Strict EM: 1 if normalized strings are equal, else 0.

    Returns 0 immediately if prediction is empty (model produced nothing).
    """
    np = normalize(predicted)
    nl = normalize(label)
    if not np:
        return 0
    return 1 if np == nl else 0


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
        model: str, limit: int, delay: float, qids: list[str] = None,
        prompt_template: str = "", csv_dir: str = "",
        json_dir: str = "", html_dir: str = "", demo: bool = False):

    questions = load_questions(questions_path)
    if qids:
        qid_set = set(qids)
        questions = [q for q in questions if str(q["id"]) in qid_set]
    elif limit:
        questions = questions[:limit]

    # --demo: render the first prompt and exit (no API call)
    if demo:
        # Reconfigure stdout for UTF-8 so Unicode chars (→ etc.) print on Windows
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if not questions:
            print("ERROR: No questions to demo.")
            sys.exit(1)
        q = questions[0]
        tid = q["table_id"]
        if html_dir:
            tpath = Path(html_dir) / f"{tid}.html"
            full_prompt = build_prompt_html(tpath, q["query"], prompt_template)
        elif json_dir:
            tpath = Path(json_dir) / f"{tid}.json"
            full_prompt = build_prompt_json(tpath, q["query"], prompt_template)
        elif csv_dir:
            tpath = Path(csv_dir) / f"{tid}.csv"
            table_txt = tpath.read_text(encoding="utf-8")
            table_txt = f"[COLUMN STRUCTURE]\n(unavailable)\n[ROW STRUCTURE]\n(unavailable)\n[TABLE HTML]\n{table_txt}"
            full_prompt = build_prompt(table_txt, q["query"], prompt_template)
        else:
            tpath = TABLE_INPUTS / f"{tid}.txt"
            table_txt = tpath.read_text(encoding="utf-8")
            full_prompt = build_prompt(table_txt, q["query"], prompt_template)
        sep = "=" * 60
        print(sep)
        print(f"DEMO PROMPT  |  table: {tid}  |  Q id: {q['id']}")
        print(sep)
        print(full_prompt)
        print(sep)
        print("END DEMO — no API call was made")
        print(sep)
        return

    total   = len(questions)
    em_hits = 0
    errors  = 0

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
            use_json = bool(json_dir)

            if html_dir:
                tbl_path = Path(html_dir) / f"{tid}.html"
                filename = str(tbl_path)
            elif json_dir:
                tbl_path = Path(json_dir) / f"{tid}.json"
                filename = str(tbl_path)
            elif csv_dir:
                tbl_path = Path(csv_dir) / f"{tid}.csv"
                filename = str(tbl_path)
            else:
                tbl_path = TABLE_INPUTS / f"{tid}.txt"
                filename = str(tbl_path.relative_to(PROJECT_ROOT))

            print(f"[{i:3d}/{total}] Q{qid} ({tid}) ... ", end="", flush=True)

            # Load table input
            if not tbl_path.exists():
                print("SKIP (table file missing)")
                errors += 1
                continue

            if html_dir:
                full_prompt = build_prompt_html(tbl_path, q["query"], prompt_template)
            elif use_json:
                full_prompt = build_prompt_json(tbl_path, q["query"], prompt_template)
            else:
                table_txt = tbl_path.read_text(encoding="utf-8")
                if csv_dir:
                    table_txt = f"[COLUMN STRUCTURE]\n(unavailable)\n[ROW STRUCTURE]\n(unavailable)\n[TABLE HTML]\n{table_txt}"
                full_prompt = build_prompt(table_txt, q["query"], prompt_template)

            # Call API
            t0 = time.perf_counter()
            try:
                full_response = call_gemini(full_prompt, api_key, model=model)
                elapsed       = time.perf_counter() - t0
                model_answer  = extract_answer(full_response)
                em            = exact_match(model_answer, q["label"])
                em_hits      += em
                done_so_far   = i - errors
                pct           = em_hits / done_so_far * 100 if done_so_far else 0
                status        = "CORRECT" if em else "WRONG"
                print(f"{status}  [{em_hits}/{done_so_far} {pct:.0f}%]  ({elapsed:.1f}s)  pred={model_answer[:40]!r}  label={q['label'][:40]!r}")
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
                "full_response":  full_response,
                "full_prompt":    full_prompt,
                "filename":       filename,
                "sub_type":       q.get("sub_type", ""),
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
    parser.add_argument("--qid",       type=str, default="",
                        help="Comma-separated question IDs, e.g. 20,22,26")
    parser.add_argument("--delay",     type=float, default=1.0,
                        help="Seconds between API calls")
    parser.add_argument("--api-key",   default=None)
    parser.add_argument("--prompt-file", type=str, default=str(DEFAULT_PROMPT),
                        help="Path to prompt template .md file")
    parser.add_argument("--csv-dir", type=str, default="",
                        help="If set, load <tid>.csv from this dir instead of HO-Tree txts")
    parser.add_argument("--json-dir", type=str, default="",
                        help="If set, load <tid>.json from this dir (use with EVIDENCE_PROMPT_JSON.md)")
    parser.add_argument("--html-dir", type=str, default="",
                        help="If set, load <tid>.html from this dir (raw HTML, use with EVIDENCE_PROMPT_HTML.md)")
    parser.add_argument("--demo", action="store_true",
                        help="Print one fully-rendered prompt and exit (no API call)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.demo:
        print("ERROR: Set GEMINI_API_KEY env var or pass --api-key")
        sys.exit(1)

    # Parse comma-separated qids
    qids = [q.strip() for q in args.qid.split(",") if q.strip()] if args.qid else None

    # Load prompt template
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"ERROR: Prompt file not found: {prompt_path}")
        sys.exit(1)
    prompt_template = load_prompt_template(prompt_path)
    print(f"Prompt template: {prompt_path.name}")

    run(
        questions_path   = Path(args.questions),
        output_csv       = Path(args.output),
        api_key          = api_key,
        model            = args.model,
        limit            = args.limit,
        delay            = args.delay,
        qids             = qids,
        prompt_template  = prompt_template,
        csv_dir          = args.csv_dir,
        json_dir         = args.json_dir,
        html_dir         = args.html_dir,
        demo             = args.demo,
    )
===
"""
run_experiment_csv.py -- Stage 2: Call Gemini API and record results to CSV

Reads:
  - tests/questions.jsonl          (questions + labels)
  - table_inputs/<table_id>.txt    (col structure, row structure, HTML)
  - OR trees_json/<table_id>.json  (flat JSON tables, with --json-dir)
  - OR <html-dir>/<table_id>.html  (raw HTML tables, with --html-dir)

Calls Gemini API for each question using the structured prompt from CURRENT_PROMPT.md
Writes one CSV row per question immediately (safe against crashes).

CSV columns:
  id | question | correct_answer | model_answer | full_response | full_prompt | filename | sub_type | EM

Usage:
  set GEMINI_API_KEY=your_key
  python run_experiment_csv.py
  python run_experiment_csv.py --limit 5 --delay 1.5 --model gemini-2.0-flash

  # JSON table input:
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md

  # Raw HTML input (cleaned automatically):
  python run_experiment_csv.py --html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md

  # Preview a fully-rendered prompt (no API call):
  python run_experiment_csv.py --demo
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --demo
  python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --demo --qid 22
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
TREES_JSON     = PROJECT_ROOT / "trees_json"
OUTPUT_CSV     = PROJECT_ROOT / "experiment_results.csv"
DEFAULT_PROMPT = PROJECT_ROOT / "EVIDENCE_PROMPT.md"

CSV_COLUMNS = ["id", "question", "correct_answer", "model_answer",
               "full_response", "full_prompt", "filename", "sub_type", "EM",
               "strategy", "prompt_tokens", "schema_match"]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def load_prompt_template(prompt_file: Path) -> str:
    """Load prompt template from an external .md file."""
    text = prompt_file.read_text(encoding="utf-8")
    # Strip the example table HTML from the template (everything in # 7 between
    # the placeholder markers should already use {placeholders})
    return text


def build_prompt(table_txt: str, question: str, template: str) -> str:
    """Parse the table .txt file and inject into the prompt template."""
    col_start  = table_txt.find("[COLUMN STRUCTURE]")
    row_start  = table_txt.find("[ROW STRUCTURE]")
    html_start = table_txt.find("[TABLE HTML]")

    col_section  = table_txt[col_start:row_start].strip()  if col_start  >= 0 else "[COLUMN STRUCTURE]\n(none)"
    row_section  = table_txt[row_start:html_start].strip() if row_start  >= 0 else "[ROW STRUCTURE]\n(none)"
    html_section = table_txt[html_start:].strip()          if html_start >= 0 else "[TABLE HTML]\n(unavailable)"

    return template.format(
        col_structure_section=col_section,
        row_structure_section=row_section,
        html_section=html_section,
        question=question,
    )


def build_prompt_json(json_path: Path, question: str, template: str) -> str:
    """Load a trees_json/*.json file and inject into the JSON prompt template."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    json_section = "[TABLE JSON]\n" + json.dumps(data, ensure_ascii=False, indent=2)
    return template.format(
        json_section=json_section,
        question=question,
    )


def clean_html(raw_html: str) -> str:
    """Extract only <table> and any sibling <caption> from an HTML document.

    Strips <head>, <style>, <meta>, scripts, and all body content outside the table.
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


def build_prompt_html(html_path: Path, question: str, template: str) -> str:
    """Load raw HTML, clean it, and inject into the prompt template."""
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_html(raw)
    html_section = "[TABLE HTML]\n" + cleaned
    return template.format(
        col_structure_section="",
        row_structure_section="",
        html_section=html_section,
        question=question,
    )


# ---------------------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------------------

RETRYABLE_STATUS_CODES = {503, 429, 500, 502, 504}
MAX_RETRIES = 3
RETRY_WAIT  = 30  # seconds


def call_gemini(prompt: str, api_key: str, model: str = "gemini-3-pro-preview",
                temperature: float = 1.0, max_tokens: int = 32000) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta"
           f"/models/{model}:generateContent")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "maxOutputTokens": max_tokens},
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, params={"key": api_key}, json=payload, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    raise RuntimeError(f"Unexpected response shape: {json.dumps(data)[:200]}")
            elif resp.status_code in RETRYABLE_STATUS_CODES:
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                print(f"  [retry {attempt}/{MAX_RETRIES}] {last_error[:80]}... waiting {RETRY_WAIT}s")
                time.sleep(RETRY_WAIT)
            else:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout) as e:
            last_error = str(e)
            print(f"  [retry {attempt}/{MAX_RETRIES}] {type(e).__name__}: {str(e)[:80]}... waiting {RETRY_WAIT}s")
            time.sleep(RETRY_WAIT)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Answer extraction & EM
# ---------------------------------------------------------------------------

_FINAL_ANSWER_RE = re.compile(
    r'(?:\*?\*?\[?\s*Final\s+Answer\s*\]?\*?\*?\s*[:\-]\s*)(.*)',
    re.IGNORECASE,
)


def _strip_code_fences(text: str) -> str:
    """Remove leading/trailing triple-backtick fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```[^\n]*\n?', '', text)
    if text.endswith("```"):
        text = re.sub(r'\n?```$', '', text)
    return text.strip()


def extract_answer(response: str) -> str:
    """Extract the text following the *last* [Final Answer]: marker.

    Handles multi-line answers (collects until the next section header or end).
    Falls back to the last non-empty line if no marker is found.
    """
    lines = response.strip().splitlines()
    best_start = -1
    # find the LAST occurrence of the marker
    for i, line in enumerate(lines):
        if _FINAL_ANSWER_RE.search(line):
            best_start = i

    if best_start >= 0:
        m = _FINAL_ANSWER_RE.search(lines[best_start])
        first_part = m.group(1).strip() if m else ""
        collected = [first_part] if first_part else []
        for subsequent in lines[best_start + 1:]:
            # stop at next section header like [Step ...] or **Step ...**
            if re.match(r'^\s*(\[|\*\*\s*Step)', subsequent):
                break
            collected.append(subsequent.strip())
        answer = "\n".join(collected).strip()
        answer = _strip_code_fences(answer)
        return answer if answer else first_part

    # fallback: last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return ""


def _process_decimal(s: str) -> str:
    """Normalize number format without forced rounding."""
    try:
        f = float(s)
        # Normalize: if it's a whole number, drop the decimal
        if f == int(f):
            return str(int(f))
        return str(f)
    except (ValueError, OverflowError):
        return s


def normalize(s: str) -> str:
    s = s.strip().strip('"').strip("'").rstrip(".").strip()
    s = s.replace("$", "").replace("%", "").replace(",", "")
    # Remove articles
    s = re.sub(r'\b(a|an|the)\b', ' ', s, flags=re.IGNORECASE)
    # Remove all punctuation
    s = re.sub(r'[^\w\s]', ' ', s)
    s = " ".join(s.lower().split())
    return _process_decimal(s)


def exact_match(predicted: str, label: str) -> int:
    """EM: try raw match first, then normalized match.

    Returns 0 immediately if prediction is empty.
    """
    if not predicted.strip():
        return 0
    # Try exact raw match (case-insensitive, stripped)
    if predicted.strip().lower() == label.strip().lower():
        return 1
    # Fall back to normalized match
    np = normalize(predicted)
    nl = normalize(label)
    return 1 if np == nl else 0


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
        model: str, limit: int, delay: float, qids: list[str] = None,
        prompt_template: str = "", csv_dir: str = "",
        json_dir: str = "", html_dir: str = "", demo: bool = False):

    questions = load_questions(questions_path)
    if qids:
        qid_set = set(qids)
        questions = [q for q in questions if str(q["id"]) in qid_set]
    elif limit:
        questions = questions[:limit]

    # Load table metadata (strategy, schema_match) from prepare_tables.py output
    table_meta = {}
    metadata_path = TABLE_INPUTS / "table_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            table_meta = json.load(f)

    # --demo: render the first prompt and exit (no API call)
    if demo:
        # Reconfigure stdout for UTF-8 so Unicode chars (→ etc.) print on Windows
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if not questions:
            print("ERROR: No questions to demo.")
            sys.exit(1)
        q = questions[0]
        tid = q["table_id"]
        if html_dir:
            tpath = Path(html_dir) / f"{tid}.html"
            full_prompt = build_prompt_html(tpath, q["query"], prompt_template)
        elif json_dir:
            tpath = Path(json_dir) / f"{tid}.json"
            full_prompt = build_prompt_json(tpath, q["query"], prompt_template)
        elif csv_dir:
            tpath = Path(csv_dir) / f"{tid}.csv"
            table_txt = tpath.read_text(encoding="utf-8")
            table_txt = f"[COLUMN STRUCTURE]\n(unavailable)\n[ROW STRUCTURE]\n(unavailable)\n[TABLE HTML]\n{table_txt}"
            full_prompt = build_prompt(table_txt, q["query"], prompt_template)
        else:
            tpath = TABLE_INPUTS / f"{tid}.txt"
            table_txt = tpath.read_text(encoding="utf-8")
            full_prompt = build_prompt(table_txt, q["query"], prompt_template)
        sep = "=" * 60
        print(sep)
        print(f"DEMO PROMPT  |  table: {tid}  |  Q id: {q['id']}")
        print(sep)
        print(full_prompt)
        print(sep)
        print("END DEMO — no API call was made")
        print(sep)
        return

    total   = len(questions)
    em_hits = 0
    errors  = 0

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
            use_json = bool(json_dir)

            if html_dir:
                tbl_path = Path(html_dir) / f"{tid}.html"
                filename = str(tbl_path)
            elif json_dir:
                tbl_path = Path(json_dir) / f"{tid}.json"
                filename = str(tbl_path)
            elif csv_dir:
                tbl_path = Path(csv_dir) / f"{tid}.csv"
                filename = str(tbl_path)
            else:
                tbl_path = TABLE_INPUTS / f"{tid}.txt"
                filename = str(tbl_path.relative_to(PROJECT_ROOT))

            print(f"[{i:3d}/{total}] Q{qid} ({tid}) ... ", end="", flush=True)

            # Load table input
            if not tbl_path.exists():
                print("SKIP (table file missing)")
                errors += 1
                continue

            if html_dir:
                full_prompt = build_prompt_html(tbl_path, q["query"], prompt_template)
            elif use_json:
                full_prompt = build_prompt_json(tbl_path, q["query"], prompt_template)
            else:
                table_txt = tbl_path.read_text(encoding="utf-8")
                if csv_dir:
                    table_txt = f"[COLUMN STRUCTURE]\n(unavailable)\n[ROW STRUCTURE]\n(unavailable)\n[TABLE HTML]\n{table_txt}"
                full_prompt = build_prompt(table_txt, q["query"], prompt_template)

            # Call API
            t0 = time.perf_counter()
            try:
                full_response = call_gemini(full_prompt, api_key, model=model)
                elapsed       = time.perf_counter() - t0
                model_answer  = extract_answer(full_response)
                em            = exact_match(model_answer, q["label"])
                em_hits      += em
                done_so_far   = i - errors
                pct           = em_hits / done_so_far * 100 if done_so_far else 0
                status        = "CORRECT" if em else "WRONG"
                print(f"{status}  [{em_hits}/{done_so_far} {pct:.0f}%]  ({elapsed:.1f}s)  pred={model_answer[:40]!r}  label={q['label'][:40]!r}")
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
                "full_response":  full_response,
                "full_prompt":    full_prompt,
                "filename":       filename,
                "sub_type":       q.get("sub_type", ""),
                "EM":             em,
                "strategy":       table_meta.get(q["table_id"], {}).get("strategy", ""),
                "prompt_tokens":  len(full_prompt) // 4,
                "schema_match":   table_meta.get(q["table_id"], {}).get("schema_match", ""),
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
    parser.add_argument("--qid",       type=str, default="",
                        help="Comma-separated question IDs, e.g. 20,22,26")
    parser.add_argument("--delay",     type=float, default=1.0,
                        help="Seconds between API calls")
    parser.add_argument("--api-key",   default=None)
    parser.add_argument("--prompt-file", type=str, default=str(DEFAULT_PROMPT),
                        help="Path to prompt template .md file")
    parser.add_argument("--csv-dir", type=str, default="",
                        help="If set, load <tid>.csv from this dir instead of HO-Tree txts")
    parser.add_argument("--json-dir", type=str, default="",
                        help="If set, load <tid>.json from this dir (use with EVIDENCE_PROMPT_JSON.md)")
    parser.add_argument("--html-dir", type=str, default="",
                        help="If set, load <tid>.html from this dir (raw HTML, use with EVIDENCE_PROMPT_HTML.md)")
    parser.add_argument("--demo", action="store_true",
                        help="Print one fully-rendered prompt and exit (no API call)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.demo:
        print("ERROR: Set GEMINI_API_KEY env var or pass --api-key")
        sys.exit(1)

    # Parse comma-separated qids
    qids = [q.strip() for q in args.qid.split(",") if q.strip()] if args.qid else None

    # Load prompt template
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"ERROR: Prompt file not found: {prompt_path}")
        sys.exit(1)
    prompt_template = load_prompt_template(prompt_path)
    print(f"Prompt template: {prompt_path.name}")

    run(
        questions_path   = Path(args.questions),
        output_csv       = Path(args.output),
        api_key          = api_key,
        model            = args.model,
        limit            = args.limit,
        delay            = args.delay,
        qids             = qids,
        prompt_template  = prompt_template,
        csv_dir          = args.csv_dir,
        json_dir         = args.json_dir,
        html_dir         = args.html_dir,
        demo             = args.demo,
    )
```

**3a. New CSV columns:**

| Column | Source |
|---|---|
| [strategy](file:///c:/Users/nqmi/Downloads/Tree-Experiment/tests/test_tree_building.py#114-118) | From `table_metadata.json` |
| `prompt_tokens` | `len(full_prompt) // 4` (estimate) |
| `schema_match` | From `table_metadata.json` |

**3b. Normalization fix — [_process_decimal()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py#225-231):**

```diff
-    return str(round(float(s), 2))       # forced 2-decimal rounding
+    if f == int(f): return str(int(f))    # 5.0 → "5"
+    return str(f)                         # 1234.567 → "1234.567" (no rounding)
```

**3c. Scoring fix — [exact_match()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/run_experiment_csv.py#249-263):**

```diff
+    # Try raw match first (case-insensitive)
+    if predicted.strip().lower() == label.strip().lower():
+        return 1
+    # Then fall back to normalized match
     np = normalize(predicted)
     nl = normalize(label)
     return 1 if np == nl else 0
```

---

## 4. [MODIFY] [tree_builder.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py)

```diff:tree_builder.py
"""
tree_builder.py — HO-Tree Construction from HTML

Converts HTML tables to hierarchical FeatureTree structures using
three strategies with automatic fallback:

  1. direct     — construct_sheet() with auto header detection
  2. fixed      — manual header/data split (configurable max_header_rows)
  3. structured — flat structured fallback (always succeeds)

Usage:
    from experiment.tree_builder import html_to_tree

    tree, strategy = html_to_tree(html_string)
"""

import tempfile
import openpyxl

from utils.sheet_utils import html2workbook, sheet2structure
from utils.constants import DEFAULT_TABLE_NAME
from table2tree.feature_tree import (
    FeatureTree,
    IndexTree,
    BodyTree,
    IndexNode,
    BodyNode,
    construct_index_tree,
    construct_body_tree,
    construct_sheet,
    construct_feature_tree,
)
from table2tree.extract_excel import get_structured_xlsx_sheet


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _html_to_workbook_sheet(html_content: str):
    """HTML string → expanded openpyxl sheet (merged cells resolved)."""
    wb = html2workbook(html_content)
    temp_path = tempfile.mktemp(suffix=".xlsx")
    wb.save(temp_path)
    sheet = get_structured_xlsx_sheet(temp_path)
    return sheet, temp_path


# ---------------------------------------------------------------------------
# Strategy 1: Direct (auto header detection via split_schema_row)
# ---------------------------------------------------------------------------

def html_to_tree_direct(html_content: str) -> FeatureTree:
    """
    HTML → Excel → expand merges → construct_sheet().
    Uses ST-Raptor's split_schema_row() to auto-detect header rows.
    """
    wb = html2workbook(html_content)
    temp_path = tempfile.mktemp(suffix=".xlsx")
    wb.save(temp_path)

    wb2 = openpyxl.load_workbook(temp_path, data_only=True)
    sheet = sheet2structure(wb2.active)
    return construct_sheet(sheet)


# ---------------------------------------------------------------------------
# Strategy 2: Fixed (manual header row count)
# ---------------------------------------------------------------------------

def html_to_tree_fixed(html_content: str, max_header_rows: int = 2) -> FeatureTree:
    """
    Manually split first `max_header_rows` rows as schema, remainder as data.
    More robust when auto-detection fails.
    """
    sheet, _ = _html_to_workbook_sheet(html_content)
    nrows = sheet.max_row
    ncols = sheet.max_column

    # Schema sheet
    schema_wb = openpyxl.Workbook()
    schema_sheet = schema_wb.active
    for r in range(1, min(max_header_rows + 1, nrows + 1)):
        for c in range(1, ncols + 1):
            schema_sheet.cell(row=r, column=c).value = sheet.cell(row=r, column=c).value

    # Data sheet
    data_wb = openpyxl.Workbook()
    data_sheet = data_wb.active
    for r in range(max_header_rows + 1, nrows + 1):
        for c in range(1, ncols + 1):
            data_sheet.cell(row=r - max_header_rows, column=c).value = sheet.cell(
                row=r, column=c
            ).value

    index_tree = construct_index_tree(schema_sheet)
    body_tree, _ = construct_body_tree(index_tree, data_sheet)
    return FeatureTree(index_tree=index_tree, body_tree=body_tree)


# ---------------------------------------------------------------------------
# Strategy 3: Structured (flat, always succeeds)
# ---------------------------------------------------------------------------

def html_to_tree_structured(html_content: str) -> FeatureTree:
    """Treat full expanded sheet as structured data — last-resort fallback."""
    sheet, _ = _html_to_workbook_sheet(html_content)
    tree_dict = {DEFAULT_TABLE_NAME: sheet}
    return construct_feature_tree(tree_dict)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def html_to_tree(html_content: str, max_header_rows: int = 2):
    """
    Build HO-Tree from an HTML table string.

    Tries strategies in order: direct → fixed → structured.

    Returns:
        (FeatureTree, strategy_name)  on success
        (None,        'failed')       if all strategies fail
    """
    strategies = [
        ("direct", lambda: html_to_tree_direct(html_content)),
        ("fixed", lambda: html_to_tree_fixed(html_content, max_header_rows)),
        ("structured", lambda: html_to_tree_structured(html_content)),
    ]
    for name, fn in strategies:
        try:
            tree = fn()
            if tree is not None and tree.get_max_col() > 0:
                return tree, name
        except Exception:
            pass
    return None, "failed"
===
"""
tree_builder.py — HO-Tree Construction from HTML

Converts HTML tables to hierarchical FeatureTree structures using
three strategies with automatic fallback:

  1. direct     — construct_sheet() with auto header detection
  2. fixed      — manual header/data split (configurable max_header_rows)
  3. structured — flat structured fallback (always succeeds)

Usage:
    from experiment.tree_builder import html_to_tree

    tree, strategy = html_to_tree(html_string)
"""

import os
import tempfile
import openpyxl

from utils.sheet_utils import html2workbook, sheet2structure
from utils.constants import DEFAULT_TABLE_NAME
from table2tree.feature_tree import (
    FeatureTree,
    IndexTree,
    BodyTree,
    IndexNode,
    BodyNode,
    construct_index_tree,
    construct_body_tree,
    construct_sheet,
    construct_feature_tree,
)
from table2tree.extract_excel import get_structured_xlsx_sheet


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _html_to_workbook_sheet(html_content: str):
    """HTML string → expanded openpyxl sheet (merged cells resolved).

    Returns (sheet, temp_path). Caller MUST call os.unlink(temp_path)
    when done to avoid leaking temp files.
    """
    wb = html2workbook(html_content)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        temp_path = tmp.name
    wb.save(temp_path)
    sheet = get_structured_xlsx_sheet(temp_path)
    return sheet, temp_path


# ---------------------------------------------------------------------------
# Strategy 1: Direct (auto header detection via split_schema_row)
# ---------------------------------------------------------------------------

def html_to_tree_direct(html_content: str) -> FeatureTree:
    """
    HTML → Excel → expand merges → construct_sheet().
    Uses ST-Raptor's split_schema_row() to auto-detect header rows.
    """
    wb = html2workbook(html_content)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        temp_path = tmp.name
    try:
        wb.save(temp_path)
        wb2 = openpyxl.load_workbook(temp_path, data_only=True)
        sheet = sheet2structure(wb2.active)
        return construct_sheet(sheet)
    finally:
        os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Strategy 2: Fixed (manual header row count)
# ---------------------------------------------------------------------------

def html_to_tree_fixed(html_content: str, max_header_rows: int = 2) -> FeatureTree:
    """
    Manually split first `max_header_rows` rows as schema, remainder as data.
    More robust when auto-detection fails.
    """
    sheet, temp_path = _html_to_workbook_sheet(html_content)
    try:
        nrows = sheet.max_row
        ncols = sheet.max_column

        # Schema sheet
        schema_wb = openpyxl.Workbook()
        schema_sheet = schema_wb.active
        for r in range(1, min(max_header_rows + 1, nrows + 1)):
            for c in range(1, ncols + 1):
                schema_sheet.cell(row=r, column=c).value = sheet.cell(row=r, column=c).value

        # Data sheet
        data_wb = openpyxl.Workbook()
        data_sheet = data_wb.active
        for r in range(max_header_rows + 1, nrows + 1):
            for c in range(1, ncols + 1):
                data_sheet.cell(row=r - max_header_rows, column=c).value = sheet.cell(
                    row=r, column=c
                ).value

        index_tree = construct_index_tree(schema_sheet)
        body_tree, _ = construct_body_tree(index_tree, data_sheet)
        return FeatureTree(index_tree=index_tree, body_tree=body_tree)
    finally:
        os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Strategy 3: Structured (flat, always succeeds)
# ---------------------------------------------------------------------------

def html_to_tree_structured(html_content: str) -> FeatureTree:
    """Treat full expanded sheet as structured data — last-resort fallback."""
    sheet, temp_path = _html_to_workbook_sheet(html_content)
    try:
        tree_dict = {DEFAULT_TABLE_NAME: sheet}
        return construct_feature_tree(tree_dict)
    finally:
        os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def html_to_tree(html_content: str, max_header_rows: int = 2):
    """
    Build HO-Tree from an HTML table string.

    Tries strategies in order: direct → fixed → structured.

    Returns:
        (FeatureTree, strategy_name)  on success
        (None,        'failed')       if all strategies fail
    """
    strategies = [
        ("direct", lambda: html_to_tree_direct(html_content)),
        ("fixed", lambda: html_to_tree_fixed(html_content, max_header_rows)),
        ("structured", lambda: html_to_tree_structured(html_content)),
    ]
    for name, fn in strategies:
        try:
            tree = fn()
            if tree is not None and tree.get_max_col() > 0:
                return tree, name
        except Exception:
            pass
    return None, "failed"

```

**Temp file cleanup** — replaced `tempfile.mktemp()` (leaks files) with `NamedTemporaryFile(delete=False)` + `os.unlink()` in `try/finally` blocks across all 3 strategies:

- [_html_to_workbook_sheet()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py#41-53) — documents caller must clean up
- [html_to_tree_direct()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py#59-74) — `finally: os.unlink(temp_path)`
- [html_to_tree_fixed()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py#80-111) — `finally: os.unlink(temp_path)`
- [html_to_tree_structured()](file:///c:/Users/nqmi/Downloads/Tree-Experiment/experiment/tree_builder.py#117-125) — `finally: os.unlink(temp_path)`

---

## Impact

| Change | Effect |
|---|---|
| Schema validation | You can now see how many tables have extraction errors |
| `table_metadata.json` | Enables strategy-vs-accuracy analysis in results |
| New CSV columns | Each experiment row now records which strategy built the tree and whether the schema matched |
| Normalization fix | Fewer false negatives — raw matches skip lossy normalization, no forced rounding |
| Temp file cleanup | No more `.xlsx` files leaked to temp directory |
