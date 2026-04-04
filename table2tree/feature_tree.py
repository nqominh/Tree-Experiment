"""
feature_tree.py - Schema-first tree structures for HO table extraction.

Active extraction now models only schema hierarchies (column and row headers)
using a single tree implementation. Value/body representations remain available
through legacy compatibility modules.
"""

from __future__ import annotations

import pickle
import re
from typing import Any

from loguru import logger

from utils.constants import DEFAULT_TABLE_NAME


def serial(level_list: list[int]) -> str:
    return ".".join(str(i) for i in level_list)


def _normalize_label(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _leading_indent(text: str | None) -> int:
    if text is None:
        return 0
    s = str(text).replace("\xa0", " ")
    return len(s) - len(s.lstrip(" "))


class TreeNode:
    def __init__(self, value: Any = None):
        self.value = value
        self.children: list[TreeNode] = []

    def add_child(self, child_node: "TreeNode") -> None:
        self.children.append(child_node)

    def remove_child(self, child_node: "TreeNode") -> None:
        if child_node in self.children:
            self.children.remove(child_node)


class SchemaNode(TreeNode):
    def __init__(self, value: Any = None):
        super().__init__(_normalize_label(value))
        self.father: SchemaNode | None = None
        # Compatibility-only storage used by legacy value/json helpers.
        self.body: list[Any] = []

    def add_body_node(self, node: Any) -> None:
        self.body.append(node)


class IndexNode(SchemaNode):
    """Backward-compatible alias for SchemaNode."""


def get_leaf_nodes(root: TreeNode | None) -> list[TreeNode]:
    if root is None:
        return []
    if not root.children:
        return [root]

    leaves: list[TreeNode] = []
    for child in root.children:
        leaves.extend(get_leaf_nodes(child))
    return leaves


class SchemaTree:
    def __init__(self):
        self.root = SchemaNode()
        self.leaf_nodes: list[SchemaNode] = []
        # Optional path list with one entry per source column/row.
        # When set, it preserves cardinality even if display tree deduplicates paths.
        self.explicit_paths: list[list[str]] | None = None

    def add_index(self, node: SchemaNode) -> None:
        node.father = self.root
        self.root.add_child(node)
        self.leaf_nodes.extend(get_leaf_nodes(node))

    def add_leaf_body_node_by_pos(self, body_node: Any, pos: int) -> None:
        """Compatibility hook used by legacy body-construction logic."""
        if 0 <= pos < len(self.leaf_nodes):
            self.leaf_nodes[pos].add_body_node(body_node)

    def value_list(self) -> list[str]:
        values: list[str] = []
        queue: list[SchemaNode] = list(self.root.children)
        while queue:
            curr = queue.pop(0)
            if curr.value is not None:
                values.append(str(curr.value))
            queue.extend(curr.children)
        return values

    def _iter_leaf_paths(self) -> list[list[str]]:
        paths: list[list[str]] = []

        def dfs(node: SchemaNode, path: list[str]) -> None:
            if node is not self.root and node.value:
                if not path or path[-1] != node.value:
                    path = path + [str(node.value)]

            if not node.children:
                if path:
                    paths.append(path)
                return

            for child in node.children:
                dfs(child, path)

        dfs(self.root, [])
        return paths

    def get_flatten_schema(self) -> list[str]:
        schema_list: list[str] = []
        seen: dict[str, int] = {}

        source_paths = self.explicit_paths if self.explicit_paths is not None else self._iter_leaf_paths()

        for path in source_paths:
            schema = "-".join(path)
            if schema in seen:
                seen[schema] += 1
                schema = f"{schema}#{seen[schema]}"
            else:
                seen[schema] = 1
            schema_list.append(schema)

        return schema_list

    def get_flatten_row_schema(self) -> list[str]:
        return self.get_flatten_schema()


class IndexTree(SchemaTree):
    """Backward-compatible alias for SchemaTree."""


# JSON serialization helpers

def _serialize_index_tree(index_tree: IndexTree | None) -> list[dict[str, Any]]:
    def _serialize_node(node: SchemaNode) -> dict[str, Any]:
        payload: dict[str, Any] = {"label": str(node.value) if node.value is not None else None}
        if node.children:
            payload["children"] = [_serialize_node(c) for c in node.children]
        return payload

    if index_tree is None:
        return []
    return [_serialize_node(c) for c in index_tree.root.children]


def _get_leaf_paths(index_tree: IndexTree | None) -> list[list[str]]:
    if index_tree is None:
        return []

    paths: list[list[str]] = []

    def dfs(node: SchemaNode, path: list[str]) -> None:
        if node is not index_tree.root and node.value is not None:
            if not path or path[-1] != str(node.value):
                path = path + [str(node.value)]
        if not node.children:
            paths.append(path)
            return
        for child in node.children:
            dfs(child, path)

    dfs(index_tree.root, [])
    return paths


class FeatureTree:
    def __init__(
        self,
        index_tree: IndexTree | None = None,
        body_tree: Any = None,
        row_index_tree: IndexTree | None = None,
    ):
        self.index_tree = index_tree if index_tree is not None else IndexTree()
        # body_tree is compatibility-only; active pipeline does not populate it.
        self.body_tree = body_tree
        self.row_index_tree = row_index_tree

    def load_from_pkl(self, pkl_file: str):
        try:
            with open(pkl_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            logger.exception("Failed to load FeatureTree from pickle: {}", pkl_file)
            return None

    def all_value_list(self) -> list[Any]:
        return self.index_value_list() + self.body_value_list()

    def get_list_value(self, pos: int) -> list[Any]:
        if self.index_tree is None:
            return []
        ncols = len(self.index_tree.leaf_nodes)
        if pos < 0 or pos >= ncols:
            return []
        return [b_node.value for b_node in self.index_tree.leaf_nodes[pos].body]

    def index_value_list(self) -> list[str]:
        if self.index_tree is None:
            return []
        return [x for x in self.index_tree.value_list() if x is not None and len(str(x)) > 0]

    def body_value_list(self) -> list[Any]:
        if self.body_tree is not None and hasattr(self.body_tree, "value_list"):
            vals = self.body_tree.value_list()
            return [x for x in vals if x is not None and len(str(x)) > 0]
        return []

    def get_max_row(self) -> int:
        if self.row_index_tree is not None and self.row_index_tree.leaf_nodes:
            return len(self.row_index_tree.leaf_nodes)

        if self.index_tree is None or not self.index_tree.leaf_nodes:
            return 0

        # Legacy compatibility: derive from leaf-attached body values if available.
        return max((len(leaf.body) for leaf in self.index_tree.leaf_nodes), default=0)

    def get_max_col(self) -> int:
        if self.index_tree is None:
            return 0
        return len(self.index_tree.leaf_nodes)

    def get_structured_table(self) -> list[Any]:
        schema = self.index_tree.get_flatten_schema() if self.index_tree else []
        return [schema]

    def __index__(self) -> dict[str, Any]:
        schema = self.index_tree.get_flatten_schema() if self.index_tree else []
        return {DEFAULT_TABLE_NAME: schema}

    def __json_legacy__(self) -> dict[str, Any]:
        from legacy.value_pipeline.json_compat import tree_to_legacy_json

        return tree_to_legacy_json(self)

    def __json__(self) -> dict[str, Any]:
        from legacy.value_pipeline.json_compat import tree_to_cells_json

        return tree_to_cells_json(self)

    def __str__(self, level_list: list[int] | None = None) -> str:
        if self.index_tree is None:
            return ""

        lines: list[str] = []

        def walk(node: SchemaNode, levels: list[int]) -> None:
            for i, child in enumerate(node.children, start=1):
                curr = levels + [i]
                label = child.value if child.value is not None else "(none)"
                lines.append(f"{serial(curr)} {label}:")
                walk(child, curr)

        walk(self.index_tree.root, [])
        return "\n".join(lines) + ("\n" if lines else "")


# ---------------------------------------------------------------------------
# Column tree construction
# ---------------------------------------------------------------------------

def _has_merge_info(sheet) -> bool:
    if sheet is None:
        return False
    return len(list(sheet.merged_cells.ranges)) > 0


def _is_title_row_in_schema(sheet, row: int, start_col: int, end_col: int) -> bool:
    values: list[str] = []
    for col in range(start_col, end_col + 1):
        val = _normalize_label(sheet.cell(row=row, column=col).value)
        if val:
            values.append(val)

    if not values:
        return True

    first = values[0]
    same = sum(1 for v in values if v == first)
    # A title row usually has one dominant value and low diversity.
    return same >= max(1, int(len(values) * 0.8)) and len(set(values)) <= 2


def _count_title_rows(sheet, max_rows: int = 3) -> int:
    if sheet is None:
        return 0

    nrows = sheet.max_row
    ncols = sheet.max_column
    count = 0
    for row in range(1, min(nrows, max_rows) + 1):
        if _is_title_row_in_schema(sheet, row, 1, ncols):
            count += 1
            continue
        break
    return count


def _forward_fill_row_labels(sheet, row: int, start_col: int, end_col: int) -> list[str | None]:
    labels: list[str | None] = []
    carry: str | None = None
    for col in range(start_col, end_col + 1):
        val = _normalize_label(sheet.cell(row=row, column=col).value)
        if val:
            carry = val
            labels.append(val)
        else:
            labels.append(carry)
    return labels


def _schema_tree_from_paths(paths: list[list[str]]) -> IndexTree:
    tree = IndexTree()
    cleaned_paths: list[list[str]] = []

    for path in paths:
        cleaned: list[str] = []
        for label in path:
            norm = _normalize_label(label)
            if not norm:
                continue
            if cleaned and cleaned[-1] == norm:
                continue
            cleaned.append(norm)

        if not cleaned:
            continue
        cleaned_paths.append(cleaned)

        node = tree.root
        for label in cleaned:
            found = None
            for child in node.children:
                if child.value == label:
                    found = child
                    break
            if found is None:
                found = IndexNode(label)
                found.father = node
                node.add_child(found)
            node = found

    tree.explicit_paths = cleaned_paths

    # Preserve source cardinality for schema matching.
    tree.leaf_nodes = [IndexNode(path[-1]) for path in cleaned_paths]
    return tree


def construct_index_tree(schema_sheet):
    """Merge-aware column index tree construction."""
    from utils.sheet_utils import get_merge_cell_size, get_sub_sheet, single_cell

    if schema_sheet is None:
        return IndexTree()

    nrows = schema_sheet.max_row
    ncols = schema_sheet.max_column
    index_tree = IndexTree()

    col = 1
    while col <= ncols:
        cell = schema_sheet.cell(row=1, column=col)
        x1, y1, x2, y2 = get_merge_cell_size(schema_sheet, cell.coordinate)
        label = _normalize_label(schema_sheet.cell(row=x1, column=y1).value)

        if not single_cell(schema_sheet, x1, y1, nrows, y2):
            sub_schema_sheet = get_sub_sheet(schema_sheet, x2 + 1, y1, nrows, y2)
            if sub_schema_sheet is not None and sub_schema_sheet.max_row > 0:
                sub_tree = construct_index_tree_smart(sub_schema_sheet)
                node = IndexNode(label)
                for child in sub_tree.root.children:
                    child.father = node
                    node.add_child(child)
            else:
                node = IndexNode(label)
        else:
            node = IndexNode(label)

        index_tree.add_index(node)
        col += y2 - y1 + 1

    return index_tree


def construct_index_tree_flattened(schema_sheet, start_row: int = 1, start_col: int = 1, end_col: int | None = None):
    """Value-based column tree construction for sheets without merge metadata."""
    if schema_sheet is None:
        return IndexTree()

    nrows = schema_sheet.max_row
    ncols = schema_sheet.max_column
    if end_col is None:
        end_col = ncols

    title_rows = _count_title_rows(schema_sheet)
    header_start = max(start_row, title_rows + 1)
    if header_start > nrows:
        header_start = 1

    filled_rows: list[list[str | None]] = []
    for row in range(header_start, nrows + 1):
        filled_rows.append(_forward_fill_row_labels(schema_sheet, row, start_col, end_col))

    paths: list[list[str]] = []
    width = end_col - start_col + 1
    for c in range(width):
        path: list[str] = []
        for r in range(len(filled_rows)):
            label = filled_rows[r][c]
            if not label:
                continue
            if path and path[-1] == label:
                continue
            path.append(label)
        if path:
            paths.append(path)

    if not paths:
        for col in range(start_col, end_col + 1):
            label = _normalize_label(schema_sheet.cell(row=nrows, column=col).value)
            if label:
                paths.append([label])

    return _schema_tree_from_paths(paths)


def construct_index_tree_smart(schema_sheet):
    if schema_sheet is None:
        return IndexTree()
    if _has_merge_info(schema_sheet):
        return construct_index_tree(schema_sheet)
    return construct_index_tree_flattened(schema_sheet)


# ---------------------------------------------------------------------------
# Row tree construction
# ---------------------------------------------------------------------------

def _has_row_merges(row_schema_sheet) -> bool:
    if row_schema_sheet is None:
        return False
    for merged_range in row_schema_sheet.merged_cells.ranges:
        min_col, min_row, max_col, max_row = merged_range.bounds
        if max_row > min_row:
            return True
    return False


def _construct_row_tree_from_merges(row_schema_sheet):
    from utils.sheet_utils import get_merge_cell_size, get_sub_sheet, single_cell

    nrows = row_schema_sheet.max_row
    ncols = row_schema_sheet.max_column

    index_tree = IndexTree()

    row = 1
    while row <= nrows:
        cell = row_schema_sheet.cell(row=row, column=1)
        x1, y1, x2, y2 = get_merge_cell_size(row_schema_sheet, cell.coordinate)
        label = _normalize_label(row_schema_sheet.cell(row=x1, column=y1).value)

        if not single_cell(row_schema_sheet, x1, y1, x2, ncols):
            sub_sheet = get_sub_sheet(row_schema_sheet, x1, y2 + 1, x2, ncols)
            if sub_sheet is not None and sub_sheet.max_column > 0:
                sub_tree = _construct_row_tree_from_merges(sub_sheet)
                node = IndexNode(label)
                for child in sub_tree.root.children:
                    child.father = node
                    node.add_child(child)
            else:
                node = IndexNode(label)
        else:
            node = IndexNode(label)

        index_tree.add_index(node)
        row = x2 + 1

    return index_tree


def _construct_row_tree_from_indentation(row_schema_sheet):
    nrows = row_schema_sheet.max_row

    entries: list[tuple[str, int]] = []
    for r in range(1, nrows + 1):
        raw = row_schema_sheet.cell(row=r, column=1).value
        if raw is None:
            continue
        label = _normalize_label(raw)
        if not label:
            continue
        depth = _leading_indent(str(raw))
        entries.append((label, depth))

    if not entries:
        return IndexTree()

    unique_depths = sorted({depth for _, depth in entries})
    depth_to_level = {depth: i for i, depth in enumerate(unique_depths)}

    tree = IndexTree()
    stack: list[IndexNode] = [tree.root]

    for label, depth in entries:
        level = depth_to_level[depth]
        parent_idx = min(level, len(stack) - 1)

        node = IndexNode(label)
        parent = stack[parent_idx]
        node.father = parent
        parent.add_child(node)

        stack = stack[: parent_idx + 1]
        stack.append(node)

    tree.leaf_nodes = [leaf for leaf in get_leaf_nodes(tree.root) if leaf is not tree.root]
    return tree


def _construct_row_tree_from_columns(row_schema_sheet):
    """Build row hierarchy by reading left-schema columns as path segments."""
    if row_schema_sheet is None:
        return IndexTree()

    nrows = row_schema_sheet.max_row
    ncols = row_schema_sheet.max_column
    paths: list[list[str]] = []

    for r in range(1, nrows + 1):
        path: list[str] = []
        for c in range(1, ncols + 1):
            label = _normalize_label(row_schema_sheet.cell(row=r, column=c).value)
            if not label:
                continue
            if path and path[-1] == label:
                continue
            path.append(label)
        if path:
            paths.append(path)

    return _schema_tree_from_paths(paths)


def construct_row_index_tree(row_schema_sheet):
    if row_schema_sheet is None:
        return IndexTree()

    if _has_row_merges(row_schema_sheet):
        return _construct_row_tree_from_merges(row_schema_sheet)

    if row_schema_sheet.max_column > 1:
        tree = _construct_row_tree_from_columns(row_schema_sheet)
        if tree.leaf_nodes:
            return tree

    return _construct_row_tree_from_indentation(row_schema_sheet)


# ---------------------------------------------------------------------------
# Sheet -> FeatureTree
# ---------------------------------------------------------------------------

def construct_sheet(sheet):
    from utils.split_utils import split_schema_column, split_schema_row

    schema_sheet, data_sheet = split_schema_row(sheet)

    index_tree = construct_index_tree_smart(schema_sheet)

    row_index_tree = None
    if data_sheet is not None:
        row_schema_sheet, _ = split_schema_column(data_sheet)
        row_index_tree = construct_row_index_tree(row_schema_sheet)

    return FeatureTree(index_tree=index_tree, row_index_tree=row_index_tree)


def construct_feature_tree(tree_dict):
    """Compatibility helper for structured fallback inputs."""
    logger.info("construct_feature_tree() Start to Process")

    if not tree_dict:
        return FeatureTree()

    # Common case: {DEFAULT_TABLE_NAME: <sheet>}
    if len(tree_dict) == 1:
        value = next(iter(tree_dict.values()))
        if hasattr(value, "cell") and hasattr(value, "max_row"):
            return construct_sheet(value)

    index_tree = IndexTree()
    for key in tree_dict.keys():
        index_tree.add_index(IndexNode(_normalize_label(key)))

    return FeatureTree(index_tree=index_tree)


# ---------------------------------------------------------------------------
# Legacy value/body compatibility exports
# ---------------------------------------------------------------------------

from legacy.value_pipeline.body_tree import (  # noqa: E402
    BodyNode,
    BodyTree,
    construct_body_tree,
    construct_body_tree_dfs,
)

__all__ = [
    "TreeNode",
    "SchemaNode",
    "SchemaTree",
    "IndexNode",
    "IndexTree",
    "BodyNode",
    "BodyTree",
    "FeatureTree",
    "construct_index_tree",
    "construct_index_tree_flattened",
    "construct_index_tree_smart",
    "construct_row_index_tree",
    "construct_body_tree",
    "construct_body_tree_dfs",
    "construct_sheet",
    "construct_feature_tree",
]

