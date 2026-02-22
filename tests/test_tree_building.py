"""
test_tree_building.py — Verify HO-Tree construction works end-to-end.

Tests:
  1. Built-in sample HTML → tree via each strategy
  2. tree_to_json / tree_to_schema / tree_to_hierarchical_string output
  3. RealHiTBench table (if available) → tree round-trip
  4. Batch processing of multiple tables
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from experiment.tree_builder import (
    html_to_tree,
    html_to_tree_direct,
    html_to_tree_fixed,
    html_to_tree_structured,
)
from experiment.tree_output import (
    tree_to_hierarchical_string,
    tree_to_schema,
    tree_to_json,
    tree_to_json_legacy,
    tree_to_row_schema,
)
from experiment.prompt_templates import (
    build_baseline_prompt,
    build_hotree_prompt_schema,
    build_hotree_prompt_json,
    build_hotree_prompt_hierarchical,
    TEMPLATE_MAP,
)
from experiment.data_loader import discover_html_tables, get_field


# ---------------------------------------------------------------------------
# Sample HTML tables for testing
# ---------------------------------------------------------------------------

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
  <tr><td>2022</td><td>140</td><td>190</td><td>240</td><td>East</td></tr>
</table>
"""

REALHITBENCH_DIR = str(PROJECT_ROOT / "RealHiTBench")
HTML_CLEANED_DIR = os.path.join(REALHITBENCH_DIR, "html_cleaned_moderate")


class TestTreeBuilderStrategies(unittest.TestCase):
    """Test each tree-building strategy individually."""

    def test_direct_simple(self):
        tree = html_to_tree_direct(SIMPLE_HTML)
        self.assertIsNotNone(tree)
        self.assertGreater(tree.get_max_col(), 0)

    def test_direct_merged(self):
        tree = html_to_tree_direct(MERGED_HTML)
        self.assertIsNotNone(tree)

    def test_fixed_simple(self):
        tree = html_to_tree_fixed(SIMPLE_HTML, max_header_rows=1)
        self.assertIsNotNone(tree)
        self.assertGreater(tree.get_max_col(), 0)

    def test_fixed_merged(self):
        tree = html_to_tree_fixed(MERGED_HTML, max_header_rows=2)
        self.assertIsNotNone(tree)

    def test_structured_simple(self):
        tree = html_to_tree_structured(SIMPLE_HTML)
        self.assertIsNotNone(tree)

    def test_structured_merged(self):
        tree = html_to_tree_structured(MERGED_HTML)
        self.assertIsNotNone(tree)


class TestHtmlToTreeFallback(unittest.TestCase):
    """Test the main html_to_tree() entry point with auto-fallback."""

    def test_simple_returns_tree_and_strategy(self):
        tree, strategy = html_to_tree(SIMPLE_HTML)
        self.assertIsNotNone(tree)
        self.assertIn(strategy, ("direct", "fixed", "structured"))

    def test_merged_returns_tree_and_strategy(self):
        tree, strategy = html_to_tree(MERGED_HTML)
        self.assertIsNotNone(tree)
        self.assertIn(strategy, ("direct", "fixed", "structured"))

    def test_empty_html_fails(self):
        tree, strategy = html_to_tree("")
        # Should try all strategies and fail gracefully
        self.assertEqual(strategy, "failed")

    def test_garbage_html_fails(self):
        tree, strategy = html_to_tree("<div>not a table</div>")
        self.assertEqual(strategy, "failed")


class TestTreeOutput(unittest.TestCase):
    """Test output format converters."""

    def setUp(self):
        self.tree, _ = html_to_tree(MERGED_HTML)
        self.assertIsNotNone(self.tree)

    def test_schema_returns_list(self):
        schema = tree_to_schema(self.tree)
        self.assertIsInstance(schema, list)
        self.assertGreater(len(schema), 0)
        # All items should be strings
        for s in schema:
            self.assertIsInstance(s, str)

    def test_schema_contains_expected_columns(self):
        schema = tree_to_schema(self.tree)
        schema_str = " ".join(schema).lower()
        # Should have year, region and some sales-related columns
        self.assertTrue(
            any("year" in s.lower() for s in schema),
            f"Expected 'Year' in schema: {schema}",
        )

    def test_json_returns_dict(self):
        j = tree_to_json(self.tree)
        self.assertIsInstance(j, dict)
        self.assertGreater(len(j), 0)

    def test_json_is_serializable(self):
        j = tree_to_json(self.tree)
        serialized = json.dumps(j, ensure_ascii=False)
        self.assertIsInstance(serialized, str)
        self.assertGreater(len(serialized), 10)

    def test_hierarchical_string_not_empty(self):
        h = tree_to_hierarchical_string(self.tree)
        self.assertIsInstance(h, str)
        self.assertGreater(len(h), 0)

    def test_none_tree_returns_defaults(self):
        self.assertEqual(tree_to_schema(None), [])
        self.assertEqual(tree_to_json(None), {})
        self.assertEqual(tree_to_hierarchical_string(None), "")


