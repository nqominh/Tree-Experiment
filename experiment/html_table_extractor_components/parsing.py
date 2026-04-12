from bs4 import BeautifulSoup

from .models import HtmlCell


def parse_html_table(html: str) -> list[list[HtmlCell | None]]:
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


def unique_cells(row: list[HtmlCell | None]) -> list[HtmlCell]:
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
