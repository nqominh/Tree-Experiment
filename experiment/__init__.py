# HO-Tree Experiment Package
#
# Clean modular API for HTML table → HO-Tree construction and evaluation.
#
# Modules:
#   tree_builder     — html_to_tree() with 3-strategy fallback
#   tree_output      — FeatureTree → JSON / schema / hierarchical string
#   prompt_templates — LLM prompt templates (baseline, schema, json, hierarchical)
#   data_loader      — Dataset discovery (HTML tables, QA data)
#   batch_runner     — Batch tree building CLI
#   debug_single     — Interactive single-table debugger

from experiment.tree_builder import (
    html_to_tree,
    html_to_tree_direct,
    html_to_tree_fixed,
    html_to_tree_structured,
)
from experiment.tree_output import (
    tree_to_hierarchical_string,
    tree_to_schema,
    tree_to_json,
)
from experiment.prompt_templates import (
    build_baseline_prompt,
    build_hotree_prompt_schema,
    build_hotree_prompt_json,
    build_hotree_prompt_hierarchical,
    TEMPLATE_MAP,
)
from experiment.data_loader import (
    discover_html_tables,
    discover_qa_data,
    get_field,
)
