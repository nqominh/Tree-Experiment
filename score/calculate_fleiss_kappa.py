import argparse
import io
import os
from collections import Counter
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


# Keep same normalization semantics as calculate_kappa.py


def map_common_judge_label(ans_lower: str):
    """Map both legacy and new judge labels to Fleiss classes.

    Supports:
    - Legacy markers: x/match/wrong table/no info
    - New labels: CORRECT/INCORRECT/UNCERTAIN
    """
    if ans_lower in ["x", "match", "correct", "true", "right"]:
        return "__MATCH__"

    if ans_lower in ["incorrect", "wrong", "false"]:
        return "__CORRECTION__"

    if ans_lower in [
        "",
        "nan",
        "none",
        "no info",
        "no_info",
        "wrong table",
        "uncertain",
        "human_review",
        "review",
    ]:
        return "__NO_INFO__"

    return None

def normalize_reviewer1(ans):
    ans = str(ans).strip()
    ans_lower = ans.lower()

    mapped = map_common_judge_label(ans_lower)
    if mapped is not None:
        return mapped

    # Reviewer 1 uses "x" to indicate match.
    if ans_lower == "x":
        return "__MATCH__"

    # Reviewer 1 "no info" variants.
    if ans_lower in ["no info", "no_info", "wrong table"]:
        return "__NO_INFO__"

    # Otherwise reviewer wrote a correction text.
    return ans_lower


def normalize_reviewer2(ans):
    ans = str(ans).strip()
    ans_lower = ans.lower()

    mapped = map_common_judge_label(ans_lower)
    if mapped is not None:
        return mapped

    # Reviewer 2 uses "match".
    if ans_lower == "match":
        return "__MATCH__"

    # Reviewer 2 blank / nan / none / wrong table => no info.
    if ans == "" or ans_lower in ["nan", "none", "wrong table"]:
        return "__NO_INFO__"

    return ans_lower


def normalize_reviewer3(ans):
    # Apply same semantics as reviewer2 for consistency.
    return normalize_reviewer2(ans)


def to_3_class(val: str) -> str:
    if val in ["__MATCH__", "__NO_INFO__"]:
        return val
    return "__CORRECTION__"


def is_no_info_marker(ans: str) -> bool:
    ans_lower = str(ans).strip().lower()
    return ans_lower in ["", "nan", "none", "no info", "no_info", "wrong table"]


def is_match_marker(ans: str) -> bool:
    ans_lower = str(ans).strip().lower()
    return ans_lower in ["x", "match"]


def canonicalize_answer_for_vote(raw_answer: str, processed_answer: str) -> str:
    raw = str(raw_answer).strip()
    processed = str(processed_answer).strip()

    if is_match_marker(raw):
        return " ".join(processed.split()).lower()
    if is_no_info_marker(raw):
        return ""

    return " ".join(raw.split()).lower()


def pretty_answer_for_output(raw_answer: str, processed_answer: str) -> str:
    raw = str(raw_answer).strip()
    processed = str(processed_answer).strip()

    if is_match_marker(raw):
        return processed
    if is_no_info_marker(raw):
        return ""

    return raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute Fleiss kappa for 3 reviewers")
    parser.add_argument(
        "--input",
        default="",
        help="Path to audit csv. Defaults to numerical_reasoning_audit.csv or score/numerical_reasoning_audit.csv",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path with final_judged_answer. Default: overwrite input file.",
    )
    parser.add_argument(
        "--max-id",
        type=int,
        default=0,
        help="Optional max id filter (0 means use all rows).",
    )
    return parser.parse_args()


def fleiss_kappa_from_ratings(rating_matrix: np.ndarray) -> float:
    """
    Compute Fleiss' kappa.

    rating_matrix shape: (N_items, K_categories)
    Each row contains category counts across raters.
    """
    if rating_matrix.ndim != 2:
        raise ValueError("rating_matrix must be 2D")

    n_items, n_cats = rating_matrix.shape
    if n_items == 0:
        raise ValueError("No items to score")

    row_sums = rating_matrix.sum(axis=1)
    unique_n = np.unique(row_sums)
    if len(unique_n) != 1:
        raise ValueError(f"Each item must have same #ratings. Found row sums: {unique_n.tolist()}")

    n_raters = int(unique_n[0])
    if n_raters < 2:
        raise ValueError("Need at least 2 ratings per item")

    # Per-item agreement
    p_i = (np.sum(rating_matrix * (rating_matrix - 1), axis=1)) / (n_raters * (n_raters - 1))
    p_bar = float(np.mean(p_i))

    # Category prevalence
    p_j = np.sum(rating_matrix, axis=0) / (n_items * n_raters)
    p_bar_e = float(np.sum(p_j ** 2))

    denom = 1.0 - p_bar_e
    if abs(denom) < 1e-12:
        return float("nan")

    return (p_bar - p_bar_e) / denom


