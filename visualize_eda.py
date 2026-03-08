"""
Visualize Numerical Reasoning Subtype Distribution
- Pie chart: overall distribution
- Stacked bar chart: distribution by batch (100 NR questions each)
"""

import matplotlib.pyplot as plt
import numpy as np

# --- Data (from EDA) ---
subtypes = ["Calculation", "Comparison", "Counting", "Multi-hop NR", "Ranking"]
overall_counts = [256, 127, 205, 78, 105]

batch_labels = ["B1\n(20-365)", "B2\n(366-729)", "B3\n(735-1032)", "B4\n(1036-1259)",
                "B5\n(1260-1664)", "B6\n(1665-2062)", "B7\n(2063-2430)", "B8\n(2431-2669)"]
batch_sizes = [100, 100, 100, 100, 100, 100, 100, 71]

# Counts per subtype per batch (rows=subtypes, cols=batches)
counts = {
    "Calculation":  [41, 28, 12, 21, 50, 42, 33, 29],
    "Comparison":   [22, 28, 19, 18,  0, 17, 16,  7],
    "Counting":     [10, 16, 37, 32, 43, 26, 24, 17],
    "Multi-hop NR": [10, 11,  6, 11,  7,  6, 15, 12],
    "Ranking":      [17, 17, 26, 18,  0,  9, 12,  6],
}

colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]

# --- Figure with 2 subplots ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [1, 2]})

# 1) Pie chart — overall distribution
wedges, texts, autotexts = ax1.pie(
    overall_counts, labels=subtypes, autopct=lambda p: f"{p:.1f}%\n({int(round(p*771/100))})",
    colors=colors, startangle=140, textprops={"fontsize": 9},
    wedgeprops={"edgecolor": "white", "linewidth": 1.5}
)
for at in autotexts:
    at.set_fontsize(8)
ax1.set_title("Overall Subtype Distribution\n(771 Numerical Reasoning Qs)", fontsize=12, fontweight="bold")

# 2) Stacked bar chart — by batch
x = np.arange(len(batch_labels))
bottom = np.zeros(len(batch_labels))

for i, st in enumerate(subtypes):
    vals = np.array(counts[st])
    bars = ax2.bar(x, vals, bottom=bottom, label=st, color=colors[i],
                   edgecolor="white", linewidth=0.5, width=0.65)
    # Annotate counts > 5
    for j, v in enumerate(vals):
        if v > 5:
            ax2.text(j, bottom[j] + v / 2, str(v),
                     ha="center", va="center", color="white", fontweight="bold", fontsize=8)
    bottom += vals

ax2.set_xticks(x)
ax2.set_xticklabels(batch_labels, fontsize=8)
ax2.set_ylabel("Number of Questions", fontsize=11)
ax2.set_title("Subtype Distribution by Batch (100 NR Qs each)", fontsize=12, fontweight="bold")
ax2.legend(title="SubQType", fontsize=8, title_fontsize=9, loc="upper right")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("subtype_distribution.png", dpi=200, bbox_inches="tight")
plt.show()
print("Saved to subtype_distribution.png")
