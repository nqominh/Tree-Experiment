from .builders import build_column_paths, build_row_paths
from .detection import (
    detect_header_rows,
    detect_left_header_cols,
    detect_title,
    looks_like_metric_table,
)
from .models import ExtractedTable, StructureNode
from .parsing import parse_html_table


def extract_table_structure(html: str) -> ExtractedTable:
    grid = parse_html_table(html)
    nrows = len(grid)
    ncols = max((len(row) for row in grid), default=0)
    if nrows == 0 or ncols == 0:
        empty = StructureNode(None)
        return ExtractedTable(
            column_tree=empty,
            row_tree=empty,
            column_paths=[],
            row_paths=[],
            data_start_row=0,
            data_start_col=0,
            expected_cols=0,
            extracted_cols=0,
        )

    title, title_rows = detect_title(grid)
    header_rows = detect_header_rows(grid, title_rows)
    left_header_cols = detect_left_header_cols(grid, header_rows)

    if looks_like_metric_table(grid, title_rows, header_rows, left_header_cols):
        column_root = StructureNode(None)
        if title:
            column_root.add_path([title])
        row_root = StructureNode(None)
        return ExtractedTable(
            column_tree=column_root,
            row_tree=row_root,
            column_paths=[[title]] if title else [],
            row_paths=[],
            data_start_row=max(title_rows, header_rows),
            data_start_col=1,
            expected_cols=1,
            extracted_cols=1 if title else 0,
            title=title,
        )

    data_start_row = max(title_rows + header_rows, header_rows)
    data_start_col = left_header_cols

    column_paths = build_column_paths(grid, title_rows, header_rows, data_start_col)
    row_paths = build_row_paths(grid, data_start_row, data_start_col)

    column_root = StructureNode(None)
    for path in column_paths:
        column_root.add_path(path)

    row_root = StructureNode(None)
    for path in row_paths:
        row_root.add_path(path)

    expected_cols = max(ncols - data_start_col, 0)
    extracted_cols = len(column_paths)
    return ExtractedTable(
        column_tree=column_root,
        row_tree=row_root,
        column_paths=column_paths,
        row_paths=row_paths,
        data_start_row=data_start_row,
        data_start_col=data_start_col,
        expected_cols=expected_cols,
        extracted_cols=extracted_cols,
        title=title,
    )
