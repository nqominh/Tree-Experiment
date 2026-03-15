import io
import json
import os
from pathlib import Path

import pandas as pd


NO_INFO_MARKERS = {"", "nan", "none", "no info", "no_info", "wrong table"}


def is_blank_or_no_info(value: object) -> bool:
    text = str(value).strip().lower()
    return text in NO_INFO_MARKERS


def find_audit_csv(project_root: Path) -> Path:
    candidates = [
        project_root / "score" / "numerical_reasoning_audit.csv",
        project_root / "numerical_reasoning_audit.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("numerical_reasoning_audit.csv not found")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    tests_dir = project_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    audit_path = find_audit_csv(project_root)

    with open(audit_path, "r", encoding="utf-8", errors="replace") as f:
        df = pd.read_csv(io.StringIO(f.read()))

    required_cols = ["id", "Question", "Processed Answer", "final_judged_answer"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns in audit file: {missing}")

    df["numeric_id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df[~df["numeric_id"].isna()].copy()
    df["qid"] = df["numeric_id"].astype(int).astype(str)

    blank_mask = df["final_judged_answer"].apply(is_blank_or_no_info)
    inspect_df = df[blank_mask].copy()
    usable_df = df[~blank_mask].copy()

    qa_path = project_root / "RealHiTBench" / "QA_final.json"
    if not qa_path.exists():
        raise SystemExit(f"Original questions file not found: {qa_path}")

    with open(qa_path, "r", encoding="utf-8") as f:
        qa_data = json.load(f)
    queries = qa_data.get("queries", [])

    query_by_id = {str(q.get("id")): q for q in queries}

    clean_questions = []
    missing_in_qa = []
    for _, row in usable_df.iterrows():
        qid = row["qid"]
        original_q = query_by_id.get(qid)
        if original_q is None:
            missing_in_qa.append(qid)
            continue

        final_answer = str(row.get("final_judged_answer", "")).strip()
        if not final_answer:
            continue

        new_q = original_q.copy()
        # Keep canonical aliases used by experiment scripts.
        new_q["table_id"] = new_q.get("FileName", "")
        new_q["query"] = new_q.get("Question", "")

        # Enforce cleaned contract: ProcessedAnswer must match final_judged_answer.
        new_q["ProcessedAnswer"] = final_answer
        new_q["FinalAnswer"] = final_answer
        new_q["label"] = final_answer
        new_q["answer"] = final_answer

        # Keep traceability for audit provenance.
        new_q["final_judged_answer"] = final_answer
        new_q["audit_processed_answer_original"] = str(row.get("Processed Answer", "")).strip()
        clean_questions.append(new_q)

    clean_out = tests_dir / "questions_clean_audit.jsonl"
    with open(clean_out, "w", encoding="utf-8") as f:
        for q in clean_questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    inspect_cols = [
        "id",
        "FileName",
        "Question",
        "Processed Answer",
        "Reviewer 1",
        "Reviewer 2",
        "Reviewer 3",
        "final_judged_answer",
    ]
    inspect_existing = [c for c in inspect_cols if c in inspect_df.columns]
    inspect_out = tests_dir / "questions_clean_audit_needs_review.csv"
    inspect_df[inspect_existing].to_csv(inspect_out, index=False, encoding="utf-8")

    print("=== CLEAN AUDIT DATASET SUMMARY ===")
    print(f"Audit file: {audit_path}")
    print(f"Total audit rows: {len(df)}")
    print(f"Usable judged rows: {len(usable_df)}")
    print(f"Needs review rows (blank/no info): {len(inspect_df)}")
    print(f"Clean JSONL written: {clean_out} ({len(clean_questions)} rows)")
    print(f"Needs review CSV written: {inspect_out}")
    if missing_in_qa:
        print(f"WARN: IDs not found in QA_final.json: {len(missing_in_qa)} (sample: {missing_in_qa[:15]})")


if __name__ == "__main__":
    main()
