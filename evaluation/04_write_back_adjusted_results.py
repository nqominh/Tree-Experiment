#!/usr/bin/env python3
"""
Write adjusted judge results back to an original CSV/XLSX file by matching IDs.

Fail-fast behavior:
- If any required column is missing, stop immediately.
- If duplicate IDs are found in either file, stop immediately.
- If any result ID is not found in the original file, stop immediately.
- No partial writes: data is validated first, then written once.

Usage:
  python 04_write_back_adjusted_results.py \
    --original score/C3_schema_only.xlsx \
    --result final_results.csv

Optional:
  --output score/C3_schema_only.updated.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write adjusted judge results to original file")
    parser.add_argument("--original", required=True, help="Original CSV/XLSX file path")
    parser.add_argument("--result", required=True, help="Result CSV/XLSX file path (from evaluation master)")
    parser.add_argument(
        "--output",
        default="",
        help="Output path. If omitted, writes to original file path (in-place).",
    )
    parser.add_argument("--original-id-col", default="id", help="ID column in original file")
    parser.add_argument("--result-id-col", default="item_id", help="ID column in result file")
    parser.add_argument("--result-final-col", default="final_label", help="Final label column in result file")
    parser.add_argument(
        "--result-source-col",
        default="adjudication_source",
        help="Adjudication source column in result file",
    )
    return parser.parse_args()


def load_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"ERROR: File not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=object)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        # Use first sheet by default.
        return pd.read_excel(path, dtype=object)

    raise SystemExit(f"ERROR: Unsupported file type: {path}")


def write_table(df: pd.DataFrame, path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df.to_csv(path, index=False, encoding="utf-8")
        return
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        df.to_excel(path, index=False)
        return

    raise SystemExit(f"ERROR: Unsupported output file type: {path}")


def to_id(value: Any) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if not s:
        return ""
    try:
        return str(int(float(s)))
    except (TypeError, ValueError):
        raise ValueError(f"Invalid ID value: {value!r}")


def final_label_to_em(value: str) -> str:
    label = (value or "").strip().upper()
    if label == "CORRECT":
        return "1"
    if label == "INCORRECT":
        return "0"
    return ""


def ensure_unique_ids(df: pd.DataFrame, id_col: str, side: str) -> pd.Series:
    if id_col not in df.columns:
        raise SystemExit(f"ERROR: Missing ID column '{id_col}' in {side} file")

    ids = df[id_col].apply(to_id)
    if (ids == "").any():
        bad_rows = ids[ids == ""].index.tolist()[:5]
        raise SystemExit(f"ERROR: Empty/invalid IDs found in {side} file at rows: {bad_rows}")

    dupes = ids[ids.duplicated()].unique().tolist()
    if dupes:
        raise SystemExit(f"ERROR: Duplicate IDs in {side} file: {dupes[:10]}")

    return ids


def main() -> None:
    args = parse_args()

    original_path = Path(args.original)
    result_path = Path(args.result)
    output_path = Path(args.output) if args.output else original_path

    original_df = load_table(original_path)
    result_df = load_table(result_path)

    required_result_cols = [args.result_id_col, args.result_final_col, args.result_source_col]
    missing_result = [c for c in required_result_cols if c not in result_df.columns]
    if missing_result:
        raise SystemExit(f"ERROR: Missing required result columns: {missing_result}")

    original_ids = ensure_unique_ids(original_df, args.original_id_col, "original")
    result_ids = ensure_unique_ids(result_df, args.result_id_col, "result")

    original_id_set = set(original_ids.tolist())
    result_id_set = set(result_ids.tolist())

    missing_in_original = sorted(result_id_set - original_id_set)
    if missing_in_original:
        raise SystemExit(
            "ERROR: Result IDs not found in original file. "
            f"Count={len(missing_in_original)}, sample={missing_in_original[:20]}"
        )

    # Build mapping from result by ID.
    result_df = result_df.copy()
    result_df["__rid"] = result_ids
    result_map = result_df.set_index("__rid")

    # Columns to write into original.
    copy_cols = [
        args.result_final_col,
        args.result_source_col,
    ]
    optional_judge_cols = ["Claude Sonnet 4.6", "GPT 5.4 Thinking", "Grok Expert"]
    for c in optional_judge_cols:
        if c in result_df.columns:
            copy_cols.append(c)

    out_df = original_df.copy()
    out_df["__oid"] = original_ids

    # Add destination columns if needed.
    dest_cols = {
        args.result_final_col: "judge_final_label",
        args.result_source_col: "judge_adjudication_source",
        "Claude Sonnet 4.6": "judge_claude_label",
        "GPT 5.4 Thinking": "judge_gpt_label",
        "Grok Expert": "judge_grok_label",
    }
    for src_col in copy_cols:
        dest_col = dest_cols[src_col]
        if dest_col not in out_df.columns:
            out_df[dest_col] = ""

    if "EM" not in out_df.columns:
        out_df["EM"] = ""

    # Populate matched rows.
    for idx, oid in out_df["__oid"].items():
        if oid in result_map.index:
            for src_col in copy_cols:
                out_df.at[idx, dest_cols[src_col]] = str(result_map.at[oid, src_col])
            out_df.at[idx, "EM"] = final_label_to_em(str(result_map.at[oid, args.result_final_col]))

    out_df = out_df.drop(columns=["__oid"])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write once after all validations and transformations.
    try:
        write_table(out_df, output_path)
    except Exception as exc:
        raise SystemExit(f"ERROR: Failed to write output file: {exc}") from exc

    print("=== WRITE-BACK SUMMARY ===")
    print(f"Original file: {original_path}")
    print(f"Result file:   {result_path}")
    print(f"Output file:   {output_path}")
    print(f"Rows in original: {len(original_df)}")
    print(f"Rows in result:   {len(result_df)}")
    print(f"Matched IDs applied: {len(result_id_set)}")
    print("Added/updated columns:")
    print("  - judge_final_label")
    print("  - judge_adjudication_source")
    if "Claude Sonnet 4.6" in copy_cols:
        print("  - judge_claude_label")
    if "GPT 5.4 Thinking" in copy_cols:
        print("  - judge_gpt_label")
    if "Grok Expert" in copy_cols:
        print("  - judge_grok_label")
    print("  - EM")


if __name__ == "__main__":
    main()
