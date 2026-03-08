"""
EDA: Numerical Reasoning Question Type from QA_final.json
- Overall subtype distribution
- Subtype distribution by batch (every 100 questions)
"""

import json
import math
from collections import Counter, defaultdict

# Load data
with open("RealHiTBench/QA_final.json", "r", encoding="utf-8") as f:
    data = json.load(f)

queries = data["queries"]

# Filter Numerical Reasoning
nr_questions = [q for q in queries if q["QuestionType"] == "Numerical Reasoning"]
print(f"Total questions in dataset: {len(queries)}")
print(f"Numerical Reasoning questions: {len(nr_questions)} ({len(nr_questions)/len(queries)*100:.1f}%)")
print()

# --- Overall subtype distribution ---
subtypes = Counter(q["SubQType"] for q in nr_questions)
print("=" * 70)
print("OVERALL SUBTYPE DISTRIBUTION")
print("=" * 70)
print(f"{'SubQType':<35} {'Count':>6} {'Percentage':>10}")
print("-" * 55)
for subtype, count in subtypes.most_common():
    pct = count / len(nr_questions) * 100
    print(f"{subtype:<35} {count:>6} {pct:>9.1f}%")
print(f"{'TOTAL':<35} {len(nr_questions):>6} {'100.0%':>10}")
print()

# --- Distribution by batch (every 100 questions) ---
# Sort by id
nr_sorted = sorted(nr_questions, key=lambda q: q["id"])
all_subtypes = sorted(subtypes.keys())

num_batches = math.ceil(len(nr_sorted) / 100)
print("=" * 100)
print(f"SUBTYPE DISTRIBUTION BY BATCH (each batch = 100 Numerical Reasoning Qs)")
print(f"Total batches: {num_batches} (last batch has {len(nr_sorted) - (num_batches-1)*100} questions)")
print("=" * 100)

# Header
header = f"{'Batch':<12} {'Size':>4}"
for st in all_subtypes:
    # Abbreviate long names
    short = st[:18] if len(st) > 18 else st
    header += f" {short:>18}"
print(header)
print("-" * len(header))

batch_data = []
for i in range(num_batches):
    batch = nr_sorted[i * 100 : (i + 1) * 100]
    batch_subtypes = Counter(q["SubQType"] for q in batch)
    batch_size = len(batch)

    id_range = f"{batch[0]['id']}-{batch[-1]['id']}"
    row = f"B{i+1} ({id_range})" 
    row = f"{row:<12} {batch_size:>4}"
    for st in all_subtypes:
        count = batch_subtypes.get(st, 0)
        pct = count / batch_size * 100
        row += f" {count:>3} ({pct:>5.1f}%)"
    print(row)
    batch_data.append((i + 1, id_range, batch_size, batch_subtypes))

print()

# --- Detailed batch breakdown ---
print("=" * 70)
print("DETAILED BATCH BREAKDOWN")
print("=" * 70)
for batch_num, id_range, batch_size, batch_subtypes in batch_data:
    print(f"\nBatch {batch_num} (IDs {id_range}, n={batch_size})")
    print(f"  {'SubQType':<35} {'Count':>6} {'Percentage':>10}")
    print(f"  {'-'*53}")
    for st in all_subtypes:
        count = batch_subtypes.get(st, 0)
        pct = count / batch_size * 100
        bar = "█" * int(pct / 2)
        print(f"  {st:<35} {count:>6} {pct:>9.1f}% {bar}")

print()
print("=" * 70)
print("ID RANGE INFO")
print("=" * 70)
print(f"First NR question ID: {nr_sorted[0]['id']}")
print(f"Last  NR question ID: {nr_sorted[-1]['id']}")
print(f"ID range spans: {nr_sorted[0]['id']} to {nr_sorted[-1]['id']}")

# --- Visualization ---
import matplotlib.pyplot as plt
import numpy as np

# Data for plot
batches = [f"B{b[0]}\n({b[2]} Qs)" for b in batch_data]
subtype_names = all_subtypes

# Create a matrix of counts
counts_matrix = {st: [] for st in subtype_names}
for batch_num, id_range, batch_size, batch_subtypes in batch_data:
    for st in subtype_names:
        counts_matrix[st].append(batch_subtypes.get(st, 0))

fig, ax = plt.subplots(figsize=(12, 7))
bottom = np.zeros(len(batches))

# Colors from a colormap
colors = plt.cm.tab10(np.linspace(0, 1, len(subtype_names)))

for i, st in enumerate(subtype_names):
    counts = np.array(counts_matrix[st])
    ax.bar(batches, counts, label=st, bottom=bottom, color=colors[i], edgecolor='white', width=0.7)
    
    # Add text annotations for counts > 5
    for j, count in enumerate(counts):
        if count > 5:
            ax.text(j, bottom[j] + count/2, str(count), ha='center', va='center', color='white', fontweight='bold', fontsize=9)
            
    bottom += counts

ax.set_title('Numerical Reasoning Subtypes by Batch', fontsize=14, pad=15)
ax.set_xlabel('Batch (100 questions per batch initially)', fontsize=12)
ax.set_ylabel('Number of Questions', fontsize=12)

# Adjust legend and layout
ax.legend(title='SubQType', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

# Save the plot
plt.savefig('subtype_distribution.png', dpi=300, bbox_inches='tight')
print("\nVisualization saved to 'subtype_distribution.png'")
