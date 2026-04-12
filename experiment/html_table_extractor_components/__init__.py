"""Componentized internals for HTML table structure extraction."""

from .api import extract_table_structure
from .builders import build_column_paths, build_row_paths, dedupe_paths
from .detection import (
    detect_header_rows,
    detect_left_header_cols,
    detect_title,
    looks_like_metric_table,
)
from .models import ExtractedTable, HtmlCell, StructureNode
from .parsing import parse_html_table, unique_cells
from .rendering import render_indented
from .text_utils import is_numeric_like, leading_indent, normalize_text

__all__ = [
    "ExtractedTable",
    "HtmlCell",
    "StructureNode",
    "extract_table_structure",
    "render_indented",
    "parse_html_table",
    "unique_cells",
    "detect_title",
    "detect_header_rows",
    "detect_left_header_cols",
    "looks_like_metric_table",
    "build_column_paths",
    "build_row_paths",
    "dedupe_paths",
    "normalize_text",
    "leading_indent",
    "is_numeric_like",
]
