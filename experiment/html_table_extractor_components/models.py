from __future__ import annotations

from dataclasses import dataclass, field

from .text_utils import leading_indent, normalize_text


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
        return normalize_text(self.text)

    @property
    def indent(self) -> int:
        return leading_indent(self.raw_text or self.text)


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