def main():
    args = parse_args()

    if args.input:
        file_path = args.input
    else:
        file_path = "numerical_reasoning_audit.csv"
        if not os.path.exists(file_path):
            file_path = os.path.join("score", "numerical_reasoning_audit.csv")

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    df = pd.read_csv(io.StringIO(content))

    df["numeric_id"] = pd.to_numeric(df["id"], errors="coerce")
    if args.max_id > 0:
        df = df[df["numeric_id"] <= args.max_id].copy()
    else:
        df = df.copy()

    # Resolve reviewer columns robustly.
    r1_col = "Reviewer 1"

    r2_col = None
    r3_col = None
    for col in df.columns:
        col_s = str(col)
        if r2_col is None and "Reviewer 2" in col_s:
            r2_col = col
        if r3_col is None and "Reviewer 3" in col_s:
            r3_col = col

    if r2_col is None:
        if len(df.columns) > 5:
            r2_col = df.columns[5]
        else:
            print("Could not find Reviewer 2 column")
            return

    if r3_col is None:
        if len(df.columns) > 6:
            r3_col = df.columns[6]
        else:
            print("Could not find Reviewer 3 column")
            return

    for col in [r1_col, r2_col, r3_col]:
        if col not in df.columns:
            print(f"Missing expected column: {col}")
            return

    df[r1_col] = df[r1_col].fillna("")
    df[r2_col] = df[r2_col].fillna("")
    df[r3_col] = df[r3_col].fillna("")

    r1_mapped = df[r1_col].apply(normalize_reviewer1).tolist()
    r2_mapped = df[r2_col].apply(normalize_reviewer2).tolist()
    r3_mapped = df[r3_col].apply(normalize_reviewer3).tolist()

    r1_class = [to_3_class(v) for v in r1_mapped]
    r2_class = [to_3_class(v) for v in r2_mapped]
    r3_class = [to_3_class(v) for v in r3_mapped]

    labels: List[str] = ["__MATCH__", "__CORRECTION__", "__NO_INFO__"]
    label_to_idx = {lab: i for i, lab in enumerate(labels)}

    rating_rows = []
    final_judged_answers: List[str] = []
    for a, b, c in zip(r1_class, r2_class, r3_class):
        row = np.zeros(len(labels), dtype=int)
        row[label_to_idx[a]] += 1
        row[label_to_idx[b]] += 1
        row[label_to_idx[c]] += 1
        rating_rows.append(row)

    # Compute final judged answer by majority vote across actual reviewer answers.
    # Rule: if all 3 reviewers provide different non-empty answers, leave blank.
    for _, row in df.iterrows():
        processed = str(row.get("Processed Answer", "")).strip()
        raw_answers = [
            str(row.get(r1_col, "")).strip(),
            str(row.get(r2_col, "")).strip(),
            str(row.get(r3_col, "")).strip(),
        ]

        canon = [canonicalize_answer_for_vote(x, processed) for x in raw_answers]
        pretty = [pretty_answer_for_output(x, processed) for x in raw_answers]

        non_empty_canon = [x for x in canon if x]
        if len(non_empty_canon) == 3 and len(set(non_empty_canon)) == 3:
            final_judged_answers.append("")
            continue

        counts = Counter(non_empty_canon)
        if not counts:
            final_judged_answers.append("")
            continue

        winner, winner_count = counts.most_common(1)[0]
        if winner_count >= 2:
            chosen = ""
            for c_val, p_val in zip(canon, pretty):
                if c_val == winner and p_val:
                    chosen = p_val
                    break
            final_judged_answers.append(chosen)
        else:
            final_judged_answers.append("")

    rating_matrix = np.vstack(rating_rows)
    kappa = fleiss_kappa_from_ratings(rating_matrix)

    total = len(df)
    exact_three_agree = sum(1 for a, b, c in zip(r1_class, r2_class, r3_class) if a == b == c)

    print("=== FLEISS KAPPA (3 REVIEWERS) ===")
    print(f"File: {file_path}")
    if args.max_id > 0:
        print(f"Rows considered (id <= {args.max_id}): {total}")
    else:
        print(f"Rows considered (all rows): {total}")
    print("Classes: __MATCH__, __CORRECTION__, __NO_INFO__")
    print(f"Exact 3-way agreement: {exact_three_agree}/{total} ({(exact_three_agree/total)*100:.2f}%)")
    print(f"Fleiss' Kappa: {kappa:.4f}")

    df["final_judged_answer"] = final_judged_answers

    output_path = Path(args.output) if args.output else Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(output_path, index=False, encoding="utf-8")
    except PermissionError:
        fallback = output_path.with_name(f"{output_path.stem}.updated{output_path.suffix}")
        df.to_csv(fallback, index=False, encoding="utf-8")
        output_path = fallback

    populated = int((df["final_judged_answer"].astype(str).str.strip() != "").sum())
    print(f"Rows with final_judged_answer: {populated}/{len(df)}")
    print(f"Saved file: {output_path}")


if __name__ == "__main__":
    main()
