#!/usr/bin/env python3
"""Simple McNemar Test for pre-scored merged CSV."""

import pandas as pd
import numpy as np
from scipy import stats

# Load data
df = pd.read_csv('merged copy.csv')
print(f"Loaded {len(df)} rows\n")

# Convert em_baseline: TRUE=1, FALSE=0, fuzzy=1 (treating as correct)
def to_binary(val):
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return int(val) if not pd.isna(val) else 0
    val_str = str(val).strip().upper()
    if val_str == 'TRUE' or val_str == '1' or val_str == 'FUZZY':
        return 1
    return 0  # FALSE or anything else = 0

df['em_base'] = df['em_baseline'].apply(to_binary)
df['em_impr'] = df['em_improved'].apply(to_binary)

em_baseline = df['em_base'].values
em_improved = df['em_impr'].values

# EM rates
em_rate_base = np.mean(em_baseline)
em_rate_impr = np.mean(em_improved)

print(f"EM Rate (Baseline):  {em_rate_base:.4f} ({em_baseline.sum()}/{len(df)})")
print(f"EM Rate (Improved):  {em_rate_impr:.4f} ({em_improved.sum()}/{len(df)})")
print(f"Delta EM:            {em_rate_impr - em_rate_base:+.4f}\n")

# Discordant pairs
n01 = np.sum((em_baseline == 0) & (em_improved == 1))  # baseline wrong, improved right
n10 = np.sum((em_baseline == 1) & (em_improved == 0))  # baseline right, improved wrong
n_discordant = n01 + n10

print(f"Discordant Pairs:")
print(f"  n01 (baseline=0, improved=1): {n01}")
print(f"  n10 (baseline=1, improved=0): {n10}")
print(f"  Total discordant:             {n_discordant}\n")

# McNemar test
if n_discordant == 0:
    print("McNemar not applicable; outputs identical on EM.")
else:
    # Exact binomial test (two-sided)
    result = stats.binomtest(min(n01, n10), n_discordant, 0.5, alternative='two-sided')
    print(f"McNemar Test (exact binomial, two-sided):")
    print(f"  p-value: {result.pvalue:.6f}")
    
    # Chi-square with continuity correction
    chi2 = (abs(n01 - n10) - 1) ** 2 / (n01 + n10)
    chi2_p = 1 - stats.chi2.cdf(chi2, df=1)
    print(f"\nMcNemar (chi-square, continuity corrected):")
    print(f"  statistic: {chi2:.4f}, p-value: {chi2_p:.6f}")
    
    # Conclusion
    alpha = 0.05
    print(f"\nConclusion (α={alpha}):")
    if result.pvalue < alpha:
        if n01 > n10:
            print(f"  ✅ Improved is SIGNIFICANTLY BETTER (p={result.pvalue:.4f})")
        else:
            print(f"  ❌ Improved is SIGNIFICANTLY WORSE (p={result.pvalue:.4f})")
    else:
        print(f"  ➖ No significant difference (p={result.pvalue:.4f})")
