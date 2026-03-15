"""Validate the cleaned audit dataset built from final_judged_answer.

Checks:
1. Every clean JSONL ID exists in the audit CSV.
2. Every clean row has non-blank/non-no-info final_judged_answer in audit CSV.
3. ProcessedAnswer in JSONL equals final_judged_answer exactly (trimmed).
4. label and answer in JSONL equal ProcessedAnswer.
5. IDs with blank/no-info final_judged_answer are excluded from clean JSONL.
6. Excluded IDs are present in the needs-review CSV file.
"""

import json
import io
import os
import sys
import pandas as pd


NO_INFO_MARKERS = {"", "nan", "none", "no info", "no_info", "wrong table"}


def is_blank_or_no_info(value: object) -> bool:
    text = str(value).strip().lower()
    return text in NO_INFO_MARKERS

def load_audit_csv():
    csv_path = os.path.join(os.path.dirname(__file__), "numerical_reasoning_audit.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(os.path.dirname(__file__), "..", "numerical_reasoning_audit.csv")
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        df = pd.read_csv(io.StringIO(f.read()))
    df['numeric_id'] = pd.to_numeric(df['id'], errors='coerce')
    df = df[~df['numeric_id'].isna()].copy()
    return df

def load_clean_jsonl():
    jsonl_path = os.path.join(os.path.dirname(__file__), "..", "tests", "questions_clean_audit.jsonl")
    questions = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def load_needs_review_csv():
    csv_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "tests",
        "questions_clean_audit_needs_review.csv",
    )
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=["id"])
    return pd.read_csv(csv_path, dtype=object)

def main():
    df = load_audit_csv()
    clean_qs = load_clean_jsonl()
    needs_review_df = load_needs_review_csv()

    required_cols = ["id", "Question", "Processed Answer", "final_judged_answer"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"FAIL: Missing required columns in audit csv: {missing}")
        return 1

    audit_by_id = {}
    for _, row in df.iterrows():
        qid = str(int(row['numeric_id']))
        audit_by_id[qid] = {
            'question': str(row.get('Question', '')).strip(),
            'processed_answer': str(row.get('Processed Answer', '')).strip(),
            'final_judged_answer': str(row.get('final_judged_answer', '')).strip(),
        }

    clean_ids = set()
    if len(clean_qs) != len({str(q.get('id')) for q in clean_qs}):
        print("FAIL: Duplicate IDs found in questions_clean_audit.jsonl")
        return 1
    
    passed = 0
    failed = 0
    errors = []
    
    for q in clean_qs:
        qid = str(q['id'])
        clean_ids.add(qid)
        
        # Test 1: ID exists in audit CSV
        if qid not in audit_by_id:
            errors.append(f"FAIL [ID {qid}]: Not found in audit CSV")
            failed += 1
            continue
        
        audit = audit_by_id[qid]
        
        # Test 2: Question text matches
        csv_question = audit['question']
        jsonl_question = str(q.get('Question', '')).strip()
        if csv_question != jsonl_question:
            errors.append(f"FAIL [ID {qid}]: Question mismatch\n  CSV:   '{csv_question[:80]}...'\n  JSONL: '{jsonl_question[:80]}...'")
            failed += 1
            continue

        # Test 3: final_judged_answer must be usable
        final_judged = audit['final_judged_answer']
        if is_blank_or_no_info(final_judged):
            errors.append(f"FAIL [ID {qid}]: Included in clean set but final_judged_answer is blank/no-info")
            failed += 1
            continue

        # Test 4: ProcessedAnswer must match final_judged_answer exactly (trimmed)
        jsonl_processed = str(q.get('ProcessedAnswer', '')).strip()
        if jsonl_processed != final_judged:
            errors.append(
                f"FAIL [ID {qid}]: ProcessedAnswer must equal final_judged_answer\n"
                f"  final_judged_answer: '{final_judged}'\n"
                f"  JSONL ProcessedAnswer: '{jsonl_processed}'"
            )
            failed += 1
            continue

        # Test 5: label and answer must align with ProcessedAnswer
        label = str(q.get('label', '')).strip()
        answer = str(q.get('answer', '')).strip()
        if label != jsonl_processed:
            errors.append(
                f"FAIL [ID {qid}]: label mismatch\n"
                f"  label: '{label}'\n"
                f"  ProcessedAnswer: '{jsonl_processed}'"
            )
            failed += 1
            continue
        if answer != jsonl_processed:
            errors.append(
                f"FAIL [ID {qid}]: answer mismatch\n"
                f"  answer: '{answer}'\n"
                f"  ProcessedAnswer: '{jsonl_processed}'"
            )
            failed += 1
            continue
        
        passed += 1
    
    # Test 6: ensure all blank/no-info IDs are excluded from clean and present in needs-review CSV.
    blank_ids = {
        str(int(row['numeric_id']))
        for _, row in df.iterrows()
        if is_blank_or_no_info(row.get('final_judged_answer', ''))
    }
    overlap = blank_ids.intersection(clean_ids)
    if overlap:
        errors.append(f"FAIL: Blank/no-info IDs present in clean JSONL: {sorted(list(overlap))[:20]}")
        failed += 1

    review_ids = set()
    if not needs_review_df.empty and 'id' in needs_review_df.columns:
        for v in needs_review_df['id'].tolist():
            try:
                review_ids.add(str(int(float(str(v).strip()))))
            except Exception:
                pass

    missing_review_ids = blank_ids - review_ids
    if missing_review_ids:
        errors.append(
            "FAIL: Some blank/no-info IDs are missing from questions_clean_audit_needs_review.csv: "
            f"{sorted(list(missing_review_ids))[:20]}"
        )
        failed += 1

    # Print results
    print("=" * 60)
    print(f"Clean Dataset Verification Report")
    print("=" * 60)
    print(f"Total clean questions tested: {len(clean_qs)}")
    print(f"Total blank/no-info rows in audit: {len(blank_ids)}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print("=" * 60)
    
    if errors:
        print("\nFailures:")
        for e in errors:
            print(f"  {e}")
    else:
        print("\nAll tests passed!")
    
    # Return exit code
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
