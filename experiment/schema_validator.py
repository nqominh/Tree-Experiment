"""
schema_validator.py — Validate extracted tree schema against source HTML

Compares the number of leaf columns in the extracted IndexTree against
the actual column count in the HTML table to detect extraction errors.
"""

from bs4 import BeautifulSoup
from table2tree.feature_tree import FeatureTree


def _count_html_data_columns(html_content: str) -> int:
    """Count actual data columns from HTML table.

    Strategy: find the first <tbody> <tr> (or first <tr> after <thead>)
    and count the number of <td>/<th> cells, accounting for colspan.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table")
    if table is None:
        return 0

    # Try tbody first, fall back to all rows
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    # Skip header rows (rows that are all <th>)
    data_row = None
    for row in rows:
        cells = row.find_all(["td", "th"])
        td_count = sum(1 for c in cells if c.name == "td")
        if td_count > 0:
            data_row = row
            break

    if data_row is None:
        # No <td> rows found — use last row as fallback
        if rows:
            data_row = rows[-1]
        else:
            return 0

    # Count columns accounting for colspan
    col_count = 0
    for cell in data_row.find_all(["td", "th"]):
        col_count += int(cell.get("colspan", 1))

    return col_count


def validate_schema(tree: FeatureTree, html_content: str) -> dict:
    """Validate extracted tree against source HTML.

    Returns:
        {
            "expected_cols": int,   # from HTML
            "extracted_cols": int,  # from tree leaf nodes
            "match": bool,
        }
    """
    if tree is None or tree.index_tree is None:
        return {"expected_cols": 0, "extracted_cols": 0, "match": False}

    expected = _count_html_data_columns(html_content)
    extracted = len(tree.index_tree.leaf_nodes)

    return {
        "expected_cols": expected,
        "extracted_cols": extracted,
        "match": expected == extracted,
    }