class TestPromptTemplates(unittest.TestCase):
    """Test that all 4 prompt templates produce valid output."""

    def setUp(self):
        self.tree, _ = html_to_tree(MERGED_HTML)
        self.html = MERGED_HTML
        self.question = "What were the Q1 sales in 2021?"

    def test_baseline(self):
        prompt = build_baseline_prompt(self.html, self.question)
        self.assertIn(self.question, prompt)
        self.assertIn("html", prompt.lower())

    def test_schema_template(self):
        schema = tree_to_schema(self.tree)
        prompt = build_hotree_prompt_schema(self.html, self.question, schema=schema)
        self.assertIn(self.question, prompt)
        self.assertIn("Column", prompt)

    def test_json_template(self):
        j = tree_to_json(self.tree)
        prompt = build_hotree_prompt_json(self.html, self.question, tree_json=j)
        self.assertIn(self.question, prompt)
        self.assertIn("JSON", prompt)

    def test_hierarchical_template(self):
        h = tree_to_hierarchical_string(self.tree)
        prompt = build_hotree_prompt_hierarchical(
            self.html, self.question, tree_string=h
        )
        self.assertIn(self.question, prompt)
        self.assertIn("HO-Tree", prompt)

    def test_template_map_has_all_keys(self):
        expected = {"baseline", "schema", "json", "hierarchical"}
        self.assertEqual(set(TEMPLATE_MAP.keys()), expected)


class TestDataLoader(unittest.TestCase):
    """Test data loading utilities."""

    def test_get_field_first_match(self):
        item = {"Question": "What?", "q": "Which?"}
        self.assertEqual(get_field(item, ["question", "Question", "q"]), "What?")

    def test_get_field_fallback(self):
        item = {"q": "Which?"}
        self.assertEqual(get_field(item, ["question", "Question", "q"]), "Which?")

    def test_get_field_default(self):
        item = {"other": "value"}
        self.assertEqual(get_field(item, ["question", "Question"], default="N/A"), "N/A")


@unittest.skipUnless(
    os.path.isdir(HTML_CLEANED_DIR),
    f"RealHiTBench not found at {HTML_CLEANED_DIR}",
)
class TestRealHiTBenchIntegration(unittest.TestCase):
    """Integration tests using actual RealHiTBench tables."""

    def test_discover_tables(self):
        tables = discover_html_tables(HTML_CLEANED_DIR, limit=5)
        self.assertGreater(len(tables), 0)
        for table_id, html in tables.items():
            self.assertIsInstance(html, str)
            self.assertIn("<", html)  # should be HTML

    def test_build_tree_from_real_table(self):
        tables = discover_html_tables(HTML_CLEANED_DIR, limit=3)
        for table_id, html in tables.items():
            tree, strategy = html_to_tree(html)
            self.assertIsNotNone(
                tree, f"Tree building failed for {table_id} (strategy={strategy})"
            )
            self.assertIn(strategy, ("direct", "fixed", "structured"))

            # Verify all output formats work
            schema = tree_to_schema(tree)
            self.assertIsInstance(schema, list)
            j = tree_to_json(tree)
            self.assertIsInstance(j, dict)
            h = tree_to_hierarchical_string(tree)
            self.assertIsInstance(h, str)

    def test_batch_5_tables(self):
        """Process 5 tables and verify >= 80% succeed."""
        tables = discover_html_tables(HTML_CLEANED_DIR, limit=5)
        successes = 0
        for table_id, html in tables.items():
            tree, strategy = html_to_tree(html)
            if tree is not None:
                successes += 1
        rate = successes / len(tables) * 100
        self.assertGreaterEqual(
            rate, 80, f"Only {successes}/{len(tables)} tables succeeded ({rate:.0f}%)"
        )


# ---------------------------------------------------------------------------
# 7. Bidirectional Hierarchy Tests
# ---------------------------------------------------------------------------

