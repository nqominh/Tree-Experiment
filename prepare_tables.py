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
