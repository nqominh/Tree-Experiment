# Experiment Results: Gemini vs Minimax

This document contains the final evaluated metrics (Exact Match and F1) for both the Gemini and Minimax models across the three core experimental conditions:
* **C1**: Vanilla (Zero-shot from raw HTML)
* **C3**: Schema Only (Zero-shot from injected schema)
* **C5**: Full Method (Injected schema + 6-step reasoning CoT)

*Note: All scores were normalized using the [qa_metrics.py](file:///c:/Users/nqmi/Downloads/Tree-Experiment/qa_metrics.py) definitions (lowercasing, article/punctuation removal, and rounding 1 decimal place).*

---

# Part 1: Gemini 2.5 Pro Results

**Dataset Size:** 626 questions

### 1.1 Overall Metrics (Gemini)
| Condition | n | EM (%) | F1 micro (%) |
|---|---|---|---|
| **C1 (Vanilla)** | 626 | 74.76 | 81.55 |
| **C3 (Schema Only)** | 626 | 74.28 | 81.14 |
| **C5 (Full Method)** | 626 | 69.97 | 77.97 |

### 1.2 Exact Match (EM) by SubType
| SubType | n | C1 % | C3 % | C5 % | Δ (C3 vs C1) |
|---|---|---|---|---|---|
| Calculation | 201 | 77.61 | 76.12 | 72.14 | -1.49 |
| Comparison | 95 | 60.00 | 57.89 | 56.84 | -2.11 |
| Counting | 185 | 86.49 | 85.41 | 82.70 | -1.08 |
| Multi-hop | 60 | 70.00 | 71.67 | 61.67 | +1.67 |
| Ranking | 85 | 62.35 | 65.88 | 55.29 | +3.53 |

### 1.3 F1 Score by SubType
| SubType | n | C1 % | C3 % | C5 % | Δ (C3 vs C1) |
|---|---|---|---|---|---|
| Calculation | 201 | 78.11 | 76.62 | 72.12 | -1.49 |
| Comparison | 95 | 79.12 | 78.86 | 77.60 | -0.26 |
| Counting | 185 | 87.87 | 87.08 | 82.32 | -0.79 |
| Multi-hop | 60 | 78.37 | 80.11 | 73.35 | +1.74 |
| Ranking | 85 | 80.90 | 82.16 | 73.35 | +1.26 |

---

# Part 2: Minimax Results

**Dataset Size:** 625 questions
*Note: Due to a parsing difference in the raw question source files, 375 of the minimax questions fell into the generic "Numerical Reasoning (NR)" category lacking a specific subtype.*

### 2.1 Overall Metrics (Minimax)
| Condition | n | EM (~%) | F1 micro (~%) |
|---|---|---|---|
| **C1 (Vanilla)** | 625 | 73.92 | 81.10 |
| **C3 (Schema Only)** | 625 | 73.92 | 80.40 |
| **C5 (Full Method)** | 625 | 60.48 | 68.60 |

### 2.2 Exact Match (EM) by SubType
| SubType | n | C1 % | C3 % | C5 % | Δ (C3 vs C1) |
|---|---|---|---|---|---|
| Calculation | 44 | 79.55 | 81.82 | 75.00 | +2.27 |
| Comparison | 57 | 57.89 | 57.89 | 33.33 | 0.00 |
| Counting | 74 | 86.49 | 82.43 | 72.97 | -4.06 |
| Multi-hop | 25 | 80.00 | 76.00 | 60.00 | -4.00 |
| NR (Generic) | 375 | 75.20 | 75.47 | 63.20 | +0.27 |
| Ranking | 50 | 58.00 | 58.00 | 40.00 | 0.00 |

### 2.3 F1 Score by SubType
| SubType | n | C1 % | C3 % | C5 % | Δ (C3 vs C1) |
|---|---|---|---|---|---|
| Calculation | 44 | 79.55 | 81.82 | 75.00 | +2.27 |
| Comparison | 57 | 77.57 | 73.89 | 52.40 | -3.68 |
| Counting | 74 | 89.30 | 85.75 | 76.46 | -3.55 |
| Multi-hop | 25 | 87.94 | 86.98 | 73.05 | -0.96 |
| NR (Generic) | 375 | 79.87 | 80.33 | 70.62 | +0.46 |
| Ranking | 50 | 80.87 | 77.75 | 69.00 | -3.12 |

---

# Key Analytical Takeaways

1. **High Baseline Equivalency:** Gemini (74.76% EM) and Minimax (73.92% EM) exhibit functionally identical core capability in zero-shot Tabular QA from raw HTML.
2. **Format Contention (C5 Degradation):** Overly restrictive forced output formats (the 6-step prompt in C5) significantly penalize both models, but disproportionately harm Minimax (dropping ~13% EM vs Gemini's ~5% drop).
3. **Asymmetric Schema Impact:** Neither model strictly "benefits" universally from schema injection (C3). However, the specific areas of benefit differ model-to-model:
   - Gemini leverages the schema to improve traversal Tasks (Multi-hop, Ranking).
   - Minimax leverages the schema to improve Calculation but degrades on counting and ranking.
