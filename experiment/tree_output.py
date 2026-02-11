"""
tree_output.py — FeatureTree Output Converters

Convert a built FeatureTree into various output formats:
  - Numbered hierarchical string (native HO-Tree display)
  - Flattened column schema list
  - Nested JSON dict

Usage:
    from experiment.tree_output import tree_to_json, tree_to_schema, tree_to_hierarchical_string
"""

from table2tree.feature_tree import FeatureTree


def tree_to_hierarchical_string(tree: FeatureTree) -> str:
    """
    Numbered hierarchical string:
        1 Year: 2020, 2021, 2022,
        2 Sales:
        2.1 Q1: 100, 120, 140,
        2.2 Q2: 150, 170, 190,
    """
    if tree is None:
        return ""
    try:
        return tree.__str__([1])
    except Exception:
        return ""


def tree_to_schema(tree: FeatureTree) -> list:
    """Flattened column paths, e.g. ['Year', 'Sales-Q1', 'Sales-Q2']."""
    if tree is None:
        return []
    try:
        return tree.index_tree.get_flatten_schema()
    except Exception:
        return []


def tree_to_json(tree: FeatureTree) -> dict:
    """Nested JSON dict representation."""
    if tree is None:
        return {}
    try:
        return tree.__json__()
    except Exception:
        return {}
