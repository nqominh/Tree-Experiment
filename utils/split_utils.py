"""
split_utils.py - Schema / Data splitting helpers.

Provides split_schema_row() to separate an openpyxl sheet into
column-schema and data regions, and split_schema_column() for the
left row-schema region.
"""

import re

from utils.sheet_utils import get_merge_cell_size, get_sub_sheet


_NUMERIC_RE = re.compile(
    r"""
    ^\s*
    [\(\-]?
    (?:
        \d{1,3}(?:,\d{3})+|\d+
    )
    (?:\.\d+)?
    %?
    [\)]?
    \s*$
    """,
    re.VERBOSE,
)


def _normalize_text(value):
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_numeric_like(value) -> bool:
    text = _normalize_text(value)
    if not text:
        return False
    candidate = (
        text.replace("$", "")
        .replace(",", "")
        .replace("*", "")
        .replace("-", "-")
        .replace("–", "-")
    )
    return bool(_NUMERIC_RE.match(candidate))


def _row_stats(sheet, row, start_col, end_col):
    values = []
    non_empty = 0
    numeric = 0
    for col in range(start_col, end_col + 1):
        raw = sheet.cell(row=row, column=col).value
        text = _normalize_text(raw)
        if text:
            non_empty += 1
            values.append(text)
            if _is_numeric_like(text):
                numeric += 1
    unique = len(set(values))
    return {
        "values": values,
        "non_empty": non_empty,
        "numeric": numeric,
        "unique": unique,
    }


def _is_title_row(sheet, row, ncols):
    """Check if a row is a title row (one dominant label, little numeric content)."""
    stats = _row_stats(sheet, row, 1, ncols)
    if stats["non_empty"] == 0:
        return True

    first_val = stats["values"][0]
    same_value_count = sum(1 for v in stats["values"] if v == first_val)
    dominant_ratio = same_value_count / max(stats["non_empty"], 1)
    numeric_ratio = stats["numeric"] / max(stats["non_empty"], 1)
    return dominant_ratio >= 0.8 and numeric_ratio <= 0.2


def _is_row_group_header(sheet, row, ncols):
    """Check if a row is a row-group header (text in col1, mostly empty elsewhere)."""
    first_val = _normalize_text(sheet.cell(row=row, column=1).value)
    if not first_val:
        return False

    empty_count = 0
    for col in range(2, ncols + 1):
        cell_val = _normalize_text(sheet.cell(row=row, column=col).value)
        if not cell_val:
            empty_count += 1

    data_cols = ncols - 1
    return data_cols > 0 and empty_count >= data_cols * 0.8


def _is_data_row(sheet, row, ncols):
    """Check if a row contains likely data values."""
    stats = _row_stats(sheet, row, 2, ncols)
    if stats["non_empty"] == 0:
        return False

    numeric_ratio = stats["numeric"] / max(stats["non_empty"], 1)
    return stats["numeric"] >= 2 and numeric_ratio >= 0.5


def _is_column_header_row(sheet, row, ncols):
    """Check if a row is likely a column-header row."""
    if _is_row_group_header(sheet, row, ncols):
        return False

    stats = _row_stats(sheet, row, 1, ncols)
    if stats["non_empty"] < 2:
        return False

    numeric_ratio = stats["numeric"] / max(stats["non_empty"], 1)
    return stats["unique"] >= 2 and numeric_ratio <= 0.4


def _find_schema_height_by_content(sheet, nrows, ncols):
    """Find header height by detecting where data rows start."""
    max_scan = min(nrows, 15)

    start_row = 1
    while start_row <= min(max_scan, 5) and _is_title_row(sheet, start_row, ncols):
        start_row += 1

    schema_end = max(0, start_row - 1)
    consecutive_data_rows = 0

    for row in range(start_row, max_scan + 1):
        if _is_data_row(sheet, row, ncols):
            consecutive_data_rows += 1
            if consecutive_data_rows >= 2:
                return max(schema_end, row - 2)
            continue

        consecutive_data_rows = 0

        if _is_row_group_header(sheet, row, ncols):
            return max(schema_end, row - 1)

        if _is_column_header_row(sheet, row, ncols):
            schema_end = row

    # Guard against over-growing header depth on noisy tables.
    return max(schema_end, min(start_row + 2, nrows))


def split_schema_row(sheet):
    """Split sheet into (schema_sub_sheet, data_sub_sheet)."""
    nrows = sheet.max_row
    ncols = sheet.max_column

    if nrows == 0 or ncols == 0:
        return (None, None)

    height = 1
    has_merges = False
    for col in range(1, ncols + 1):
        cell = sheet.cell(row=1, column=col)
        x1, y1, x2, y2 = get_merge_cell_size(sheet, cell.coordinate)
        if x2 > x1 or y2 > y1:
            has_merges = True
        height = max(height, x2)

    if not has_merges or height <= 1:
        height = _find_schema_height_by_content(sheet, nrows, ncols)

    height = min(height, nrows)

    return (
        get_sub_sheet(sheet, 1, 1, height, ncols),
        get_sub_sheet(sheet, height + 1, 1, nrows, ncols) if height < nrows else None,
    )


def _is_numeric_column(sheet, col, start_row, end_row):
    """Check if a column is predominantly numeric (data column)."""
    numeric_count = 0
    non_empty_count = 0
    for row in range(start_row, end_row + 1):
        val = _normalize_text(sheet.cell(row=row, column=col).value)
        if val:
            non_empty_count += 1
            if _is_numeric_like(val):
                numeric_count += 1
    return non_empty_count > 0 and numeric_count >= non_empty_count * 0.5


def _find_schema_width_by_content(sheet, nrows, ncols):
    """Find row-schema width by detecting where label columns end."""
    scan_end = min(nrows, 30)
    if scan_end < 2:
        return 1

    max_left = min(4, ncols)
    best_width = 1

    for col in range(1, max_left + 1):
        if _is_numeric_column(sheet, col, 2, scan_end):
            return max(1, col - 1)

        values = set()
        text_count = 0
        non_empty = 0
        for row in range(2, scan_end + 1):
            val = _normalize_text(sheet.cell(row=row, column=col).value)
            if not val:
                continue
            non_empty += 1
            values.add(val)
            if not _is_numeric_like(val):
                text_count += 1

        if non_empty == 0:
            continue

        text_ratio = text_count / non_empty
        diversity = len(values) / non_empty
        if text_ratio >= 0.6 and diversity >= 0.3:
            best_width = col

    return best_width


def split_schema_column(sheet):
    """Split sheet into (row_schema_sub_sheet, data_sub_sheet) by columns."""
    nrows = sheet.max_row
    ncols = sheet.max_column

    if nrows == 0 or ncols == 0:
        return (None, None)

    width = 1
    has_merges = False
    for row in range(1, nrows + 1):
        cell = sheet.cell(row=row, column=1)
        x1, y1, x2, y2 = get_merge_cell_size(sheet, cell.coordinate)
        if x2 > x1 or y2 > y1:
            has_merges = True
        width = max(width, y2)

    if not has_merges or width <= 1:
        width = _find_schema_width_by_content(sheet, nrows, ncols)

    width = min(width, ncols)

    return (
        get_sub_sheet(sheet, 1, 1, nrows, width),
        get_sub_sheet(sheet, 1, width + 1, nrows, ncols) if width < ncols else None,
    )

