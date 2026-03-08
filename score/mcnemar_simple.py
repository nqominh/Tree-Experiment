#!/usr/bin/env python3
"""McNemar Test comparing Accurate columns from two separate score CSVs.

Usage:
    python mcnemar_simple.py [baseline.csv] [improved.csv]

Defaults:
    baseline = "gemini-3.1 - non-processed evidence gemini 3.csv"
    improved = "gemini-3.1 - processed evidence prompt gemini 3.csv"
"""

import csv
import sys
import os
import numpy as np
from scipy import stats

# ── Defaults ──────────────────────────────────────────────────────────
DEFAULT_BASELINE = "gemini-3.1 - non-processed evidence gemini 3.csv"
DEFAULT_IMPROVED = "gemini-3.1 - processed evidence prompt gemini 3.csv"


def to_binary(val: str) -> int:
    """Map TRUE/FALSE/1/0/FUZZY → 1 or 0."""
    v = str(val).strip().upper()
    if v in ("TRUE", "1", "FUZZY"):
        return 1
    return 0


def load_csv(path: str):
    """Load a CSV, skip junk preamble lines, return {id: binary_accurate}."""
    records = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        # Find the real header (first line that starts with "id,")
        for raw_line in f:
            if raw_line.lstrip("\ufeff").strip().lower().startswith("id,"):
                header_line = raw_line
                break
        else:
            sys.exit(f"ERROR: could not find header row starting with 'id,' in {path}")

        # Re-read remainder with csv.DictReader using that header
        reader = csv.DictReader([header_line] + f.readlines())
        for row in reader:
            qid = row["id"].strip()
            records[qid] = to_binary(row["Accurate"])
    return records


def main():
    baseline_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASELINE
    improved_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_IMPROVED

    for p in (baseline_path, improved_path):
        if not os.path.isfile(p):
            sys.exit(f"File not found: {p}")

    base = load_csv(baseline_path)
    impr = load_csv(improved_path)

    shared_ids = sorted(set(base) & set(impr), key=lambda x: int(x))
    print(f"Baseline rows: {len(base)}  |  Improved rows: {len(impr)}")
    print(f"Shared IDs:    {len(shared_ids)}\n")

    if not shared_ids:
        sys.exit("No shared IDs — cannot compare.")

    em_baseline = np.array([base[i] for i in shared_ids])
    em_improved = np.array([impr[i] for i in shared_ids])
    n = len(shared_ids)

    # EM rates
    em_rate_base = np.mean(em_baseline)
    em_rate_impr = np.mean(em_improved)

    print(f"EM Rate (Baseline):  {em_rate_base:.4f} ({em_baseline.sum()}/{n})")
    print(f"EM Rate (Improved):  {em_rate_impr:.4f} ({em_improved.sum()}/{n})")
    print(f"Delta EM:            {em_rate_impr - em_rate_base:+.4f}\n")

    # Discordant pairs
    n01 = int(np.sum((em_baseline == 0) & (em_improved == 1)))
    n10 = int(np.sum((em_baseline == 1) & (em_improved == 0)))
    n_discordant = n01 + n10

    print("Discordant Pairs:")
    print(f"  n01 (baseline=0, improved=1): {n01}")
    print(f"  n10 (baseline=1, improved=0): {n10}")
    print(f"  Total discordant:             {n_discordant}\n")

    # McNemar test
    if n_discordant == 0:
        print("McNemar not applicable; outputs identical on EM.")
        return

    # Exact binomial test (two-sided)
    result = stats.binomtest(min(n01, n10), n_discordant, 0.5,
                             alternative="two-sided")
    print(f"McNemar Test (exact binomial, two-sided):")
    print(f"  p-value: {result.pvalue:.6f}")

    # Chi-square with continuity correction
    chi2 = (abs(n01 - n10) - 1) ** 2 / n_discordant
    chi2_p = 1 - stats.chi2.cdf(chi2, df=1)
    print(f"\nMcNemar (chi-square, continuity corrected):")
    print(f"  statistic: {chi2:.4f}, p-value: {chi2_p:.6f}")

    # Conclusion
    alpha = 0.05
    print(f"\nConclusion (alpha={alpha}):")
    if result.pvalue < alpha:
        if n01 > n10:
            print(f"  Improved is SIGNIFICANTLY BETTER (p={result.pvalue:.4f})")
        else:
            print(f"  Improved is SIGNIFICANTLY WORSE (p={result.pvalue:.4f})")
    else:
        print(f"  No significant difference (p={result.pvalue:.4f})")


if __name__ == "__main__":
    main()
