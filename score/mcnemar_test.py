#!/usr/bin/env python3
"""
McNemar Test Script for Comparing Exact Match (EM) Between Two Model Runs

This script performs a paired McNemar test to compare EM between baseline
and improved model runs on the same questions.
"""

import argparse
import json
import re
import sys
import warnings
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats


def normalize_string(s: str) -> str:
    """
    Normalize a string for exact match comparison.
    
    Steps:
    - lowercase
    - remove commas inside numbers
    - remove percent signs
    - normalize unicode dashes to ASCII dash
    - canonicalize numbers
    """
    if pd.isna(s):
        return ""
    
    s = str(s).strip().lower()
    
    # Remove commas inside numbers (e.g., 101,529 -> 101529)
    s = re.sub(r'(\d),(\d)', r'\1\2', s)
    
    # Remove percent signs
    s = s.replace('%', '')
    
    # Normalize unicode dashes to ASCII dash
    s = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]', '-', s)
    
    # Strip again after removals
    s = s.strip()
    
    # Try to canonicalize as a number
    try:
        d = Decimal(s)
        # Normalize to remove trailing zeros: 543.00 -> 543, 6.60 -> 6.6
        s = str(d.normalize())
    except InvalidOperation:
        pass  # Not a number, keep as-is
    
    return s


def extract_prediction(model_answer: str) -> str:
    """
    Extract a clean final prediction from model_answer.
    
    Priority:
    1. Content after markers like 'Final Answer:' or '[Final Answer]:'
    2. First non-empty line before sections like '# Thought', 'Thought', '# Solution', or code fences
    """
    if pd.isna(model_answer):
        return ""
    
    text = str(model_answer).strip()
    
    # Check for 'Final Answer:' markers (case-insensitive)
    final_answer_patterns = [
        r'\[?\s*final\s*answer\s*\]?\s*[:\-]\s*(.+)',
        r'final\s*answer\s*[:\-]\s*(.+)',
    ]
    
    for pattern in final_answer_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            # Take only the first line of the answer
            first_line = answer.split('\n')[0].strip()
            if first_line:
                return first_line
    
    # Otherwise, find first non-empty line before special sections
    stop_patterns = [
        r'^#\s*thought',
        r'^thought\s*:',
        r'^#\s*solution',
        r'^```',
    ]
    
    lines = text.split('\n')
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if this line starts a section we should stop at
        should_stop = False
        for pattern in stop_patterns:
            if re.match(pattern, line_stripped, re.IGNORECASE):
                should_stop = True
                break
        
        if should_stop:
            break
        
        return line_stripped
    
    return text.split('\n')[0].strip() if text else ""


def compute_em(gold: str, pred: str) -> int:
    """Compute Exact Match: 1 if normalized pred == normalized gold, else 0."""
    pred_extracted = extract_prediction(pred)
    norm_gold = normalize_string(gold)
    norm_pred = normalize_string(pred_extracted)
    return 1 if norm_gold == norm_pred else 0


def load_and_prepare(
    filepath: str,
    key_col: str,
    em_col: Optional[str],
    gold_col: str,
    pred_col: str
) -> Tuple[pd.DataFrame, bool]:
    """
    Load a CSV file and prepare it for comparison.
    
    Returns:
        Tuple of (DataFrame with key_col and em column, whether EM was pre-computed)
    """
    df = pd.read_csv(filepath)
    
    if key_col not in df.columns:
        raise ValueError(f"Key column '{key_col}' not found in {filepath}. "
                        f"Available columns: {list(df.columns)}")
    
    # Check for duplicates
    duplicates = df[key_col].duplicated()
    if duplicates.any():
        n_dups = duplicates.sum()
        warnings.warn(f"Found {n_dups} duplicate '{key_col}' values in {filepath}. "
                     f"Keeping first occurrence only.")
        df = df.drop_duplicates(subset=[key_col], keep='first')
    
    # Check if EM column exists
    has_em = em_col in df.columns if em_col else False
    
    if has_em:
        # Format A: already scored
        df = df[[key_col, em_col]].copy()
        df = df.rename(columns={em_col: 'em'})
        df['em'] = df['em'].astype(int)
        return df, True
    else:
        # Format B: need to compute EM from gold/pred
        if gold_col not in df.columns:
            raise ValueError(f"Gold column '{gold_col}' not found in {filepath}. "
                           f"Available columns: {list(df.columns)}")
        if pred_col not in df.columns:
            raise ValueError(f"Prediction column '{pred_col}' not found in {filepath}. "
                           f"Available columns: {list(df.columns)}")
        
        df = df[[key_col, gold_col, pred_col]].copy()
        df['em'] = df.apply(lambda row: compute_em(row[gold_col], row[pred_col]), axis=1)
        return df[[key_col, 'em']], False


