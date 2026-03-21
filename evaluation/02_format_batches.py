#!/usr/bin/env python3
"""
Script 2: Format evaluation_master.csv into chat-ready batch CSV files.

Usage:
    python 02_format_batches.py --input evaluation_master.csv --batch-size 55 --output-dir batches/
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

MASTER_REQUIRED_COLUMNS = [
    "item_id",
    "question",
    "gold_answer",
    "model_answer",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create judge prompt batch files")
    parser.add_argument("--input", default="evaluation_master.csv", help="Input master CSV")
    parser.add_argument("--batch-size", type=int, default=55, help="Items per batch (default: 55)")
    parser.add_argument("--output-dir", default="batches", help="Output directory for batch txt files")
    return parser.parse_args()


def to_int_id(value: object) -> int:
    return int(float(str(value).strip()))


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_judge_prompt_markdown() -> str:
    return (
        "# LLM Judge Prompt\n\n"
        "You are grading free-form numerical reasoning answers.\n\n"
        "For each item independently, read `question`, `gold_answer`, and `model_answer` from the batch CSV.\n"
        "Write your decision in the `judgement` column using one label per row:\n"
        "- CORRECT\n"
        "- INCORRECT\n"
        "- UNCERTAIN\n\n"
        "## Rules\n"
        "1. Judge each item independently; do not let one item influence another.\n"
        "2. CORRECT if mathematically equivalent: 62.6 = 62.60 = 62.6%.\n"
        "3. CORRECT if same value, different format: 1,000 = 1000, $7.50 = 7.5.\n"
        "4. CORRECT if rounded to 2 decimal places and matches gold.\n"
        "   For 2-decimal checks, treat absolute difference < 0.005 as equivalent after rounding.\n"
        "5. CORRECT if answer contains the right value even with extra explanation.\n"
        "6. INCORRECT if the number is wrong.\n"
        "7. INCORRECT if partial answer when full answer is required.\n"
        "8. UNCERTAIN only if correctness genuinely cannot be determined from the gold answer.\n\n"
        "## How To Use\n"
        "1. Open one `batch_XX_items.csv` file.\n"
        "2. Paste this prompt into the LLM and provide the CSV content.\n"
        "3. Ask the LLM to return the same CSV with `judgement` filled.\n"
        "4. Save the LLM output CSV to your judge output folder.\n"
    )


def build_batch_items_df(rows: list[dict[str, object]]) -> pd.DataFrame:
    batch_rows: list[dict[str, object]] = []
    for row in rows:
        batch_rows.append(
            {
                "item_id": to_int_id(row["item_id"]),
                "question": clean_text(row.get("question", "")),
                "gold_answer": clean_text(row.get("gold_answer", "")),
                "model_answer": clean_text(row.get("model_answer", "")),
                "judgement": "",
            }
        )

    return pd.DataFrame(
        batch_rows,
        columns=["item_id", "question", "gold_answer", "model_answer", "judgement"],
    )


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("ERROR: --batch-size must be > 0")

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise SystemExit(f"ERROR: Input file not found: {input_path}")

    df = pd.read_csv(input_path, dtype=object)

    missing = [c for c in MASTER_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"ERROR: Missing required columns in {input_path}: {missing}")

    if "batch_id" not in df.columns:
        df["batch_id"] = ""

    if df.empty:
        # Still write an empty index for consistency.
        index_path = output_dir / "batch_index.csv"
        pd.DataFrame(columns=["item_id", "batch_id"]).to_csv(index_path, index=False)
        df.to_csv(input_path, index=False)
        print("=== BATCH SUMMARY ===")
        print("Total items:     0")
        print("Batches created: 0  (batch size: {})".format(args.batch_size))
        print(f"Output dir: {output_dir}")
        return

    # Stable numeric sort by item_id.
    df = df.copy()
    df["_item_sort"] = df["item_id"].apply(to_int_id)
    df = df.sort_values(by=["_item_sort", "item_id"], kind="stable").drop(columns=["_item_sort"])

    records = df.to_dict(orient="records")
    total_items = len(records)
    total_batches = math.ceil(total_items / args.batch_size)

    batch_index_rows: list[dict[str, object]] = []

    prompt_md_path = output_dir / "judge_prompt.md"
    prompt_md_path.write_text(build_judge_prompt_markdown(), encoding="utf-8")

    for i in range(total_batches):
        start = i * args.batch_size
        end = min(start + args.batch_size, total_items)
        chunk = records[start:end]

        batch_num = i + 1
        batch_id = f"batch_{batch_num:02d}"
        csv_path = output_dir / f"{batch_id}_items.csv"

        batch_items_df = build_batch_items_df(chunk)
        batch_items_df.to_csv(csv_path, index=False, encoding="utf-8")

        item_ids = [to_int_id(r["item_id"]) for r in chunk]
        df.loc[df["item_id"].apply(to_int_id).isin(item_ids), "batch_id"] = batch_id

        for item_id in item_ids:
            batch_index_rows.append({"item_id": item_id, "batch_id": batch_id})

    # Save updated master with batch_id.
    df.to_csv(input_path, index=False, encoding="utf-8")

    # Save batch index mapping.
    index_df = pd.DataFrame(batch_index_rows, columns=["item_id", "batch_id"])
    index_path = output_dir / "batch_index.csv"
    index_df.to_csv(index_path, index=False, encoding="utf-8")

    print("=== BATCH SUMMARY ===")
    print(f"Total items:      {total_items}")
    print(f"Batches created:  {total_batches}  (batch size: {args.batch_size})")
    print(f"Output dir: {output_dir}/")
    print(f"Judge prompt: {prompt_md_path}")
    print()
    print("Next steps:")
    print("  Judge 1 (Claude):")
    print("    1. Open batches/judge_prompt.md")
    print("    2. Open batches/batch_01_items.csv")
    print("    3. Paste prompt + CSV into a NEW conversation at claude.ai")
    print("    4. Save output CSV as: judge_outputs/claude/batch_01_items.csv")
    print("    5. Repeat for remaining batch files in a NEW conversation")
    print()
    print("  Judge 2 (ChatGPT):")
    print("    1. Open batches/judge_prompt.md")
    print("    2. Open batches/batch_01_items.csv")
    print("    3. Paste prompt + CSV into a NEW conversation at chatgpt.com")
    print("    4. Save output CSV as: judge_outputs/gpt/batch_01_items.csv")
    print("    5. Repeat for remaining batch files in a NEW conversation")
    print()
    print("  Then run: python 03_parse_outputs.py")


if __name__ == "__main__":
    main()
