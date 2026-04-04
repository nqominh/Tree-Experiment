"""Legacy JSON/value serializers for FeatureTree compatibility."""

from __future__ import annotations

from typing import Any

from utils.constants import DEFAULT_TABLE_NAME


def _serialize_index_tree(index_tree) -> list[dict[str, Any]]:
    def _serialize_node(node):
        payload: dict[str, Any] = {"label": str(node.value) if node.value is not None else None}
        if node.children:
            payload["children"] = [_serialize_node(c) for c in node.children]
        return payload

    if index_tree is None:
        return []
    return [_serialize_node(c) for c in index_tree.root.children]


def _get_leaf_paths(index_tree) -> list[list[str]]:
    if index_tree is None:
        return []

    paths: list[list[str]] = []

    def dfs(node, path: list[str]) -> None:
        if node is not index_tree.root and node.value is not None:
            label = str(node.value)
            if not path or path[-1] != label:
                path = path + [label]
        if not node.children:
            paths.append(path)
            return
        for child in node.children:
            dfs(child, path)

    dfs(index_tree.root, [])
    return paths


def tree_to_cells_json(tree) -> dict[str, Any]:
    if tree is None:
        return {}

    result = {
        "col_tree": _serialize_index_tree(tree.index_tree),
        "row_tree": _serialize_index_tree(tree.row_index_tree),
        "cells": [],
    }

    if tree.index_tree is None or tree.row_index_tree is None:
        return result

    col_paths = _get_leaf_paths(tree.index_tree)
    row_paths = _get_leaf_paths(tree.row_index_tree)

    for col_idx, col_leaf in enumerate(tree.index_tree.leaf_nodes):
        col_path = col_paths[col_idx] if col_idx < len(col_paths) else []
        for row_idx, body_node in enumerate(getattr(col_leaf, "body", [])):
            row_path = row_paths[row_idx] if row_idx < len(row_paths) else []
            val = getattr(body_node, "value", None)
            if val is not None and str(val).strip() not in ("", "None"):
                result["cells"].append(
                    {
                        "row_path": row_path,
                        "col_path": col_path,
                        "value": str(val),
                    }
                )

    return result


def tree_to_legacy_json(tree) -> dict[str, Any]:
    if tree is None or tree.index_tree is None:
        return {DEFAULT_TABLE_NAME: []}

    schema = tree.index_tree.get_flatten_schema()
    if not schema:
        return {DEFAULT_TABLE_NAME: []}

    max_rows = max((len(getattr(leaf, "body", [])) for leaf in tree.index_tree.leaf_nodes), default=0)
    if max_rows == 0:
        return {DEFAULT_TABLE_NAME: []}

    rows: list[dict[str, str]] = []
    for row_idx in range(max_rows):
        row_payload: dict[str, str] = {}
        for col_idx, leaf in enumerate(tree.index_tree.leaf_nodes):
            if row_idx >= len(getattr(leaf, "body", [])):
                continue
            val = leaf.body[row_idx].value
            if val is None or str(val).strip() in ("", "None"):
                continue
            if col_idx < len(schema):
                row_payload[schema[col_idx]] = str(val)
        if row_payload:
            rows.append(row_payload)

    return {DEFAULT_TABLE_NAME: rows}