def compute_em_if_needed(
    df: pd.DataFrame,
    gold_col: str,
    pred_col: str
) -> pd.DataFrame:
    """Compute EM column if not already present."""
    if 'em' not in df.columns:
        df['em'] = df.apply(lambda row: compute_em(row[gold_col], row[pred_col]), axis=1)
    return df


def mcnemar_exact(
    em_baseline: np.ndarray,
    em_improved: np.ndarray,
    alternative: str = 'two-sided'
) -> dict:
    """
    Perform exact McNemar test using binomial test on discordant pairs.
    
    Args:
        em_baseline: Array of EM scores (0/1) for baseline
        em_improved: Array of EM scores (0/1) for improved
        alternative: 'two-sided', 'greater' (improved better), or 'less'
    
    Returns:
        Dictionary with test results
    """
    # Count discordant pairs
    n01 = np.sum((em_baseline == 0) & (em_improved == 1))  # baseline wrong, improved right
    n10 = np.sum((em_baseline == 1) & (em_improved == 0))  # baseline right, improved wrong
    n00 = np.sum((em_baseline == 0) & (em_improved == 0))  # both wrong
    n11 = np.sum((em_baseline == 1) & (em_improved == 1))  # both right
    
    n_discordant = n01 + n10
    
    result = {
        'n01': int(n01),
        'n10': int(n10),
        'n00': int(n00),
        'n11': int(n11),
        'n_discordant': int(n_discordant),
        'alternative': alternative,
    }
    
    if n_discordant == 0:
        result['p_value'] = None
        result['applicable'] = False
        result['message'] = "McNemar not applicable; outputs identical on EM."
        return result
    
    # Map alternative for binomtest
    # For 'greater' (improved better): we want to test if n01 > n10
    # binomtest tests if successes > expected, so we count n01 as "successes"
    if alternative == 'greater':
        # Test if improved is better: H1: P(n01) > 0.5
        binom_alt = 'greater'
        successes = n01
    elif alternative == 'less':
        # Test if improved is worse: H1: P(n01) < 0.5
        binom_alt = 'less'
        successes = n01
    else:  # two-sided
        binom_alt = 'two-sided'
        successes = min(n01, n10)
    
    # Exact binomial test
    binom_result = stats.binomtest(successes, n_discordant, 0.5, alternative=binom_alt)
    result['p_value'] = float(binom_result.pvalue)
    result['applicable'] = True
    
    # Also compute chi-square McNemar with continuity correction (for reference)
    if n_discordant > 0:
        chi2_stat = (abs(n01 - n10) - 1) ** 2 / (n01 + n10)
        chi2_pvalue = 1 - stats.chi2.cdf(chi2_stat, df=1)
        result['chi2_statistic'] = float(chi2_stat)
        result['chi2_pvalue'] = float(chi2_pvalue)
    
    return result


