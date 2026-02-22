"""
highlight_fuzzy.py -- Find EM=1 rows where the answer matched only after normalization.

A "fuzzy match" is one where:
  EM == 1  (normalized strings match)
  BUT raw model_answer != raw correct_answer  (they differ before normalization)

Outputs: experiment_results_highlighted.html
"""

import csv
import re
from pathlib import Path

INPUT_CSV  = Path("experiment_results.csv")
OUTPUT_HTML = Path("experiment_results_highlighted.html")


def normalize(s: str) -> str:
    s = s.strip().strip('"').strip("'").rstrip(".").strip()
    s = s.replace("$", "").replace("%", "").replace(",", "")
    return " ".join(s.lower().split())


def is_fuzzy(model_answer: str, correct_answer: str, em: str) -> bool:
    """True if EM=1 but raw strings differ (i.e., normalization was needed)."""
    return (em.strip() == "1"
            and model_answer.strip() != correct_answer.strip()
            and normalize(model_answer) == normalize(correct_answer))


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []
    return headers, rows


def render_html(headers: list[str], rows: list[dict]) -> str:
    total      = len(rows)
    em_correct = sum(1 for r in rows if r.get("EM", "0").strip() == "1")
    fuzzy_rows = [r for r in rows if is_fuzzy(
        r.get("model_answer", ""), r.get("correct_answer", ""), r.get("EM", "0"))]

    display_cols = ["id", "question", "correct_answer", "model_answer", "EM"]
    display_cols = [c for c in display_cols if c in headers]

    def cell(value: str, is_header=False) -> str:
        tag = "th" if is_header else "td"
        safe = (value.replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace('"', "&quot;"))
        return f"<{tag}>{safe}</{tag}>"

    rows_html = []
    for r in rows:
        fuzzy  = is_fuzzy(r.get("model_answer",""), r.get("correct_answer",""), r.get("EM","0"))
        em_val = r.get("EM","0").strip()

        if fuzzy:
            style = 'class="fuzzy"'        # red — fuzzy match
        elif em_val == "1":
            style = 'class="correct"'      # green — clean exact match
        else:
            style = 'class="wrong"'        # default — wrong

        cols = "".join(cell(r.get(c, "")) for c in display_cols)
        rows_html.append(f"  <tr {style}>{cols}</tr>")

    header_html = "".join(cell(c, is_header=True) for c in display_cols)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Experiment Results — Fuzzy Match Audit</title>
<style>
  body     {{ font-family: Arial, sans-serif; font-size: 13px; margin: 20px; }}
  h1       {{ font-size: 18px; }}
  .summary {{ margin-bottom: 16px; padding: 10px; background: #f5f5f5; border-radius: 6px; }}
  table    {{ border-collapse: collapse; width: 100%; }}
  th, td   {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; }}
  th       {{ background: #333; color: #fff; }}
  tr.correct  {{ background: #e6f4ea; }}
  tr.fuzzy    {{ background: #fce8e6; }}
  tr.wrong    {{ background: #fff; }}
  .legend  {{ margin-bottom: 12px; display: flex; gap: 16px; }}
  .dot     {{ display: inline-block; width: 14px; height: 14px;
              border-radius: 3px; margin-right: 4px; vertical-align: middle; }}
</style>
</head>
<body>
<h1>Experiment Results — Fuzzy Match Audit</h1>
<div class="summary">
  <strong>Total:</strong> {total} &nbsp;|&nbsp;
  <strong>EM Correct:</strong> {em_correct} ({em_correct/total*100:.1f}%) &nbsp;|&nbsp;
  <strong>Fuzzy (EM=1, raw differs):</strong> {len(fuzzy_rows)} rows highlighted in red
</div>
<div class="legend">
  <span><span class="dot" style="background:#e6f4ea;border:1px solid #aaa"></span>Clean exact match (EM=1, strings identical)</span>
  <span><span class="dot" style="background:#fce8e6;border:1px solid #aaa"></span>Fuzzy match (EM=1 only after normalization)</span>
  <span><span class="dot" style="background:#fff;border:1px solid #aaa"></span>Wrong (EM=0)</span>
</div>
<table>
<thead><tr>{header_html}</tr></thead>
<tbody>
{"".join(rows_html)}
</tbody>
</table>
</body>
</html>"""


if __name__ == "__main__":
    if not INPUT_CSV.exists():
        print(f"ERROR: {INPUT_CSV} not found. Run run_experiment_csv.py first.")
        raise SystemExit(1)

    headers, rows = load_csv(INPUT_CSV)
    html = render_html(headers, rows)
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    fuzzy_count = sum(1 for r in rows if is_fuzzy(
        r.get("model_answer",""), r.get("correct_answer",""), r.get("EM","0")))

    print(f"Done. {len(rows)} rows processed, {fuzzy_count} fuzzy matches highlighted.")
    print(f"Output: {OUTPUT_HTML.resolve()}")
