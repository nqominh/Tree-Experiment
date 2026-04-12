"""Behavior equivalence tests for html_table_extractor refactor.

Compares outputs from:
- legacy monolithic implementation
- new componentized implementation
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from experiment import html_table_extractor as new_extractor
from experiment import html_table_extractor_legacy as old_extractor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_TABLES_DIR = PROJECT_ROOT / "RealHiTBench" / "html"
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts" / "html_table_extractor"


SIMPLE_HTML = """\
<table>
  <tr><td>Name</td><td>Age</td><td>City</td></tr>
  <tr><td>Alice</td><td>30</td><td>NYC</td></tr>
  <tr><td>Bob</td><td>25</td><td>LA</td></tr>
</table>
"""

MERGED_HTML = """\
<table>
  <tr>
    <td rowspan="2">Year</td>
    <td colspan="3">Sales</td>
    <td rowspan="2">Region</td>
  </tr>
  <tr>
    <td>Q1</td><td>Q2</td><td>Q3</td>
  </tr>
  <tr><td>2020</td><td>100</td><td>150</td><td>200</td><td>North</td></tr>
  <tr><td>2021</td><td>120</td><td>170</td><td>220</td><td>South</td></tr>
</table>
"""

METRIC_HTML = """\
<table>
  <tr><th colspan="2">Population Snapshot</th></tr>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total</td><td>1,234</td></tr>
  <tr><td>Growth %</td><td>3.4%</td></tr>
  <tr><td>Delta</td><td>+42</td></tr>
</table>
"""


def _tree_tuple(node) -> tuple:
    if node is None:
        return ()
    return (
        node.label,
        tuple(_tree_tuple(child) for child in node.children),
    )


def _normalize_output(result) -> dict:
    return {
        "column_paths": result.column_paths,
        "row_paths": result.row_paths,
        "data_start_row": result.data_start_row,
        "data_start_col": result.data_start_col,
        "expected_cols": result.expected_cols,
        "extracted_cols": result.extracted_cols,
        "strategy": result.strategy,
        "title": result.title,
        "column_tree": _tree_tuple(result.column_tree),
        "row_tree": _tree_tuple(result.row_tree),
    }


def _run_both(html: str) -> tuple[dict, dict]:
    old = old_extractor.extract_table_structure(html)
    new = new_extractor.extract_table_structure(html)
    return _normalize_output(old), _normalize_output(new)


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("_")
    return cleaned or "table"


def _write_artifacts(case_name: str, html: str, old: dict, new: dict) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(case_name)

    payload = {
        "case": case_name,
        "matches": old == new,
        "old": old,
        "new": new,
    }

    json_path = ARTIFACTS_DIR / f"{stem}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    old_result = old_extractor.extract_table_structure(html)
    new_result = new_extractor.extract_table_structure(html)
    report_lines = [
        f"case: {case_name}",
        f"matches: {old == new}",
        "",
        "[OLD] column tree",
        old_extractor.render_indented(old_result.column_tree),
        "",
        "[OLD] row tree",
        old_extractor.render_indented(old_result.row_tree),
        "",
        "[NEW] column tree",
        new_extractor.render_indented(new_result.column_tree),
        "",
        "[NEW] row tree",
        new_extractor.render_indented(new_result.row_tree),
        "",
    ]

    txt_path = ARTIFACTS_DIR / f"{stem}.txt"
    txt_path.write_text("\n".join(report_lines), encoding="utf-8")


class TestHtmlTableExtractorEquivalence(unittest.TestCase):
    def test_inline_simple_table(self):
        old, new = _run_both(SIMPLE_HTML)
        _write_artifacts("inline_simple_table", SIMPLE_HTML, old, new)
        self.assertEqual(old, new)

    def test_inline_merged_table(self):
        old, new = _run_both(MERGED_HTML)
        _write_artifacts("inline_merged_table", MERGED_HTML, old, new)
        self.assertEqual(old, new)

    def test_inline_metric_table(self):
        old, new = _run_both(METRIC_HTML)
        _write_artifacts("inline_metric_table", METRIC_HTML, old, new)
        self.assertEqual(old, new)

    def test_render_indented_equivalence(self):
        old_result = old_extractor.extract_table_structure(MERGED_HTML)
        new_result = new_extractor.extract_table_structure(MERGED_HTML)

        old_col = old_extractor.render_indented(old_result.column_tree)
        new_col = new_extractor.render_indented(new_result.column_tree)
        old_row = old_extractor.render_indented(old_result.row_tree)
        new_row = new_extractor.render_indented(new_result.row_tree)

        old, new = _run_both(MERGED_HTML)
        _write_artifacts("render_indented_equivalence", MERGED_HTML, old, new)

        self.assertEqual(old_col, new_col)
        self.assertEqual(old_row, new_row)

    @unittest.skipUnless(REAL_TABLES_DIR.is_dir(), "RealHiTBench/html directory not found")
    def test_real_tables_subset_equivalence(self):
        html_files = sorted(REAL_TABLES_DIR.glob("*.html"))[:5]
        self.assertGreater(len(html_files), 0, "No HTML files found for equivalence test")

        for path in html_files:
            with self.subTest(table=path.name):
                html = path.read_text(encoding="utf-8", errors="ignore")
                old, new = _run_both(html)
                _write_artifacts(path.stem, html, old, new)
                self.assertEqual(old, new)


if __name__ == "__main__":
    unittest.main()
