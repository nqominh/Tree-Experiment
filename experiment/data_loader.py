"""
data_loader.py — Dataset Discovery & Loading Utilities

Helpers for locating HTML tables and QA data in the RealHiTBench dataset.

Usage:
    from experiment.data_loader import discover_html_tables, discover_qa_data
"""

import json
import os


def discover_html_tables(root_dir: str, limit: int = None) -> dict[str, str]:
    """
    Walk `root_dir` and return {table_id: html_content}.

    Args:
        root_dir: Root directory to search (e.g. "RealHiTBench").
        limit:    Max number of tables to load (None = all).
    """
    table_map: dict[str, str] = {}
    count = 0
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in sorted(filenames):
            if fname.endswith(".html"):
                if limit and count >= limit:
                    return table_map
                table_id = fname.replace(".html", "")
                fpath = os.path.join(dirpath, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    table_map[table_id] = f.read()
                count += 1
    return table_map


def discover_qa_data(root_dir: str) -> list[dict]:
    """
    Walk `root_dir` and load all .json / .jsonl QA files.

    Handles both flat JSON arrays and the RealHiTBench format
    with a top-level "queries" key.
    """
    qa: list[dict] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            if fname.endswith(".jsonl"):
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            qa.append(json.loads(line))
            elif fname.endswith(".json"):
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        qa.extend(data)
                    elif isinstance(data, dict):
                        # Handle RealHiTBench {"queries": [...]} format
                        if "queries" in data:
                            qa.extend(data["queries"])
                        else:
                            qa.append(data)
    return qa


def get_field(item: dict, candidates: list[str], default=""):
    """
    Get the first matching field from a dict, trying multiple key names.

    Useful because different QA datasets use different key names
    for the same concept (e.g. "question" vs "Question" vs "q").
    """
    for c in candidates:
        if c in item:
            return item[c]
    return default