def run_mcnemar_test(args: argparse.Namespace) -> dict:
    """Main function to run the McNemar test."""
    
    print("=" * 60)
    print("McNemar Test: Comparing EM Between Baseline and Improved")
    print("=" * 60)
    print()
    
    # Load baseline
    print(f"Loading baseline: {args.baseline}")
    df_baseline, baseline_has_em = load_and_prepare(
        args.baseline, args.key_col, args.em_col, args.gold_col, args.pred_col
    )
    n_baseline = len(df_baseline)
    print(f"  Rows loaded: {n_baseline}")
    print(f"  EM pre-computed: {baseline_has_em}")
    
    # Load improved
    print(f"\nLoading improved: {args.improved}")
    df_improved, improved_has_em = load_and_prepare(
        args.improved, args.key_col, args.em_col, args.gold_col, args.pred_col
    )
    n_improved = len(df_improved)
    print(f"  Rows loaded: {n_improved}")
    print(f"  EM pre-computed: {improved_has_em}")
    
    # Merge on key column
    print(f"\nMerging on '{args.key_col}'...")
    df_merged = pd.merge(
        df_baseline, 
        df_improved, 
        on=args.key_col, 
        suffixes=('_baseline', '_improved'),
        how='inner'
    )
    n_merged = len(df_merged)
    
    # Report dropped rows
    n_dropped_baseline = n_baseline - n_merged
    n_dropped_improved = n_improved - n_merged
    
    print(f"  Merged rows: {n_merged}")
    if n_dropped_baseline > 0:
        print(f"  Dropped from baseline (no match in improved): {n_dropped_baseline}")
    if n_dropped_improved > 0:
        print(f"  Dropped from improved (no match in baseline): {n_dropped_improved}")
    
    if n_merged == 0:
        raise ValueError("No matching rows found between baseline and improved files. "
                        f"Check that '{args.key_col}' values match.")
    
    # Extract EM arrays
    em_baseline = df_merged['em_baseline'].values
    em_improved = df_merged['em_improved'].values
    
    # Compute EM rates
    em_rate_baseline = float(np.mean(em_baseline))
    em_rate_improved = float(np.mean(em_improved))
    delta_em = em_rate_improved - em_rate_baseline
    
    print()
    print("-" * 60)
    print("RESULTS")
    print("-" * 60)
    print()
    print(f"EM Rate (Baseline):  {em_rate_baseline:.4f} ({int(np.sum(em_baseline))}/{n_merged})")
    print(f"EM Rate (Improved):  {em_rate_improved:.4f} ({int(np.sum(em_improved))}/{n_merged})")
    print(f"Delta EM:            {delta_em:+.4f}")
    print()
    
    # Run McNemar test
    mcnemar_result = mcnemar_exact(em_baseline, em_improved, args.alternative)
    
    print("Discordant Pairs:")
    print(f"  n01 (baseline=0, improved=1): {mcnemar_result['n01']}")
    print(f"  n10 (baseline=1, improved=0): {mcnemar_result['n10']}")
    print(f"  Total discordant:             {mcnemar_result['n_discordant']}")
    print()
    
    if not mcnemar_result['applicable']:
        print(f"⚠️  {mcnemar_result['message']}")
        conclusion = "Not applicable"
    else:
        print(f"McNemar Test (exact binomial):")
        print(f"  Alternative:  {mcnemar_result['alternative']}")
        print(f"  p-value:      {mcnemar_result['p_value']:.6f}")
        
        if 'chi2_statistic' in mcnemar_result:
            print(f"\nMcNemar Test (chi-square with continuity correction):")
            print(f"  Chi-square statistic: {mcnemar_result['chi2_statistic']:.4f}")
            print(f"  p-value:              {mcnemar_result['chi2_pvalue']:.6f}")
        
        print()
        
        # Interpretation
        is_significant = mcnemar_result['p_value'] < args.alpha
        
        if is_significant:
            if args.alternative == 'two-sided':
                if mcnemar_result['n01'] > mcnemar_result['n10']:
                    conclusion = f"✅ Improved is SIGNIFICANTLY BETTER than baseline (p={mcnemar_result['p_value']:.4f} < α={args.alpha})"
                else:
                    conclusion = f"❌ Improved is SIGNIFICANTLY WORSE than baseline (p={mcnemar_result['p_value']:.4f} < α={args.alpha})"
            elif args.alternative == 'greater':
                conclusion = f"✅ Improved is SIGNIFICANTLY BETTER than baseline (p={mcnemar_result['p_value']:.4f} < α={args.alpha})"
            else:
                conclusion = f"❌ Improved is SIGNIFICANTLY WORSE than baseline (p={mcnemar_result['p_value']:.4f} < α={args.alpha})"
        else:
            conclusion = f"➖ No significant difference detected (p={mcnemar_result['p_value']:.4f} ≥ α={args.alpha})"
        
        print("CONCLUSION:")
        print(f"  {conclusion}")
    
    print()
    print("=" * 60)
    
    # Prepare results dictionary
    results = {
        'baseline_file': args.baseline,
        'improved_file': args.improved,
        'n_baseline': n_baseline,
        'n_improved': n_improved,
        'n_merged': n_merged,
        'n_dropped_baseline': n_dropped_baseline,
        'n_dropped_improved': n_dropped_improved,
        'em_rate_baseline': em_rate_baseline,
        'em_rate_improved': em_rate_improved,
        'delta_em': delta_em,
        'n01': mcnemar_result['n01'],
        'n10': mcnemar_result['n10'],
        'n00': mcnemar_result['n00'],
        'n11': mcnemar_result['n11'],
        'n_discordant': mcnemar_result['n_discordant'],
        'alternative': mcnemar_result['alternative'],
        'alpha': args.alpha,
        'p_value': mcnemar_result.get('p_value'),
        'applicable': mcnemar_result['applicable'],
        'conclusion': conclusion,
    }
    
    if 'chi2_statistic' in mcnemar_result:
        results['chi2_statistic'] = mcnemar_result['chi2_statistic']
        results['chi2_pvalue'] = mcnemar_result['chi2_pvalue']
    
    # Save JSON if requested
    if args.out_json:
        with open(args.out_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {args.out_json}")
    
    # Save merged CSV if requested
    if args.out_merged:
        df_merged.to_csv(args.out_merged, index=False)
        print(f"Merged data saved to: {args.out_merged}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run paired McNemar test to compare Exact Match (EM) between two model runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with Format A (pre-scored EM):
  python mcnemar_test.py --baseline baseline.csv --improved improved.csv

  # With Format B (raw answers):
  python mcnemar_test.py --baseline baseline.csv --improved improved.csv \\
      --gold_col correct_answer --pred_col model_answer

  # One-sided test (improved better):
  python mcnemar_test.py --baseline baseline.csv --improved improved.csv \\
      --alternative greater

  # Save outputs:
  python mcnemar_test.py --baseline baseline.csv --improved improved.csv \\
      --out_json results.json --out_merged merged.csv
        """
    )
    
    # Required arguments
    parser.add_argument('--baseline', required=True, help='Path to baseline CSV file')
    parser.add_argument('--improved', required=True, help='Path to improved CSV file')
    
    # Key column
    parser.add_argument('--key_col', default='id', 
                       help='Column name for pairing rows (default: id)')
    
    # Format A: pre-scored EM
    parser.add_argument('--em_col', default='em',
                       help='Column name for EM scores if pre-computed (default: em)')
    
    # Format B: raw answers
    parser.add_argument('--gold_col', default='correct_answer',
                       help='Column name for gold/correct answers (default: correct_answer)')
    parser.add_argument('--pred_col', default='model_answer',
                       help='Column name for model predictions (default: model_answer)')
    
    # Test parameters
    parser.add_argument('--alternative', choices=['two-sided', 'greater', 'less'],
                       default='two-sided',
                       help='Alternative hypothesis (default: two-sided). '
                            '"greater" tests if improved is better.')
    parser.add_argument('--alpha', type=float, default=0.05,
                       help='Significance level (default: 0.05)')
    
    # Output options
    parser.add_argument('--out_json', help='Path to save results as JSON')
    parser.add_argument('--out_merged', help='Path to save merged data as CSV')
    
    args = parser.parse_args()
    
    try:
        run_mcnemar_test(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
