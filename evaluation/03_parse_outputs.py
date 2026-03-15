#!/usr/bin/env python3
"""
Script 3: Aggregate labels from three judges into final labels.

Usage:
  python 03_parse_outputs.py \
    --master evaluation_master.csv \
    --output final_results.csv
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

VALID_LABELS = {"CORRECT", "INCORRECT", "UNCERTAIN"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate three-judge votes")
    parser.add_argument("--master", default="evaluation_master.csv", help="Master CSV path")
    parser.add_argument("--output", default="final_results.csv", help="Output CSV path")
    parser.add_argument(
        "--human-review-output",
        default="human_review_list.csv",
        help="Output CSV path for HUMAN_REVIEW rows",
    )
    parser.add_argument(
        "--summary-output",
        default="summary_report.txt",
        help="Text summary output path",
    )
    parser.add_argument(
        "--judge-columns",
        default="Claude Sonnet 4.6,GPT 5.4 Thinking,Grok Expert",
        help="Comma-separated judge column names in master CSV",
    )
    return parser.parse_args()


def normalize_label(value: object) -> str:
    if pd.isna(value):
        return ""
    cleaned = str(value).strip().upper()
    if cleaned in VALID_LABELS:
        return cleaned
    return ""


def aggregate_row(labels: list[str]) -> tuple[str, str]:
    usable = [x for x in labels if x in VALID_LABELS]
    if len(usable) < 2:
        return "HUMAN_REVIEW", "human_review"

    # Majority vote among CORRECT / INCORRECT only.
    # UNCERTAIN votes do not contribute to automatic pass/fail decision.
    binary_votes = [x for x in usable if x in {"CORRECT", "INCORRECT"}]
    counts = Counter(binary_votes)

    if counts["CORRECT"] >= 2:
        return "CORRECT", "majority_vote"
    if counts["INCORRECT"] >= 2:
        return "INCORRECT", "majority_vote"

    return "HUMAN_REVIEW", "human_review"


def main() -> None:
    args = parse_args()

    master_path = Path(args.master)
    output_path = Path(args.output)
    human_path = Path(args.human_review_output)
    summary_path = Path(args.summary_output)

    if not master_path.exists():
        raise SystemExit(f"ERROR: Master file not found: {master_path}")

    judge_cols = [c.strip() for c in args.judge_columns.split(",") if c.strip()]
    if len(judge_cols) != 3:
        raise SystemExit("ERROR: --judge-columns must provide exactly 3 columns.")

    df = pd.read_csv(master_path, dtype=object)

    missing = [c for c in judge_cols if c not in df.columns]
    if missing:
        raise SystemExit(f"ERROR: Missing judge columns in master CSV: {missing}")

    if "final_label" not in df.columns:
        df["final_label"] = ""
    if "adjudication_source" not in df.columns:
        df["adjudication_source"] = ""

    parsed_counts = {col: 0 for col in judge_cols}
    missing_counts = {col: 0 for col in judge_cols}

    for col in judge_cols:
        normalized = df[col].apply(normalize_label)
        parsed_counts[col] = int((normalized != "").sum())
        missing_counts[col] = int((normalized == "").sum())
        df[col] = normalized

    final_labels: list[str] = []
    sources: list[str] = []

    both_correct = 0
    both_incorrect = 0
    human_review = 0

    for _, row in df.iterrows():
        labels = [row.get(c, "") for c in judge_cols]
        final_label, source = aggregate_row(labels)
        final_labels.append(final_label)
        sources.append(source)

        if final_label == "CORRECT":
            both_correct += 1
        elif final_label == "INCORRECT":
            both_incorrect += 1
        else:
            human_review += 1

    df["final_label"] = final_labels
    df["adjudication_source"] = sources

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")

    # Write back to master as requested. If locked, write a fallback file.
    master_write_path = master_path
    master_write_note = ""
    try:
        df.to_csv(master_path, index=False, encoding="utf-8")
    except PermissionError:
        master_write_path = master_path.with_name(f"{master_path.stem}.updated{master_path.suffix}")
        df.to_csv(master_write_path, index=False, encoding="utf-8")
        master_write_note = " (master was locked; wrote fallback copy)"

    human_df = df[df["final_label"] == "HUMAN_REVIEW"].copy()
    wanted_cols = [
        "item_id",
        "question",
        "gold_answer",
        "model_answer",
        *judge_cols,
    ]
    existing_cols = [c for c in wanted_cols if c in human_df.columns]
    human_df = human_df[existing_cols].sort_values(by=["item_id"], kind="stable")
    human_df.to_csv(human_path, index=False, encoding="utf-8")

    total = len(df)
    correct_count = int((df["final_label"] == "CORRECT").sum())
    incorrect_count = int((df["final_label"] == "INCORRECT").sum())
    review_count = int((df["final_label"] == "HUMAN_REVIEW").sum())

    correct_pct = (correct_count / total * 100) if total else 0.0
    incorrect_pct = (incorrect_count / total * 100) if total else 0.0
    review_pct = (review_count / total * 100) if total else 0.0

    summary = []
    summary.append("=== EVALUATION SUMMARY ===")
    summary.append("")
    summary.append(f"Total EM==0 items evaluated:   {total}")
    summary.append("")
    summary.append("Judge parsing:")
    for col in judge_cols:
        summary.append(
            f"  {col} parsed: {parsed_counts[col]:5d} items  ({missing_counts[col]} missing -> HUMAN_REVIEW)"
        )
    summary.append("")
    summary.append("Agreement breakdown (3-judge majority):")
    summary.append(f"  CORRECT by majority:         {both_correct}")
    summary.append(f"  INCORRECT by majority:       {both_incorrect}")
    summary.append(f"  No majority / uncertain:     {human_review}  -> HUMAN_REVIEW")
    summary.append("")
    summary.append("Final labels:")
    summary.append(f"  CORRECT  (majority vote):    {correct_count}  ({correct_pct:.1f}%)")
    summary.append(f"  INCORRECT (majority vote):   {incorrect_count}  ({incorrect_pct:.1f}%)")
    summary.append(f"  HUMAN_REVIEW:                {review_count}  ({review_pct:.1f}%)")
    summary.append("")
    summary.append(f"Human review list saved to: {human_path}")
    summary.append(f"Final results saved to:     {output_path}")
    summary.append(f"Master write target:        {master_write_path}{master_write_note}")

    summary_text = "\n".join(summary) + "\n"
    summary_path.write_text(summary_text, encoding="utf-8")

    print(summary_text)


if __name__ == "__main__":
    main()