class TestBidirectionalHierarchy(unittest.TestCase):
    """Tests for the new row-index-tree and addressed-cell JSON format."""

    ACTIVITYTIME_PATH = os.path.join(
        PROJECT_ROOT, "RealHiTBench", "html", "activitytime-table01.html"
    )

    @unittest.skipUnless(
        os.path.exists(os.path.join(PROJECT_ROOT, "RealHiTBench", "html", "activitytime-table01.html")),
        "activitytime-table01.html not found"
    )
    def test_indentation_row_tree(self):
        """Row tree built from activitytime's indentation hierarchy."""
        with open(self.ACTIVITYTIME_PATH, encoding="utf-8") as f:
            html = f.read()
        tree, strategy = html_to_tree(html)
        self.assertIsNotNone(tree, "Tree construction failed")
        self.assertIsNotNone(tree.row_index_tree, "row_index_tree should be populated")
        # Should have leaf nodes from indented row headers
        leaves = tree.row_index_tree.leaf_nodes
        self.assertGreater(len(leaves), 0, "Row tree should have leaves")
        # Check some expected labels exist
        leaf_values = [str(n.value) for n in leaves]
        # "Sleeping" should be a leaf (indented under Personal care)
        self.assertTrue(
            any("Sleeping" in v for v in leaf_values),
            f"Expected 'Sleeping' in row leaves, got: {leaf_values[:10]}"
        )

    @unittest.skipUnless(
        os.path.exists(os.path.join(PROJECT_ROOT, "RealHiTBench", "html", "activitytime-table01.html")),
        "activitytime-table01.html not found"
    )
    def test_new_json_format(self):
        """New __json__() returns col_tree, row_tree, cells."""
        with open(self.ACTIVITYTIME_PATH, encoding="utf-8") as f:
            html = f.read()
        tree, _ = html_to_tree(html)
        self.assertIsNotNone(tree)
        j = tree_to_json(tree)
        self.assertIn("col_tree", j, "Missing col_tree key")
        self.assertIn("row_tree", j, "Missing row_tree key")
        self.assertIn("cells", j, "Missing cells key")
        self.assertIsInstance(j["cells"], list)
        self.assertGreater(len(j["cells"]), 0, "Should have some cells")
        # Each cell should have row_path, col_path, value
        cell = j["cells"][0]
        self.assertIn("row_path", cell)
        self.assertIn("col_path", cell)
        self.assertIn("value", cell)

    @unittest.skipUnless(
        os.path.exists(os.path.join(PROJECT_ROOT, "RealHiTBench", "html", "activitytime-table01.html")),
        "activitytime-table01.html not found"
    )
    def test_row_schema_output(self):
        """tree_to_row_schema() returns non-empty list."""
        with open(self.ACTIVITYTIME_PATH, encoding="utf-8") as f:
            html = f.read()
        tree, _ = html_to_tree(html)
        self.assertIsNotNone(tree)
        row_schema = tree_to_row_schema(tree)
        self.assertIsInstance(row_schema, list)
        self.assertGreater(len(row_schema), 0, "Row schema should not be empty")

    @unittest.skipUnless(
        os.path.exists(os.path.join(PROJECT_ROOT, "RealHiTBench", "html", "activitytime-table01.html")),
        "activitytime-table01.html not found"
    )
    def test_legacy_json_compat(self):
        """__json_legacy__() still produces the old format."""
        with open(self.ACTIVITYTIME_PATH, encoding="utf-8") as f:
            html = f.read()
        tree, _ = html_to_tree(html)
        self.assertIsNotNone(tree)
        j = tree_to_json_legacy(tree)
        self.assertIsInstance(j, dict)
        # Legacy format should have "table" key or be a flat dict
        # Should NOT have col_tree/row_tree
        self.assertNotIn("col_tree", j, "Legacy format should not have col_tree")

    def test_th_map_annotation(self):
        """html2workbook() should set _th_map on the worksheet."""
        from utils.sheet_utils import html2workbook
        html = """<table>
            <tr><th>H1</th><th>H2</th></tr>
            <tr><td>A</td><td>B</td></tr>
        </table>"""
        wb = html2workbook(html)
        ws = wb.active
        self.assertTrue(hasattr(ws, '_th_map'), "ws should have _th_map attribute")
        self.assertTrue(ws._th_map.get((1, 1), False), "H1 at (1,1) should be th")
        self.assertTrue(ws._th_map.get((1, 2), False), "H2 at (1,2) should be th")
        self.assertFalse(ws._th_map.get((2, 1), False), "A at (2,1) should not be th")
        self.assertFalse(ws._th_map.get((2, 2), False), "B at (2,2) should not be th")


if __name__ == "__main__":
    unittest.main(verbosity=2)
