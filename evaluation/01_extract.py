#!/usr/bin/env python3
"""
Script 1: Extract EM==0 rows from one or more XLSX files into a master CSV.

Usage:
  python 01_extract.py --input results/*.xlsx --output evaluation_master.csv
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = ["id", "question", "correct_answer", "model_answer", "EM"]
MASTER_COLUMNS = [
    "item_id",
    "sheet_name",
    "source_file",
    "question",
    "gold_answer",
    "model_answer",
    "batch_id",
    "judge1_label",
    "judge2_label",
    "final_label",
    "adjudication_source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract EM==0 rows from XLSX files")
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more xlsx paths or glob patterns (e.g. results/*.xlsx)",
    )
    parser.add_argument(
        "--output",
        default="evaluation_master.csv",
        help="Output master CSV path (default: evaluation_master.csv)",
    )
    return parser.parse_args()


def expand_input_paths(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for p in patterns:
        matches = sorted(glob.glob(p))
        if matches:
            paths.extend(Path(m) for m in matches)
        else:
            # If no glob matches, keep as literal path if exists.
            literal = Path(p)
            if literal.exists():
                paths.append(literal)
    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            unique.append(rp)
    return unique


def is_em_falsy(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value is False
    if isinstance(value, (int, float)):
        return float(value) == 0.0

    s = str(value).strip().lower()
    return s in {"0", "0.0", "false", "f", "no", "n"}


def safe_int_id(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def safe_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def main() -> None:
    args = parse_args()
    input_paths = expand_input_paths(args.input)

    if not input_paths:
        raise SystemExit("ERROR: No input xlsx files found. Check --input path/glob.")

    files_processed = 0
    sheets_processed = 0
    sheets_skipped = 0
    em_one_rows_skipped = 0
    em_zero_rows_extracted = 0
    duplicates_removed = 0

    extracted_rows: list[dict[str, object]] = []
    seen_item_ids: set[int] = set()

    for xlsx_path in input_paths:
        if xlsx_path.suffix.lower() not in {".xlsx", ".xlsm", ".xls"}:
            print(f"WARN: Skipping non-excel file: {xlsx_path}")
            continue

        files_processed += 1
        print(f"[FILE] {xlsx_path}")

        try:
            excel = pd.ExcelFile(xlsx_path)
        except Exception as e:  # pragma: no cover - defensive
            print(f"WARN: Failed to read workbook {xlsx_path}: {e}")
            continue

        for sheet_name in excel.sheet_names:
            sheets_processed += 1
            print(f"  [SHEET] {sheet_name}")

            try:
                df = pd.read_excel(xlsx_path, sheet_name=sheet_name, dtype=object)
            except Exception as e:
                print(f"    WARN: Failed to read sheet '{sheet_name}': {e}")
                sheets_skipped += 1
                continue

            missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
            if missing_cols:
                print(
                    f"    WARN: Missing columns {missing_cols}. "
                    f"Available: {list(df.columns)}. Skipping sheet."
                )
                sheets_skipped += 1
                continue

            if len(df) <= 1:
                print(f"    WARN: Sheet has {len(df)} data row(s). Skipping.")
                sheets_skipped += 1
                continue

            for _, row in df.iterrows():
                item_id = safe_int_id(row.get("id"))
                if item_id is None:
                    print("    WARN: Invalid id encountered; skipping row.")
                    continue

                em_value = row.get("EM")
                if not is_em_falsy(em_value):
                    em_one_rows_skipped += 1
                    continue

                if item_id in seen_item_ids:
                    duplicates_removed += 1
                    print(f"    WARN: Duplicate item_id {item_id}; keeping first occurrence.")
                    continue

                seen_item_ids.add(item_id)
                em_zero_rows_extracted += 1
                extracted_rows.append(
                    {
                        "item_id": item_id,
                        "sheet_name": sheet_name,
                        "source_file": xlsx_path.name,
                        "question": safe_text(row.get("question")),
                        "gold_answer": safe_text(row.get("correct_answer")),
                        "model_answer": safe_text(row.get("model_answer")),
                        "batch_id": "",
                        "judge1_label": "",
                        "judge2_label": "",
                        "final_label": "",
                        "adjudication_source": "",
                    }
                )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_df = pd.DataFrame(extracted_rows, columns=MASTER_COLUMNS)
    out_df.to_csv(out_path, index=False, encoding="utf-8")

    print("\n=== EXTRACTION SUMMARY ===")
    print(f"Files processed:      {files_processed}")
    print(f"Sheets processed:     {sheets_processed}")
    print(f"Sheets skipped:       {sheets_skipped}  (missing columns/read issues/too few rows)")
    print(f"EM==1 rows skipped:   {em_one_rows_skipped}")
    print(f"EM==0 rows extracted: {em_zero_rows_extracted}")
    print(f"Duplicates removed:   {duplicates_removed}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
