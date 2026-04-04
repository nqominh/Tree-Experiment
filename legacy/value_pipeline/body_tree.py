"""Legacy body-tree implementation preserved for compatibility."""

from __future__ import annotations

from typing import Any


class BodyNode:
    def __init__(self, value: Any = None):
        self.value = value
        self.children: list[BodyNode] = []
        self.father: list[BodyNode] = []
        self.x1: int | None = None
        self.y1: int | None = None
        self.x2: int | None = None
        self.y2: int | None = None

    def get_pos(self) -> list[int | None]:
        return [self.x1, self.y1, self.x2, self.y2]

    def add_child(self, child_node: "BodyNode") -> None:
        self.children.append(child_node)

    def add_father(self, node: "BodyNode") -> None:
        self.father.append(node)


class BodyTree:
    def __init__(self):
        self.root = BodyNode()

    def add_deep(self, node: BodyNode) -> None:
        curr = self.root
        while curr.children:
            curr = curr.children[0]
        curr.add_child(node)
        node.add_father(curr)

    def value_list(self) -> list[Any]:
        values: list[Any] = []
        queue: list[BodyNode] = list(self.root.children)
        while queue:
            curr = queue.pop(0)
            if curr.value not in values:
                values.append(curr.value)
            queue.extend(curr.children)
        return values


def construct_body_tree_dfs(index_tree, data_sheet, x, y, depth):
    from utils.sheet_utils import get_merge_cell_size, get_merge_cell_value

    cell = data_sheet.cell(row=x, column=y)
    x1, y1, x2, y2 = get_merge_cell_size(data_sheet, cell.coordinate)

    value = get_merge_cell_value(data_sheet, cell.coordinate)
    root = BodyNode(value)
    root.x1 = x1
    root.x2 = x2
    root.y1 = y1
    root.y2 = y2
    index_tree.add_leaf_body_node_by_pos(root, depth)

    if y2 >= data_sheet.max_column:
        return root

    row = x1
    while row <= x2:
        cell = data_sheet.cell(row=row, column=y2 + 1)
        xx1, yy1, xx2, yy2 = get_merge_cell_size(data_sheet, cell.coordinate)

        if xx1 < x1:
            if depth + 1 < len(index_tree.leaf_nodes) and index_tree.leaf_nodes[depth + 1].body:
                child = index_tree.leaf_nodes[depth + 1].body[-1]
                if child is not None:
                    root.add_child(child)
                    child.add_father(root)
        else:
            body_node = construct_body_tree_dfs(index_tree, data_sheet, xx1, yy1, depth + 1)
            body_node.add_father(root)
            root.add_child(body_node)

        row += xx2 - xx1 + 1

    return root


def construct_body_tree(index_tree, data_sheet):
    """Build a legacy BodyTree from the data sheet and link it to index leaves."""
    from utils.sheet_utils import get_merge_cell_size

    if data_sheet is None:
        return None, None

    nrows = data_sheet.max_row

    body_tree = BodyTree()
    root = body_tree.root

    row = 1
    while row <= nrows:
        cell = data_sheet.cell(row=row, column=1)
        x1, y1, x2, y2 = get_merge_cell_size(data_sheet, cell.coordinate)

        body_node = construct_body_tree_dfs(index_tree, data_sheet, x1, y1, 0)
        body_node.add_father(root)
        root.add_child(body_node)

        row += x2 - x1 + 1

    return body_tree, index_tree

