"""
select_next_100.py -- Sample 100 Numerical Reasoning questions from QA_final.json

Filters:
  1. QuestionType == "Numerical Reasoning"
  2. id > 365  (exclude the first batch already in questions.jsonl)

Outputs:
  tests/questions_batch2.jsonl  (same format as questions.jsonl)

Usage:
  python select_next_100.py
  python select_next_100.py --seed 42 --count 100
"""

import argparse
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
QA_SOURCE    = PROJECT_ROOT / "RealHiTBench" / "QA_final.json"
OUTPUT_PATH  = PROJECT_ROOT / "tests" / "questions_batch2.jsonl"


def main():
    parser = argparse.ArgumentParser(description="Sample NR questions from QA_final.json")
    parser.add_argument("--seed",  type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--count", type=int, default=100, help="Number of questions to sample")
    parser.add_argument("--min-id", type=int, default=366, help="Minimum question ID (exclusive of first batch)")
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH))
    args = parser.parse_args()

    # Load source
    with open(QA_SOURCE, encoding="utf-8") as f:
        data = json.load(f)
    all_questions = data["queries"]
    print(f"Loaded {len(all_questions)} total questions from QA_final.json")

    # Filter: Numerical Reasoning only
    nr_questions = [q for q in all_questions if q.get("QuestionType") == "Numerical Reasoning"]
    print(f"Numerical Reasoning questions: {len(nr_questions)}")

    # Exclude first batch (id <= 365)
    pool = [q for q in nr_questions if q["id"] >= args.min_id]
    print(f"Pool after excluding IDs < {args.min_id}: {len(pool)}")

    if len(pool) < args.count:
        print(f"WARNING: Only {len(pool)} questions available, sampling all of them")
        sample = pool
    else:
        random.seed(args.seed)
        sample = random.sample(pool, args.count)

    # Sort by ID for readability
    sample.sort(key=lambda q: q["id"])

    # Write in questions.jsonl format
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        for q in sample:
            row = {
                "id":       q["id"],
                "table_id": q["FileName"],
                "query":    q["Question"],
                "label":    q["ProcessedAnswer"],
                "sub_type": q["SubQType"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(sample)} questions to {output_path}")
    print(f"ID range: {sample[0]['id']} — {sample[-1]['id']}")

    # Summary by sub_type
    st = {}
    for q in sample:
        t = q["SubQType"]
        st[t] = st.get(t, 0) + 1
    print("\nSub-type distribution:")
    for k, v in sorted(st.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
