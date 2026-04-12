"""
html_table_extractor.py -- Standalone HTML table structure extraction.

This module builds prompt-facing column and row hierarchies directly from
HTML tables without relying on the ST-Raptor HO-Tree implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from bs4 import BeautifulSoup

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


def _normalize_text(value: str) -> str:
    text = value.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _leading_indent(value: str) -> int:
    expanded = value.replace("\xa0", " ")
    return len(expanded) - len(expanded.lstrip(" "))


def _is_numeric_like(value: str) -> bool:
    text = _normalize_text(value)
    if not text:
        return False
    candidate = text.replace("$", "").replace("£", "").replace("€", "")
    candidate = candidate.replace("¥", "").replace(",", "").replace("*", "")
    candidate = candidate.replace("−", "-").replace("–", "-")
    return bool(_NUMERIC_RE.match(candidate))


@dataclass(eq=False)
class HtmlCell:
    text: str
    raw_text: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False

    @property
    def normalized(self) -> str:
        return _normalize_text(self.text)

    @property
    def indent(self) -> int:
        return _leading_indent(self.raw_text or self.text)


@dataclass
class StructureNode:
    label: str | None
    children: list["StructureNode"] = field(default_factory=list)
    _index: dict[str, "StructureNode"] = field(default_factory=dict, init=False, repr=False)

    def add_path(self, path: list[str]) -> None:
        node = self
        for label in path:
            if not label:
                continue
            child = node._index.get(label)
            if child is None:
                child = StructureNode(label=label)
                node._index[label] = child
                node.children.append(child)
            node = child


@dataclass
class ExtractedTable:
    column_tree: StructureNode
    row_tree: StructureNode
    column_paths: list[list[str]]
    row_paths: list[list[str]]
    data_start_row: int
    data_start_col: int
    expected_cols: int
    extracted_cols: int
    strategy: str = "html_grid"
    title: str = ""


def extract_table_structure(html: str) -> ExtractedTable:
    grid = _parse_html_table(html)
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

    title, title_rows = _detect_title(grid)
    header_rows = _detect_header_rows(grid, title_rows)
    left_header_cols = _detect_left_header_cols(grid, header_rows)

    if _looks_like_metric_table(grid, title_rows, header_rows, left_header_cols):
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

    column_paths = _build_column_paths(grid, title_rows, header_rows, data_start_col)
    row_paths = _build_row_paths(grid, data_start_row, data_start_col)

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


def render_indented(root: StructureNode) -> str:
    if root is None or not root.children:
        return "(none)"

    lines: list[str] = []

    def walk(node: StructureNode, depth: int) -> None:
        if node.label:
            lines.append(f"{'  ' * depth}{node.label}")
        next_depth = depth + (1 if node.label else 0)
        for child in node.children:
            walk(child, next_depth)

    walk(root, 0)
    return "\n".join(lines) if lines else "(none)"


def _parse_html_table(html: str) -> list[list[HtmlCell | None]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    grid: list[list[HtmlCell | None]] = []
    rows = table.find_all("tr")
    for r, tr in enumerate(rows):
        while len(grid) <= r:
            grid.append([])

        c = 0
        cells = tr.find_all(["td", "th"], recursive=False)
        for cell in cells:
            while c < len(grid[r]) and grid[r][c] is not None:
                c += 1

            raw_text = cell.get_text(" ", strip=False)
            text = cell.get_text(" ", strip=True)
            rowspan = int(cell.get("rowspan", 1) or 1)
            colspan = int(cell.get("colspan", 1) or 1)
            obj = HtmlCell(
                text=text,
                raw_text=raw_text,
                row=r,
                col=c,
                rowspan=rowspan,
                colspan=colspan,
                is_header=(cell.name == "th"),
            )
            for rr in range(r, r + rowspan):
                while len(grid) <= rr:
                    grid.append([])
                while len(grid[rr]) < c + colspan:
                    grid[rr].append(None)
                for cc in range(c, c + colspan):
                    grid[rr][cc] = obj
            c += colspan

    width = max((len(row) for row in grid), default=0)
    for row in grid:
        if len(row) < width:
            row.extend([None] * (width - len(row)))
    return grid


def _detect_title(grid: list[list[HtmlCell | None]]) -> tuple[str, int]:
    title = ""
    title_rows = 0
    width = len(grid[0]) if grid else 0
    for row in grid[:3]:
        nonempty = [cell for cell in row if cell and cell.normalized]
        if not nonempty:
            title_rows += 1
            continue
        unique = []
        seen: set[int] = set()
        for cell in nonempty:
            ident = id(cell)
            if ident not in seen:
                seen.add(ident)
                unique.append(cell)
        if len(unique) <= 2 and any(cell.colspan >= max(width - 1, 1) for cell in unique):
            if not title:
                title = unique[0].normalized
            title_rows += 1
            continue
        if len(unique) == 1 and unique[0].normalized:
            if not title:
                title = unique[0].normalized
            title_rows += 1
            continue
        break
    return title, title_rows


def _detect_header_rows(grid: list[list[HtmlCell | None]], title_rows: int) -> int:
    header_rows = 0
    max_scan = min(len(grid), title_rows + 6)
    for ridx in range(title_rows, max_scan):
        row = grid[ridx]
        unique = _unique_cells(row)
        nonempty = [cell for cell in unique if cell.normalized]
        if not nonempty:
            header_rows += 1
            continue

        numeric = sum(1 for cell in nonempty if _is_numeric_like(cell.text))
        has_span = any(cell.rowspan > 1 or cell.colspan > 1 for cell in nonempty)
        mostly_text = numeric <= max(1, len(nonempty) // 3)
        if has_span or all(cell.is_header for cell in nonempty) or mostly_text:
            header_rows += 1
            continue
        break

    if header_rows == 0 and len(grid) > title_rows:
        first = _unique_cells(grid[title_rows])
        if any(cell.is_header for cell in first):
            header_rows = 1
    return header_rows


def _detect_left_header_cols(grid: list[list[HtmlCell | None]], header_rows: int) -> int:
    if not grid:
        return 0
    ncols = len(grid[0])
    start_row = header_rows
    max_cols = min(ncols, 4)
    best = 0
    for c in range(max_cols):
        column_cells = []
        data_cells = []
        for r in range(start_row, len(grid)):
            cell = grid[r][c]
            if cell and cell.normalized:
                column_cells.append(cell)
            for cc in range(c + 1, ncols):
                candidate = grid[r][cc]
                if candidate and candidate.normalized:
                    data_cells.append(candidate)
        if not column_cells or not data_cells:
            break
        textish = sum(1 for cell in column_cells if not _is_numeric_like(cell.text))
        following_numeric = sum(1 for cell in data_cells if _is_numeric_like(cell.text))
        if textish >= max(1, len(column_cells) // 2) and following_numeric >= max(2, len(data_cells) // 4):
            best = c + 1
            continue
        if c == 0 and following_numeric > len(column_cells):
            best = 1
        break
    return best


def _looks_like_metric_table(
    grid: list[list[HtmlCell | None]],
    title_rows: int,
    header_rows: int,
    left_header_cols: int,
) -> bool:
    if not grid or len(grid[0]) != 2:
        return False
    if title_rows == 0:
        return False
    if left_header_cols != 1:
        return False
    start_row = title_rows + header_rows
    value_rows = 0
    numeric_or_formula_like = 0
    for row in grid[start_row:]:
        left = row[0]
        right = row[1]
        left_text = left.normalized if left else ""
        right_text = right.normalized if right else ""
        if not left_text and not right_text:
            continue
        if left_text and right_text:
            value_rows += 1
            if _is_numeric_like(right_text) or any(ch.isdigit() for ch in right_text):
                numeric_or_formula_like += 1
    return value_rows >= 3 and numeric_or_formula_like >= max(2, value_rows // 2)


def _build_column_paths(
    grid: list[list[HtmlCell | None]],
    title_rows: int,
    header_rows: int,
    data_start_col: int,
) -> list[list[str]]:
    start = title_rows
    end = title_rows + header_rows
    if end <= start:
        return []

    paths: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    ncols = len(grid[0]) if grid else 0
    for c in range(data_start_col, ncols):
        path: list[str] = []
        last = None
        for r in range(start, end):
            cell = grid[r][c]
            if not cell:
                continue
            label = cell.normalized
            if not label or label == last:
                continue
            path.append(label)
            last = label
        normalized = tuple(path)
        if normalized and normalized not in seen:
            paths.append(path)
            seen.add(normalized)
    return paths


def _build_row_paths(
    grid: list[list[HtmlCell | None]],
    data_start_row: int,
    data_start_col: int,
) -> list[list[str]]:
    if not grid:
        return []

    row_paths: list[list[str]] = []
    first_col_cells = [
        grid[r][0]
        for r in range(data_start_row, len(grid))
        if grid[r] and grid[r][0] and grid[r][0].normalized
    ]
    use_indent = bool(first_col_cells) and max((cell.indent for cell in first_col_cells), default=0) >= 2

    if data_start_col <= 1 and use_indent:
        stack: list[str] = []
        for r in range(data_start_row, len(grid)):
            row = grid[r]
            label_cell = row[0] if row else None
            label = label_cell.normalized if label_cell else ""
            if not label:
                continue
            depth = max(label_cell.indent // 2, 0)
            if depth > len(stack):
                depth = len(stack)
            stack = stack[:depth]
            stack.append(label)
            row_paths.append(stack.copy())
        return _dedupe_paths(row_paths)

    carry: list[str] = []
    for r in range(data_start_row, len(grid)):
        row = grid[r]
        path: list[str] = []
        for c in range(data_start_col):
            cell = row[c] if c < len(row) else None
            label = cell.normalized if cell else ""
            if label:
                if c < len(carry):
                    carry[c] = label
                    carry = carry[: c + 1]
                else:
                    carry.append(label)
                path.append(label)
            elif c < len(carry):
                path.append(carry[c])
        cleaned = [label for i, label in enumerate(path) if i == 0 or label != path[i - 1]]
        if cleaned:
            row_paths.append(cleaned)
    return _dedupe_paths(row_paths)


def _dedupe_paths(paths: list[list[str]]) -> list[list[str]]:
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def _unique_cells(row: list[HtmlCell | None]) -> list[HtmlCell]:
    unique: list[HtmlCell] = []
    seen: set[int] = set()
    for cell in row:
        if cell is None:
            continue
        ident = id(cell)
        if ident in seen:
            continue
        seen.add(ident)
        unique.append(cell)
    return unique
