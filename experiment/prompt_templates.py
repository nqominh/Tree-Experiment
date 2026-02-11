"""
prompt_templates.py — LLM Prompt Templates for HO-Tree Table QA

Four templates for different levels of structural context:
  - baseline        : HTML + question (no structure)
  - schema   (A)    : Column paths with parent-child notes
  - json     (B)    : Nested dict structure
  - hierarchical (C): Numbered tree with data values (native HO-Tree)

Usage:
    from experiment.prompt_templates import TEMPLATE_MAP, build_baseline_prompt
"""

import json


# ---------------------------------------------------------------------------
# Baseline (HTML only)
# ---------------------------------------------------------------------------

def build_baseline_prompt(html: str, question: str) -> str:
    """Baseline: raw HTML table + question, no structural hints."""
    parts = [
        "You are an expert in analyzing tables. "
        "Answer the question based on the table below.",
        "",
        "# Table (HTML)",
        "```html",
        html[:5000],
        "```",
        "",
        "# Question",
        question,
        "",
        "Think step by step, then provide:",
        "[Final Answer]: your_answer",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template A — Schema Context
# ---------------------------------------------------------------------------

def build_hotree_prompt_schema(
    html: str,
    question: str,
    schema: list | None = None,
) -> str:
    """
    Template A: column paths + parent-child relationship notes.

    Args:
        schema: list of flattened column paths from tree_to_schema().
    """
    parts = [
        "You are an expert in analyzing hierarchical tables.",
        "",
        "# Table Structure",
    ]
    if schema:
        parts.append(f"Columns: {', '.join(schema)}")
        # Detect parent-child from hyphenated paths
        parents: dict[str, list[str]] = {}
        for s in schema:
            if "-" in s:
                parent, child = s.rsplit("-", 1)
                parents.setdefault(parent, []).append(child)
        for parent, children in parents.items():
            parts.append(
                f'Note: {", ".join(children)} are sub-columns under parent "{parent}"'
            )
    parts.extend(
        [
            "",
            "# Table (HTML)",
            "```html",
            html[:4500],
            "```",
            "",
            "# Question",
            question,
            "",
            "Think step by step:",
            "1. Identify relevant columns using the structure above.",
            "2. Locate the correct data cells.",
            "3. Perform any calculations.",
            "",
            "[Final Answer]: your_answer",
        ]
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template B — JSON Structure
# ---------------------------------------------------------------------------

def build_hotree_prompt_json(
    html: str,
    question: str,
    tree_json: dict | None = None,
) -> str:
    """
    Template B: nested JSON dict of the tree.

    Args:
        tree_json: dict from tree_to_json().
    """
    json_str = json.dumps(tree_json or {}, indent=2, ensure_ascii=False)[:2500]
    parts = [
        "You are an expert in analyzing hierarchical tables.",
        "",
        "# Table Structure (JSON)",
        "```json",
        json_str,
        "```",
        "",
        "# Table (HTML)",
        "```html",
        html[:3500],
        "```",
        "",
        "# Question",
        question,
        "",
        "Think step by step, then provide:",
        "[Final Answer]: your_answer",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Template C — Hierarchical / Path-Based (native HO-Tree)
# ---------------------------------------------------------------------------

def build_hotree_prompt_hierarchical(
    html: str,
    question: str,
    tree_string: str | None = None,
) -> str:
    """
    Template C: numbered tree string with data values.

    Args:
        tree_string: str from tree_to_hierarchical_string().
    """
    parts = [
        "You are an expert in analyzing hierarchical tables.",
        "",
        "# Instructions",
        "1. Study the table structure below "
        "(hierarchical format with parent-child relationships)",
        "2. Each numbered entry shows: header → data values",
        "3. Indented sub-entries (e.g. 2.1, 2.2) are children of the parent (2)",
        "",
    ]
    if tree_string:
        parts.extend(
            [
                "# Table Structure (HO-Tree)",
                "```",
                tree_string[:3000],
                "```",
                "",
            ]
        )
    parts.extend(
        [
            "# Table (HTML)",
            "```html",
            html[:3500],
            "```",
            "",
            "# Question",
            question,
            "",
            "Think step by step:",
            "1. Identify relevant hierarchy path using the tree structure.",
            "2. Locate the specific values in the table.",
            "3. Perform any required calculations.",
            "",
            "[Final Answer]: your_answer",
        ]
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TEMPLATE_MAP = {
    "baseline": build_baseline_prompt,
    "schema": build_hotree_prompt_schema,
    "json": build_hotree_prompt_json,
    "hierarchical": build_hotree_prompt_hierarchical,
}
