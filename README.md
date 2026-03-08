# Tree-Experiment: Table QA with Gemini

Prompt-based Table QA experiments on the **RealHiTBench** benchmark using Google Gemini models.

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install requests beautifulsoup4

# Set API key
$env:GEMINI_API_KEY="your_gemini_api_key"
```

## Project Structure

| Path | Description |
|------|-------------|
| `run_experiment_csv.py` | Main experiment runner (all modes) |
| `EVIDENCE_PROMPT.md` | 6-step evidence pipeline, processed tree+HTML |
| `EVIDENCE_PROMPT_HTML.md` | 6-step evidence pipeline, raw HTML only |
| `EVIDENCE_PROMPT_JSON.md` | 6-step evidence pipeline, JSON input |
| `BASE_PROMPT_TEMPLATE.md` | Basic rules, processed tree+HTML |
| `BASE_PROMPT_TEMPLATE_HTML.md` | Basic rules, raw HTML only |
| `SIMPLE_PROMPT_TEMPLATE.md` | Minimal chain-of-thought, raw HTML only |
| `tests/questions.jsonl` | Batch 1 questions (100 Qs, IDs 20–365) |
| `tests/questions_batch2.jsonl` | Batch 2 questions (100 Qs, IDs 382–2669) |
| `table_inputs/` | Processed tree+HTML `.txt` files |
| `trees_json/` | JSON table representations |
| `RealHiTBench/html/` | Raw HTML table files |
| `score/mcnemar_simple.py` | McNemar's test for comparing two result CSVs |
| `prepare_tables.py` | Generate `table_inputs/` from RealHiTBench |
| `inspect_tokens.py` | Estimate prompt token counts per question |
| `eda_numerical_reasoning.py` | Sub-type distribution analysis |

## Experiment Commands

### Common flags

| Flag | Description |
|------|-------------|
| `--questions <path>` | Question file (default: `tests/questions.jsonl`) |
| `--output <path>` | Output CSV path |
| `--model <name>` | Gemini model name |
| `--prompt-file <path>` | Prompt template file |
| `--html-dir <path>` | Use raw HTML tables from this directory |
| `--json-dir <path>` | Use JSON tables from this directory |
| `--delay <sec>` | Seconds between API calls (default: 1.0) |
| `--limit <n>` | Run only first N questions |
| `--qid <ids>` | Comma-separated question IDs (e.g. `20,22,26`) |
| `--demo` | Print one rendered prompt and exit (no API call) |

---

### 1. Processed Tables (tree+HTML) — Evidence Prompt

```powershell
# Batch 1
python run_experiment_csv.py --prompt-file EVIDENCE_PROMPT.md --model gemini-2.5-pro --output evidence_processed_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --prompt-file EVIDENCE_PROMPT.md --model gemini-2.5-pro --output evidence_processed_batch2.csv --delay 1.5
```

### 2. Processed Tables (tree+HTML) — Base Prompt

```powershell
# Batch 1
python run_experiment_csv.py --prompt-file BASE_PROMPT_TEMPLATE.md --model gemini-2.5-pro --output base_processed_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --prompt-file BASE_PROMPT_TEMPLATE.md --model gemini-2.5-pro --output base_processed_batch2.csv --delay 1.5
```

### 3. Non-Processed HTML — Evidence Prompt

```powershell
# Batch 1
python run_experiment_csv.py --html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md --model gemini-2.5-pro --output evidence_html_nonprocessed_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md --model gemini-2.5-pro --output evidence_html_nonprocessed_batch2.csv --delay 1.5
```

### 4. Non-Processed HTML — Base Prompt

```powershell
# Batch 1
python run_experiment_csv.py --html-dir RealHiTBench/html --prompt-file BASE_PROMPT_TEMPLATE_HTML.md --model gemini-2.5-pro --output base_html_nonprocessed_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --html-dir RealHiTBench/html --prompt-file BASE_PROMPT_TEMPLATE_HTML.md --model gemini-2.5-pro --output base_html_nonprocessed_batch2.csv --delay 1.5
```

### 5. Non-Processed HTML — Simple Prompt

```powershell
# Batch 1
python run_experiment_csv.py --html-dir RealHiTBench/html --prompt-file SIMPLE_PROMPT_TEMPLATE.md --model gemini-2.5-pro --output simple_html_nonprocessed_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --html-dir RealHiTBench/html --prompt-file SIMPLE_PROMPT_TEMPLATE.md --model gemini-2.5-pro --output simple_html_nonprocessed_batch2.csv --delay 1.5
```

### 6. JSON Tables — Evidence Prompt

```powershell
# Batch 1
python run_experiment_csv.py --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --model gemini-2.5-pro --output evidence_json_batch1.csv --delay 1.5

# Batch 2
python run_experiment_csv.py --questions tests/questions_batch2.jsonl --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --model gemini-2.5-pro --output evidence_json_batch2.csv --delay 1.5
```

### 7. Using Gemini 3.1 Model

Replace `--model gemini-2.5-pro` with `--model gemini-3.1-pro-preview` in any command above. Example:

```powershell
python run_experiment_csv.py --prompt-file EVIDENCE_PROMPT.md --model gemini-3.1-pro-preview --output evidence_processed_3.1_batch1.csv --delay 1.5
```

---

## Demo Mode (Preview Prompts)

Preview a fully rendered prompt without calling the API:

```powershell
# Processed + Evidence
python run_experiment_csv.py --demo --qid 20

# HTML + Evidence
python run_experiment_csv.py --demo --html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md --qid 382

# JSON + Evidence
python run_experiment_csv.py --demo --json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md --qid 20
```

---

## Comparing Results

Run McNemar's test between two result CSVs:

```powershell
python score/mcnemar_simple.py <baseline.csv> <improved.csv>
```

---

## Experiment Matrix

| Input Format | Prompt | Flag Combination |
|---|---|---|
| Processed (tree+HTML) | Evidence | `--prompt-file EVIDENCE_PROMPT.md` |
| Processed (tree+HTML) | Base | `--prompt-file BASE_PROMPT_TEMPLATE.md` |
| Non-processed (HTML) | Evidence | `--html-dir RealHiTBench/html --prompt-file EVIDENCE_PROMPT_HTML.md` |
| Non-processed (HTML) | Base | `--html-dir RealHiTBench/html --prompt-file BASE_PROMPT_TEMPLATE_HTML.md` |
| Non-processed (HTML) | Simple | `--html-dir RealHiTBench/html --prompt-file SIMPLE_PROMPT_TEMPLATE.md` |
| JSON | Evidence | `--json-dir trees_json --prompt-file EVIDENCE_PROMPT_JSON.md` |

Each can be run on **Batch 1** (default) or **Batch 2** (`--questions tests/questions_batch2.jsonl`), and with **Gemini 2.5** (`gemini-2.5-pro`) or **Gemini 3.1** (`gemini-3.1-pro-preview`).
