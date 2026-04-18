#!/usr/bin/env python3
"""
Comprehensive EDA for C1/C3/C5 minimax audits with router-focused outputs.

Inputs:
- score/minimax/C1_vanilla_minimax_audit.csv
- score/minimax/C3_schema_only_minimax_audit.csv
- score/minimax/C5_full_method_minimax_audit.csv
- tests/questions_clean_audit copy.jsonl

Outputs (default: score/minimax/router_eda):
- router_main_comparison.csv
- router_by_table_summary.csv
- router_by_subtype_summary.csv
- router_disagreement_only.csv
- router_executive_summary.md
- charts/*.png
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


@dataclass
class LoadStats:
    name: str
    rows_raw: int
    rows_deduped: int
    duplicates_removed: int


MODEL_SPECS = [
    ("C1", "c1", "score/minimax/C1_vanilla_minimax_audit.csv"),
    ("C3", "c3", "score/minimax/C3_schema_only_minimax_audit.csv"),
    ("C5", "c5", "score/minimax/C5_full_method_minimax_audit.csv"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Router EDA with charts for C1/C3/C5 minimax audits")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Workspace root directory",
    )
    parser.add_argument(
        "--jsonl-path",
        default="tests/questions_clean_audit copy.jsonl",
        help="Path to audit metadata JSONL (relative to base-dir)",
    )
    parser.add_argument(
        "--output-dir",
        default="score/minimax/router_eda",
        help="Output directory for CSV/MD/charts (relative to base-dir)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Top-N groups for risk charts",
    )
    return parser.parse_args()


def ensure_id_as_str(df: pd.DataFrame, id_col: str = "id") -> pd.DataFrame:
    out = df.copy()
    out[id_col] = out[id_col].astype(str).str.strip()
    return out


def load_minimax_model(base_dir: Path, model_key: str, csv_rel_path: str) -> Tuple[pd.DataFrame, LoadStats]:
    csv_path = base_dir / csv_rel_path
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing model file: {csv_path}")

    needed_cols = ["id", "question", "correct_answer", "model_answer", "filename", "sub_type", "EM"]
    df = pd.read_csv(csv_path, usecols=needed_cols)
    rows_raw = len(df)
    df = ensure_id_as_str(df)

    dup_mask = df.duplicated(subset=["id"], keep="first")
    duplicates_removed = int(dup_mask.sum())
    if duplicates_removed:
        df = df.loc[~dup_mask].copy()

    df[f"{model_key}_em"] = pd.to_numeric(df["EM"], errors="coerce")
    df[f"{model_key}_em"] = df[f"{model_key}_em"].round().clip(lower=0, upper=1)

    renamed = df.rename(
        columns={
            "question": f"{model_key}_question",
            "correct_answer": f"{model_key}_correct_answer",
            "model_answer": f"{model_key}_model_answer",
            "filename": f"{model_key}_filename",
            "sub_type": f"{model_key}_sub_type",
        }
    )
    keep = [
        "id",
        f"{model_key}_question",
        f"{model_key}_correct_answer",
        f"{model_key}_model_answer",
        f"{model_key}_filename",
        f"{model_key}_sub_type",
        f"{model_key}_em",
    ]
    cleaned = renamed[keep].copy()

    stats = LoadStats(
        name=model_key,
        rows_raw=rows_raw,
        rows_deduped=len(cleaned),
        duplicates_removed=duplicates_removed,
    )
    return cleaned, stats


def _first_present(record: dict, keys: Iterable[str]) -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def load_jsonl_metadata(base_dir: Path, jsonl_rel_path: str) -> Tuple[pd.DataFrame, LoadStats]:
    jsonl_path = base_dir / jsonl_rel_path
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Missing metadata file: {jsonl_path}")

    rows: List[dict] = []
    with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            rec_id = str(rec.get("id", "")).strip()
            if not rec_id:
                continue

            rows.append(
                {
                    "id": rec_id,
                    "meta_table_id": _first_present(rec, ["table_id", "FileName"]),
                    "meta_file_name": _first_present(rec, ["FileName", "table_id"]),
                    "meta_subqtype": _first_present(rec, ["SubQType"]),
                    "meta_question_type": _first_present(rec, ["QuestionType"]),
                    "meta_question": _first_present(rec, ["query", "Question"]),
                    "meta_label": _first_present(rec, ["final_judged_answer", "label", "answer", "FinalAnswer"]),
                    "meta_source": _first_present(rec, ["Source"]),
                    "meta_structure": _first_present(rec, ["CompStrucCata"]),
                }
            )

    df = pd.DataFrame(rows)
    rows_raw = len(df)
    dup_mask = df.duplicated(subset=["id"], keep="first")
    duplicates_removed = int(dup_mask.sum())
    if duplicates_removed:
        df = df.loc[~dup_mask].copy()

    stats = LoadStats(
        name="metadata",
        rows_raw=rows_raw,
        rows_deduped=len(df),
        duplicates_removed=duplicates_removed,
    )
    return df, stats


def classify_pattern(c1_em: float, c3_em: float, c5_em: float) -> str:
    vals = [c1_em, c3_em, c5_em]
    if any(pd.isna(v) for v in vals):
        return "MISSING_MODEL_EM"

    c1, c3, c5 = (int(c1_em), int(c3_em), int(c5_em))
    total = c1 + c3 + c5
    if total == 3:
        return "ALL_CORRECT"
    if total == 0:
        return "ALL_WRONG"
    if total == 1:
        if c1 == 1:
            return "C1_ONLY_RIGHT"
        if c3 == 1:
            return "C3_ONLY_RIGHT"
        return "C5_ONLY_RIGHT"
    if total == 2:
        if c1 == 0:
            return "C1_ONLY_WRONG"
        if c3 == 0:
            return "C3_ONLY_WRONG"
        return "C5_ONLY_WRONG"
    return "UNEXPECTED"


def combine_first_columns(df: pd.DataFrame, cols: List[str]) -> pd.Series:
    out = pd.Series([""] * len(df), index=df.index, dtype="object")
    for col in cols:
        if col not in df.columns:
            continue
        candidate = df[col].fillna("").astype(str).str.strip()
        out = np.where((pd.Series(out).astype(str).str.len() == 0) & (candidate.str.len() > 0), candidate, out)
        out = pd.Series(out, index=df.index)
    return out.astype(str)


def build_main_table(model_dfs: Dict[str, pd.DataFrame], meta_df: pd.DataFrame) -> pd.DataFrame:
    base = None
    for key in ["c1", "c3", "c5"]:
        if base is None:
            base = model_dfs[key]
        else:
            base = base.merge(model_dfs[key], on="id", how="outer")
    assert base is not None

    merged = base.merge(meta_df, on="id", how="left")

    merged["filename_fallback"] = combine_first_columns(
        merged,
        ["c1_filename", "c3_filename", "c5_filename", "meta_file_name"],
    )
    merged["table_id"] = merged["meta_table_id"].fillna("").astype(str).str.strip()
    merged["table_id_source"] = np.where(merged["table_id"].str.len() > 0, "jsonl_table_id", "filename_fallback")
    merged["table_id"] = np.where(merged["table_id"].str.len() > 0, merged["table_id"], merged["filename_fallback"])

    merged["subtype"] = merged["meta_subqtype"].fillna("").astype(str).str.strip()
    merged["subtype"] = np.where(merged["subtype"].str.len() > 0, merged["subtype"], merged["meta_question_type"].fillna(""))
    merged["subtype"] = pd.Series(merged["subtype"]).fillna("").astype(str).str.strip()
    merged["subtype"] = np.where(merged["subtype"].str.len() > 0, merged["subtype"], combine_first_columns(merged, ["c1_sub_type", "c3_sub_type", "c5_sub_type"]))

    merged["question"] = combine_first_columns(merged, ["meta_question", "c1_question", "c3_question", "c5_question"])
    merged["gold_answer"] = combine_first_columns(merged, ["meta_label", "c1_correct_answer", "c3_correct_answer", "c5_correct_answer"])

    for m in ["c1", "c3", "c5"]:
        merged[f"{m}_em"] = pd.to_numeric(merged[f"{m}_em"], errors="coerce")

    merged["pattern"] = merged.apply(lambda r: classify_pattern(r["c1_em"], r["c3_em"], r["c5_em"]), axis=1)
    merged["em_sum"] = merged[["c1_em", "c3_em", "c5_em"]].fillna(0).sum(axis=1)
    merged["has_all_model_em"] = merged[["c1_em", "c3_em", "c5_em"]].notna().all(axis=1)
    merged["is_disagreement"] = np.where(
        merged["has_all_model_em"],
        (merged["c1_em"] != merged["c3_em"]) | (merged["c1_em"] != merged["c5_em"]) | (merged["c3_em"] != merged["c5_em"]),
        False,
    )

    merged["all_wrong"] = merged["pattern"].eq("ALL_WRONG")
    merged["c1_only_right"] = merged["pattern"].eq("C1_ONLY_RIGHT")
    merged["c3_only_right"] = merged["pattern"].eq("C3_ONLY_RIGHT")
    merged["c5_only_right"] = merged["pattern"].eq("C5_ONLY_RIGHT")

    return merged


def summarize_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    grp = df.groupby(group_col, dropna=False)
    summary = grp.agg(
        n_questions=("id", "count"),
        c1_accuracy=("c1_em", "mean"),
        c3_accuracy=("c3_em", "mean"),
        c5_accuracy=("c5_em", "mean"),
        disagreement_rate=("is_disagreement", "mean"),
        all_wrong_rate=("all_wrong", "mean"),
        c1_only_right_count=("c1_only_right", "sum"),
        c3_only_right_count=("c3_only_right", "sum"),
        c5_only_right_count=("c5_only_right", "sum"),
    ).reset_index()

    summary["best_model_accuracy"] = summary[["c1_accuracy", "c3_accuracy", "c5_accuracy"]].max(axis=1)

    def best_model_label(row: pd.Series) -> str:
        vals = {"C1": row["c1_accuracy"], "C3": row["c3_accuracy"], "C5": row["c5_accuracy"]}
        max_val = max(vals.values())
        winners = [name for name, value in vals.items() if pd.notna(value) and abs(value - max_val) < 1e-12]
        return ",".join(winners) if winners else "N/A"

    summary["best_model"] = summary.apply(best_model_label, axis=1)
    summary["risk_score"] = (0.6 * summary["disagreement_rate"].fillna(0)) + (0.4 * summary["all_wrong_rate"].fillna(0))
    return summary.sort_values(["risk_score", "n_questions"], ascending=[False, False])


def save_csv(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")


def pct_text(v: float) -> str:
    if pd.isna(v):
        return "NA"
    return f"{100.0 * float(v):.2f}%"


def plot_model_accuracy(main_df: pd.DataFrame, out_path: Path) -> None:
    acc = {
        "C1": float(main_df["c1_em"].mean(skipna=True)),
        "C3": float(main_df["c3_em"].mean(skipna=True)),
        "C5": float(main_df["c5_em"].mean(skipna=True)),
    }
    labels = list(acc.keys())
    vals = [acc[k] for k in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, vals, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Exact Match")
    ax.set_title("Model Accuracy Comparison (EM)")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_pattern_stacked_by_subtype(main_df: pd.DataFrame, out_path: Path, top_n: int) -> None:
    data = main_df.copy()
    top_subtypes = data["subtype"].fillna("UNKNOWN").value_counts().head(top_n).index.tolist()
    data = data[data["subtype"].fillna("UNKNOWN").isin(top_subtypes)].copy()
    data["subtype"] = data["subtype"].replace("", "UNKNOWN")

    pattern_order = [
        "ALL_CORRECT",
        "ALL_WRONG",
        "C1_ONLY_RIGHT",
        "C3_ONLY_RIGHT",
        "C5_ONLY_RIGHT",
        "C1_ONLY_WRONG",
        "C3_ONLY_WRONG",
        "C5_ONLY_WRONG",
        "MISSING_MODEL_EM",
        "UNEXPECTED",
    ]

    pivot = (
        data.groupby(["subtype", "pattern"], dropna=False)["id"]
        .count()
        .reset_index(name="count")
        .pivot(index="subtype", columns="pattern", values="count")
        .fillna(0)
    )
    for p in pattern_order:
        if p not in pivot.columns:
            pivot[p] = 0
    pivot = pivot[pattern_order]
    pivot = pivot.div(pivot.sum(axis=1), axis=0).fillna(0)

    fig, ax = plt.subplots(figsize=(12, 7))
    bottom = np.zeros(len(pivot))
    colors = [
        "#4caf50",
        "#d32f2f",
        "#1976d2",
        "#f57c00",
        "#7b1fa2",
        "#64b5f6",
        "#ffb74d",
        "#ba68c8",
        "#9e9e9e",
        "#212121",
    ]
    x = np.arange(len(pivot.index))

    for idx, col in enumerate(pivot.columns):
        vals = pivot[col].to_numpy()
        ax.bar(x, vals, bottom=bottom, label=col, color=colors[idx % len(colors)], width=0.8)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(pivot.index, rotation=45, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Share")
    ax.set_title("Disagreement Pattern Distribution by Subtype (Top Volume)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_table_risk(by_table_df: pd.DataFrame, out_path: Path, top_n: int) -> None:
    top = by_table_df.head(top_n).copy()
    top = top.iloc[::-1]

    fig, ax = plt.subplots(figsize=(11, 8))
    ax.barh(top["table_id"], top["risk_score"], color="#b71c1c")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Risk Score (0.6 * disagreement_rate + 0.4 * all_wrong_rate)")
    ax.set_title("Top Table-Level Router Risk")
    for i, (_, row) in enumerate(top.iterrows()):
        ax.text(min(float(row["risk_score"]) + 0.01, 0.99), i, pct_text(row["risk_score"]), va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_subtype_heatmap(by_subtype_df: pd.DataFrame, out_path: Path, top_n: int) -> None:
    heat = by_subtype_df.head(top_n).copy()
    if heat.empty:
        return

    matrix = heat[["c1_accuracy", "c3_accuracy", "c5_accuracy"]].fillna(0).to_numpy()
    rows = heat["subtype"].tolist()
    cols = ["C1", "C3", "C5"]

    fig, ax = plt.subplots(figsize=(8, max(4, 0.5 * len(rows))))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_title("Subtype Accuracy Heatmap (Top Risk Subtypes)")

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", color="black", fontsize=8)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Accuracy")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_disagreement_vs_accuracy(by_table_df: pd.DataFrame, out_path: Path, top_n: int) -> None:
    scatter_df = by_table_df.head(top_n).copy()
    if scatter_df.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    x = scatter_df["disagreement_rate"].fillna(0)
    y = scatter_df["best_model_accuracy"].fillna(0)
    sizes = 40 + (scatter_df["n_questions"].fillna(0) * 2)
    ax.scatter(x, y, s=sizes, alpha=0.7, c="#1565c0")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Disagreement Rate")
    ax.set_ylabel("Best Model Accuracy")
    ax.set_title("Table-Level Disagreement vs Best Accuracy (Top Risk)")
    for _, row in scatter_df.head(12).iterrows():
        ax.annotate(str(row["table_id"]), (row["disagreement_rate"], row["best_model_accuracy"]), fontsize=7, alpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def write_markdown_summary(
    out_md: Path,
    main_df: pd.DataFrame,
    by_table_df: pd.DataFrame,
    by_subtype_df: pd.DataFrame,
    load_stats: List[LoadStats],
    chart_paths: Dict[str, Path],
) -> None:
    total_rows = len(main_df)
    disagreements = int(main_df["is_disagreement"].sum())
    all_wrong = int(main_df["all_wrong"].sum())
    fallback_rows = int((main_df["table_id_source"] == "filename_fallback").sum())
    missing_meta_rows = int(main_df["meta_table_id"].fillna("").astype(str).str.strip().eq("").sum())

    overall_acc = {
        "C1": float(main_df["c1_em"].mean(skipna=True)),
        "C3": float(main_df["c3_em"].mean(skipna=True)),
        "C5": float(main_df["c5_em"].mean(skipna=True)),
    }

    top_tables = by_table_df.head(10)
    top_subtypes = by_subtype_df.head(10)

    lines = []
    lines.append("# Router EDA Executive Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Dataset Coverage")
    lines.append("")
    lines.append(f"- Total rows in merged comparison: {total_rows}")
    lines.append(f"- Disagreement rows: {disagreements} ({pct_text(disagreements / total_rows if total_rows else np.nan)})")
    lines.append(f"- All-wrong rows: {all_wrong} ({pct_text(all_wrong / total_rows if total_rows else np.nan)})")
    lines.append(f"- Rows using filename fallback instead of JSONL table_id: {fallback_rows}")
    lines.append(f"- Rows missing JSONL table_id metadata: {missing_meta_rows}")
    lines.append("")
    lines.append("## Load Diagnostics")
    lines.append("")
    for st in load_stats:
        lines.append(
            f"- {st.name}: raw={st.rows_raw}, deduped={st.rows_deduped}, duplicates_removed={st.duplicates_removed}"
        )
    lines.append("")
    lines.append("## Overall EM Accuracy")
    lines.append("")
    lines.append(f"- C1: {pct_text(overall_acc['C1'])}")
    lines.append(f"- C3: {pct_text(overall_acc['C3'])}")
    lines.append(f"- C5: {pct_text(overall_acc['C5'])}")
    lines.append("")
    lines.append("## Top Table Risk (Router Focus)")
    lines.append("")
    for _, row in top_tables.iterrows():
        lines.append(
            "- "
            f"{row['table_id']}: risk={pct_text(row['risk_score'])}, "
            f"disagreement={pct_text(row['disagreement_rate'])}, "
            f"all_wrong={pct_text(row['all_wrong_rate'])}, "
            f"best_model={row['best_model']}"
        )
    lines.append("")
    lines.append("## Top Subtype Risk (Router Focus)")
    lines.append("")
    for _, row in top_subtypes.iterrows():
        lines.append(
            "- "
            f"{row['subtype']}: risk={pct_text(row['risk_score'])}, "
            f"disagreement={pct_text(row['disagreement_rate'])}, "
            f"all_wrong={pct_text(row['all_wrong_rate'])}, "
            f"best_model={row['best_model']}"
        )
    lines.append("")
    lines.append("## Chart Index")
    lines.append("")
    for title, path in chart_paths.items():
        lines.append(f"- {title}: {path.as_posix()}")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    base_dir = Path(args.base_dir).resolve()
    output_dir = (base_dir / args.output_dir).resolve()
    charts_dir = output_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    model_dfs: Dict[str, pd.DataFrame] = {}
    stats: List[LoadStats] = []
    for _, key, rel_path in MODEL_SPECS:
        df, st = load_minimax_model(base_dir, key, rel_path)
        model_dfs[key] = df
        stats.append(st)

    meta_df, meta_stats = load_jsonl_metadata(base_dir, args.jsonl_path)
    stats.append(meta_stats)

    main_df = build_main_table(model_dfs, meta_df)
    main_df = main_df.sort_values("id").reset_index(drop=True)

    by_table_df = summarize_group(main_df, "table_id").rename(columns={"table_id": "table_id"})
    by_subtype_df = summarize_group(main_df.rename(columns={"subtype": "group_subtype"}), "group_subtype").rename(
        columns={"group_subtype": "subtype"}
    )

    main_cols = [
        "id",
        "table_id",
        "table_id_source",
        "subtype",
        "meta_question_type",
        "meta_source",
        "meta_structure",
        "question",
        "gold_answer",
        "c1_model_answer",
        "c3_model_answer",
        "c5_model_answer",
        "c1_em",
        "c3_em",
        "c5_em",
        "em_sum",
        "pattern",
        "is_disagreement",
        "all_wrong",
    ]
    main_out = main_df[main_cols].copy()

    disagreement_only = main_out[main_out["is_disagreement"]].copy()

    main_csv = output_dir / "router_main_comparison.csv"
    by_table_csv = output_dir / "router_by_table_summary.csv"
    by_subtype_csv = output_dir / "router_by_subtype_summary.csv"
    disagreement_csv = output_dir / "router_disagreement_only.csv"
    summary_md = output_dir / "router_executive_summary.md"

    save_csv(main_out, main_csv)
    save_csv(by_table_df, by_table_csv)
    save_csv(by_subtype_df, by_subtype_csv)
    save_csv(disagreement_only, disagreement_csv)

    chart_paths = {
        "Model Accuracy": charts_dir / "model_accuracy_comparison.png",
        "Pattern Distribution by Subtype": charts_dir / "pattern_distribution_by_subtype.png",
        "Top Table Router Risk": charts_dir / "table_router_risk_top.png",
        "Subtype Accuracy Heatmap": charts_dir / "subtype_accuracy_heatmap.png",
        "Disagreement vs Best Accuracy": charts_dir / "disagreement_vs_best_accuracy.png",
    }

    plot_model_accuracy(main_df, chart_paths["Model Accuracy"])
    plot_pattern_stacked_by_subtype(main_df, chart_paths["Pattern Distribution by Subtype"], args.top_n)
    plot_table_risk(by_table_df, chart_paths["Top Table Router Risk"], args.top_n)
    plot_subtype_heatmap(by_subtype_df, chart_paths["Subtype Accuracy Heatmap"], args.top_n)
    plot_disagreement_vs_accuracy(by_table_df, chart_paths["Disagreement vs Best Accuracy"], args.top_n)

    write_markdown_summary(summary_md, main_df, by_table_df, by_subtype_df, stats, chart_paths)

    print("Router EDA completed")
    print(f"Output directory: {output_dir}")
    print(f"Main CSV: {main_csv}")
    print(f"By-table CSV: {by_table_csv}")
    print(f"By-subtype CSV: {by_subtype_csv}")
    print(f"Disagreement CSV: {disagreement_csv}")
    print(f"Summary: {summary_md}")


if __name__ == "__main__":
    main()