"""Build a ratio-stratified sample and compare C1 vs new-pipeline outputs.

This script supports three modes:
  - split:   create a reproducible 120-row stratified sample JSONL
  - compare: build side-by-side C1 vs new-pipeline comparison CSV
  - all:     run split then compare in one command

Comparison CSV columns:
  id,questions,subqtype,c1 answer,c1 em,new pipeline answer,em,f1

Notes:
  - `c1 em` is copied directly from the baseline C1 CSV `EM` column.
  - `em` and `f1` are computed for NEW pipeline answer vs gold label.
  - If either C1 answer or NEW answer is missing, `em=0` and `f1=0`.
  - F1 preprocessing/logic mirrors `qa_metrics.py`.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import string
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.answer_normalization import exact_match_with_normalization

# Allow reading large prompt/response fields from audit CSVs.
csv.field_size_limit(sys.maxsize)

DEFAULT_QUESTIONS_JSONL = PROJECT_ROOT / "tests" / "questions_clean_audit copy.jsonl"
DEFAULT_C1_CSV = PROJECT_ROOT / "score" / "minimax" / "C1_vanilla_minimax_audit.csv"

DEFAULT_SEED = 42
DEFAULT_SAMPLE_SIZE = 120

SUBTYPE_QUOTAS: dict[str, int] = {
    "Calculation": 39,
    "Comparison": 18,
    "Counting": 36,
    "Multi-hop Numerical Reasoning": 11,
    "Ranking": 16,
}

COMPARE_COLUMNS = [
    "id",
    "questions",
    "subqtype",
    "c1 answer",
    "c1 em",
    "new pipeline answer",
    "em",
    "f1",
]


def _normalize_id(raw_id: Any) -> str:
    return str(raw_id).strip()


def _pick_first_nonempty(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def canonicalize_question_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map raw question JSONL record into runner-compatible canonical shape."""
    qid = _normalize_id(row.get("id", ""))
    table_id = _pick_first_nonempty(row, ("table_id", "FileName"))
    query = _pick_first_nonempty(row, ("query", "Question"))
    label = _pick_first_nonempty(
        row,
        ("label", "final_judged_answer", "answer", "FinalAnswer", "ProcessedAnswer"),
    )
    sub_type = _pick_first_nonempty(row, ("SubQType", "sub_type"))

    if not qid:
        raise ValueError("Question row missing `id`.")
    if not table_id:
        raise ValueError(f"Question {qid} missing `table_id`/`FileName`.")
    if not query:
        raise ValueError(f"Question {qid} missing `query`/`Question`.")
    if not label:
        raise ValueError(f"Question {qid} missing label fields.")
    if not sub_type:
        raise ValueError(f"Question {qid} missing `SubQType`/`sub_type`.")

    return {
        "id": qid,
        "table_id": table_id,
        "query": query,
        "label": label,
        "sub_type": sub_type,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_stratified_sample(
    questions: list[dict[str, Any]],
    subtype_quotas: dict[str, int],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Sample per-subtype with fixed quotas, then shuffle mixed output."""
    by_subtype: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        by_subtype[str(row["sub_type"]).strip()].append(row)

    insufficient: list[str] = []
    for subtype, needed in subtype_quotas.items():
        available = len(by_subtype.get(subtype, []))
        if available < needed:
            insufficient.append(f"{subtype}: need {needed}, available {available}")
    if insufficient:
        details = "; ".join(insufficient)
        raise ValueError(f"Insufficient rows for requested quotas. {details}")

    rng = random.Random(seed)
    sampled: list[dict[str, Any]] = []
    sampled_ids_by_subtype: dict[str, list[str]] = {}

    for subtype, needed in subtype_quotas.items():
        selected = rng.sample(by_subtype[subtype], needed)
        sampled.extend(selected)
        sampled_ids_by_subtype[subtype] = [_normalize_id(row["id"]) for row in selected]

    rng.shuffle(sampled)
    return sampled, sampled_ids_by_subtype


def build_split(
    questions_jsonl: Path,
    split_output_jsonl: Path,
    split_summary_output: Path,
    seed: int,
    sample_size: int,
    subtype_quotas: dict[str, int] | None = None,
) -> dict[str, Any]:
    quotas = subtype_quotas or SUBTYPE_QUOTAS
    expected_size = sum(quotas.values())
    if sample_size != expected_size:
        raise ValueError(
            f"sample_size ({sample_size}) must equal sum of quotas ({expected_size})."
        )

    raw_rows = load_jsonl(questions_jsonl)
    canonical_rows = [canonicalize_question_row(row) for row in raw_rows]
    sampled_rows, sampled_ids_by_subtype = build_stratified_sample(
        canonical_rows,
        subtype_quotas=quotas,
        seed=seed,
    )
    write_jsonl(split_output_jsonl, sampled_rows)

    realized_counts = Counter(row["sub_type"] for row in sampled_rows)
    summary = {
        "source_questions_jsonl": str(questions_jsonl),
        "seed": seed,
        "sample_size": len(sampled_rows),
        "quotas": quotas,
        "realized_counts": dict(realized_counts),
        "sampled_ids_by_subtype": sampled_ids_by_subtype,
        "sampled_ids_in_output_order": [_normalize_id(row["id"]) for row in sampled_rows],
    }

    split_summary_output.parent.mkdir(parents=True, exist_ok=True)
    split_summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _load_csv_first_by_id(path: Path) -> tuple[dict[str, dict[str, str]], int]:
    by_id: dict[str, dict[str, str]] = {}
    duplicates = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        if "id" not in reader.fieldnames:
            raise ValueError(f"CSV missing required `id` column: {path}")
        for row in reader:
            qid = _normalize_id(row.get("id", ""))
            if not qid:
                continue
            if qid in by_id:
                duplicates += 1
                continue
            by_id[qid] = row
    return by_id, duplicates


def _qa_process_decimal(text: str) -> str:
    pattern = r"\b\d+\.\d+\b"

    def _round_match(match: re.Match[str]) -> str:
        number = float(match.group())
        rounded_number = round(number, 1)
        return str(rounded_number)

    return re.sub(pattern, _round_match, text)


def _qa_normalize_answer(text: str) -> str:
    def remove_articles(value: str) -> str:
        return re.sub(r"\b(a|an|the)\b", " ", value)

    def white_space_fix(value: str) -> str:
        return " ".join(value.split())

    def remove_punc(value: str) -> str:
        excluded = set(string.punctuation)
        return "".join(ch for ch in value if ch not in excluded)

    def lower(value: str) -> str:
        return value.lower()

    return white_space_fix(remove_articles(remove_punc(lower(text))))


def _qa_word_level_f1(reference: str, prediction: str) -> float:
    prediction_words = prediction.split()
    reference_words = reference.split()
    common = Counter(prediction_words) & Counter(reference_words)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = 1.0 * num_same / len(prediction_words)
    recall = 1.0 * num_same / len(reference_words)
    return (2 * precision * recall) / (precision + recall)


def qa_style_row_f1(reference: str, prediction: str) -> float:
    """Replicate qa_metrics.py preprocessing + token-overlap F1 for one row.

    Returns percentage score in [0, 100], rounded to 2 decimals.
    """
    ref = _qa_normalize_answer(_qa_process_decimal(str(reference)))
    pred = _qa_normalize_answer(_qa_process_decimal(str(prediction)))
    if len(pred) == 0:
        pred = "#"
    return round(_qa_word_level_f1(ref, pred) * 100, 2)


def build_compare(
    sampled_questions_jsonl: Path,
    c1_csv: Path,
    new_pipeline_csv: Path,
    compare_output_csv: Path,
) -> dict[str, Any]:
    sampled_raw = load_jsonl(sampled_questions_jsonl)
    sampled = [canonicalize_question_row(row) for row in sampled_raw]

    c1_by_id, c1_duplicates = _load_csv_first_by_id(c1_csv)
    new_by_id, new_duplicates = _load_csv_first_by_id(new_pipeline_csv)

    missing_c1_answer = 0
    missing_new_answer = 0
    missing_label = 0
    rows_out: list[dict[str, Any]] = []

    for row in sampled:
        qid = _normalize_id(row["id"])
        question = row["query"]
        subqtype = row["sub_type"]
        gold_label = str(row.get("label", "")).strip()

        c1_row = c1_by_id.get(qid, {})
        new_row = new_by_id.get(qid, {})

        c1_answer = str(c1_row.get("model_answer", "") or "").strip()
        c1_em = str(c1_row.get("EM", "") or "").strip()
        new_answer = str(new_row.get("model_answer", "") or "").strip()

        if not c1_answer:
            missing_c1_answer += 1
        if not new_answer:
            missing_new_answer += 1
        if not gold_label:
            missing_label += 1

        if (not c1_answer) or (not new_answer) or (not gold_label):
            em = 0
            f1 = 0.0
        else:
            em = exact_match_with_normalization(new_answer, gold_label)
            f1 = qa_style_row_f1(gold_label, new_answer)

        rows_out.append(
            {
                "id": qid,
                "questions": question,
                "subqtype": subqtype,
                "c1 answer": c1_answer,
                "c1 em": c1_em,
                "new pipeline answer": new_answer,
                "em": em,
                "f1": f1,
            }
        )

    compare_output_csv.parent.mkdir(parents=True, exist_ok=True)
    with compare_output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPARE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows_out)

    return {
        "rows_written": len(rows_out),
        "missing_c1_answer": missing_c1_answer,
        "missing_new_answer": missing_new_answer,
        "missing_label": missing_label,
        "c1_duplicate_ids_ignored": c1_duplicates,
        "new_duplicate_ids_ignored": new_duplicates,
        "output_csv": str(compare_output_csv),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create ratio-stratified sample and C1-vs-new comparison CSV."
    )
    parser.add_argument(
        "--mode",
        choices=["split", "compare", "all"],
        default="all",
        help="split: sample only, compare: compare only, all: split then compare",
    )
    parser.add_argument(
        "--questions-jsonl",
        type=str,
        default=str(DEFAULT_QUESTIONS_JSONL),
        help="Source questions JSONL for sampling",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help="Must equal sum of configured subtype quotas (default: 120)",
    )
    parser.add_argument(
        "--split-output-jsonl",
        type=str,
        default="",
        help="Output sampled JSONL path (default derived from seed)",
    )
    parser.add_argument(
        "--split-summary-output",
        type=str,
        default="",
        help="Output summary JSON path (default derived from seed)",
    )
    parser.add_argument(
        "--c1-csv",
        type=str,
        default=str(DEFAULT_C1_CSV),
        help="Baseline C1 CSV (reads model_answer and EM)",
    )
    parser.add_argument(
        "--new-csv",
        type=str,
        default="",
        help="New pipeline CSV for comparison mode/all mode",
    )
    parser.add_argument(
        "--compare-output-csv",
        type=str,
        default="",
        help="Comparison CSV output (default derived from seed)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    questions_jsonl = Path(args.questions_jsonl)
    split_output_jsonl = (
        Path(args.split_output_jsonl)
        if args.split_output_jsonl
        else PROJECT_ROOT / "tests" / f"questions_ratio120_seed{args.seed}.jsonl"
    )
    split_summary_output = (
        Path(args.split_summary_output)
        if args.split_summary_output
        else PROJECT_ROOT / "tests" / f"questions_ratio120_seed{args.seed}_summary.json"
    )
    compare_output_csv = (
        Path(args.compare_output_csv)
        if args.compare_output_csv
        else PROJECT_ROOT / "score" / "minimax" / f"c1_vs_new_pipeline_ratio120_seed{args.seed}.csv"
    )
    c1_csv = Path(args.c1_csv)

    if args.mode in {"compare", "all"} and not args.new_csv:
        raise SystemExit("ERROR: --new-csv is required for compare/all mode.")
    new_csv = Path(args.new_csv) if args.new_csv else None

    if args.mode in {"split", "all"}:
        split_summary = build_split(
            questions_jsonl=questions_jsonl,
            split_output_jsonl=split_output_jsonl,
            split_summary_output=split_summary_output,
            seed=args.seed,
            sample_size=args.sample_size,
        )
        print(f"[split] wrote sampled JSONL: {split_output_jsonl}")
        print(f"[split] wrote summary JSON: {split_summary_output}")
        print(f"[split] sampled rows: {split_summary['sample_size']}")
        print(f"[split] subtype counts: {split_summary['realized_counts']}")

    if args.mode in {"compare", "all"}:
        compare_stats = build_compare(
            sampled_questions_jsonl=split_output_jsonl,
            c1_csv=c1_csv,
            new_pipeline_csv=new_csv,
            compare_output_csv=compare_output_csv,
        )
        print(f"[compare] wrote comparison CSV: {compare_output_csv}")
        print(f"[compare] rows: {compare_stats['rows_written']}")
        print(
            "[compare] missing -> "
            f"c1_answer={compare_stats['missing_c1_answer']}, "
            f"new_answer={compare_stats['missing_new_answer']}, "
            f"label={compare_stats['missing_label']}"
        )
        print(
            "[compare] duplicate ids ignored -> "
            f"c1={compare_stats['c1_duplicate_ids_ignored']}, "
            f"new={compare_stats['new_duplicate_ids_ignored']}"
        )


if __name__ == "__main__":
    main()
