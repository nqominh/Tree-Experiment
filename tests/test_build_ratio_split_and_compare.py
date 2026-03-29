"""Tests for ratio sampling + C1-vs-new comparison utility script."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_ratio_split_and_compare.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_ratio_split_and_compare", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_split_is_reproducible_and_matches_fixed_quotas(tmp_path) -> None:
    mod = _load_module()
    questions_path = tmp_path / "questions.jsonl"

    rows: list[dict] = []
    next_id = 1
    for subtype, quota in mod.SUBTYPE_QUOTAS.items():
        for _ in range(quota + 5):
            rows.append(
                {
                    "id": next_id,
                    "table_id": f"t{next_id}",
                    "query": f"q{next_id}",
                    "label": f"a{next_id}",
                    "SubQType": subtype,
                }
            )
            next_id += 1
    _write_jsonl(questions_path, rows)

    out1 = tmp_path / "split_seed42_a.jsonl"
    sum1 = tmp_path / "split_seed42_a_summary.json"
    out2 = tmp_path / "split_seed42_b.jsonl"
    sum2 = tmp_path / "split_seed42_b_summary.json"
    out3 = tmp_path / "split_seed7.jsonl"
    sum3 = tmp_path / "split_seed7_summary.json"

    s1 = mod.build_split(
        questions_jsonl=questions_path,
        split_output_jsonl=out1,
        split_summary_output=sum1,
        seed=42,
        sample_size=120,
    )
    s2 = mod.build_split(
        questions_jsonl=questions_path,
        split_output_jsonl=out2,
        split_summary_output=sum2,
        seed=42,
        sample_size=120,
    )
    s3 = mod.build_split(
        questions_jsonl=questions_path,
        split_output_jsonl=out3,
        split_summary_output=sum3,
        seed=7,
        sample_size=120,
    )

    ids1 = s1["sampled_ids_in_output_order"]
    ids2 = s2["sampled_ids_in_output_order"]
    ids3 = s3["sampled_ids_in_output_order"]

    assert ids1 == ids2
    assert ids1 != ids3
    assert s1["realized_counts"] == mod.SUBTYPE_QUOTAS
    assert len(_read_jsonl(out1)) == 120

    counts = Counter(row["sub_type"] for row in _read_jsonl(out1))
    assert dict(counts) == mod.SUBTYPE_QUOTAS


def test_compare_schema_includes_c1_em_and_missing_answers_zero_metrics(tmp_path) -> None:
    mod = _load_module()
    sampled_jsonl = tmp_path / "sampled.jsonl"
    c1_csv = tmp_path / "c1.csv"
    new_csv = tmp_path / "new.csv"
    out_csv = tmp_path / "compare.csv"

    sampled_rows = [
        {"id": "1", "table_id": "t1", "query": "Q1", "label": "The cat", "sub_type": "Comparison"},
        {"id": "2", "table_id": "t2", "query": "Q2", "label": "12", "sub_type": "Calculation"},
        {"id": "3", "table_id": "t3", "query": "Q3", "label": "x", "sub_type": "Ranking"},
    ]
    _write_jsonl(sampled_jsonl, sampled_rows)

    _write_csv(
        c1_csv,
        rows=[
            {"id": "1", "model_answer": "cat", "EM": "77"},
            {"id": "2", "model_answer": "11", "EM": "0"},
        ],
        columns=["id", "model_answer", "EM"],
    )
    _write_csv(
        new_csv,
        rows=[
            {"id": "1", "model_answer": "cat"},
            {"id": "3", "model_answer": "x"},
        ],
        columns=["id", "model_answer"],
    )

    stats = mod.build_compare(
        sampled_questions_jsonl=sampled_jsonl,
        c1_csv=c1_csv,
        new_pipeline_csv=new_csv,
        compare_output_csv=out_csv,
    )

    rows = _read_csv(out_csv)
    assert rows
    assert list(rows[0].keys()) == mod.COMPARE_COLUMNS
    assert stats["rows_written"] == 3
    assert stats["missing_c1_answer"] == 1
    assert stats["missing_new_answer"] == 1

    by_id = {row["id"]: row for row in rows}

    # c1 em is copied from baseline CSV directly (not recomputed)
    assert by_id["1"]["c1 em"] == "77"
    assert by_id["1"]["em"] == "1"
    assert float(by_id["1"]["f1"]) == 100.0

    # Missing NEW answer => em/f1 forced to zero.
    assert by_id["2"]["new pipeline answer"] == ""
    assert by_id["2"]["em"] == "0"
    assert float(by_id["2"]["f1"]) == 0.0

    # Missing C1 answer => em/f1 forced to zero.
    assert by_id["3"]["c1 answer"] == ""
    assert by_id["3"]["em"] == "0"
    assert float(by_id["3"]["f1"]) == 0.0
