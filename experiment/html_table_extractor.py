"""
html_table_extractor.py -- Standalone HTML table structure extraction.

This module keeps the public API stable while delegating implementation
to componentized internals in experiment/html_table_extractor_components.
"""

from __future__ import annotations

# Public dataclasses
from .html_table_extractor_components.models import ExtractedTable, HtmlCell, StructureNode

# Public API
from .html_table_extractor_components.api import extract_table_structure
from .html_table_extractor_components.rendering import render_indented

# Backward-compatible internal helpers (kept for compatibility)
from .html_table_extractor_components.text_utils import (
    is_numeric_like as _is_numeric_like,
    leading_indent as _leading_indent,
    normalize_text as _normalize_text,
)
from .html_table_extractor_components.parsing import (
    parse_html_table as _parse_html_table,
    unique_cells as _unique_cells,
)
from .html_table_extractor_components.detection import (
    detect_header_rows as _detect_header_rows,
    detect_left_header_cols as _detect_left_header_cols,
    detect_title as _detect_title,
    looks_like_metric_table as _looks_like_metric_table,
)
from .html_table_extractor_components.builders import (
    build_column_paths as _build_column_paths,
    build_row_paths as _build_row_paths,
    dedupe_paths as _dedupe_paths,
)

__all__ = [
    "HtmlCell",
    "StructureNode",
    "ExtractedTable",
    "extract_table_structure",
    "render_indented",
]
