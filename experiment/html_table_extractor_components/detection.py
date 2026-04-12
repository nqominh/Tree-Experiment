from .models import HtmlCell
from .parsing import unique_cells
from .text_utils import is_numeric_like


def detect_title(grid: list[list[HtmlCell | None]]) -> tuple[str, int]:
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


def detect_header_rows(grid: list[list[HtmlCell | None]], title_rows: int) -> int:
    header_rows = 0
    max_scan = min(len(grid), title_rows + 6)
    for ridx in range(title_rows, max_scan):
        row = grid[ridx]
        unique = unique_cells(row)
        nonempty = [cell for cell in unique if cell.normalized]
        if not nonempty:
            header_rows += 1
            continue

        numeric = sum(1 for cell in nonempty if is_numeric_like(cell.text))
        has_span = any(cell.rowspan > 1 or cell.colspan > 1 for cell in nonempty)
        mostly_text = numeric <= max(1, len(nonempty) // 3)
        if has_span or all(cell.is_header for cell in nonempty) or mostly_text:
            header_rows += 1
            continue
        break

    if header_rows == 0 and len(grid) > title_rows:
        first = unique_cells(grid[title_rows])
        if any(cell.is_header for cell in first):
            header_rows = 1
    return header_rows


def detect_left_header_cols(grid: list[list[HtmlCell | None]], header_rows: int) -> int:
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
        textish = sum(1 for cell in column_cells if not is_numeric_like(cell.text))
        following_numeric = sum(1 for cell in data_cells if is_numeric_like(cell.text))
        if textish >= max(1, len(column_cells) // 2) and following_numeric >= max(2, len(data_cells) // 4):
            best = c + 1
            continue
        if c == 0 and following_numeric > len(column_cells):
            best = 1
        break
    return best


def looks_like_metric_table(
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
            if is_numeric_like(right_text) or any(ch.isdigit() for ch in right_text):
                numeric_or_formula_like += 1
    return value_rows >= 3 and numeric_or_formula_like >= max(2, value_rows // 2)
