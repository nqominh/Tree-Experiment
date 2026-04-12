from .models import HtmlCell


def build_column_paths(
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


def build_row_paths(
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
        return dedupe_paths(row_paths)

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
    return dedupe_paths(row_paths)


def dedupe_paths(paths: list[list[str]]) -> list[list[str]]:
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for path in paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped
