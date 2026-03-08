"""
Inspect prompt token counts for specific question IDs using table_inputs .txt files.
IDs > 1940 are loaded from tests/questions_batch2.jsonl, others from tests/questions.jsonl.
Results are ranked descending by token count and compared to the folder average.

Usage:
    .venv/Scripts/python.exe inspect_tokens.py
"""
import json
from pathlib import Path

PROJECT_ROOT    = Path(__file__).resolve().parent
QUESTIONS_PATH  = PROJECT_ROOT / "tests" / "questions.jsonl"
QUESTIONS_PATH2 = PROJECT_ROOT / "tests" / "questions_batch2.jsonl"
TABLE_INPUTS    = PROJECT_ROOT / "table_inputs"
PROMPT_TXT      = PROJECT_ROOT / "EVIDENCE_PROMPT.md"

INSPECT_IDS = [360, 278, 250, 217, 169, 108, 2652, 2476, 2318, 1943]

def estimate_tokens(text: str) -> int:
    return len(text) // 4

def load_questions(path: Path) -> dict:
    questions = {}
    if not path.exists():
        return questions
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            questions[str(q["id"])] = q
    return questions

def build_prompt(content: str, question: str, template: str) -> str:
    parts     = content.split("[TABLE HTML]")
    col_row   = parts[0] if len(parts) > 1 else ""
    html      = "[TABLE HTML]" + parts[1] if len(parts) > 1 else content
    col_parts = col_row.split("[ROW STRUCTURE]")
    col_sec   = col_parts[0].strip()
    row_sec   = "[ROW STRUCTURE]" + col_parts[1].strip() if len(col_parts) > 1 else ""
    return template.format(
        col_structure_section=col_sec,
        row_structure_section=row_sec,
        html_section=html,
        question=question,
    )

def main():
    questions = load_questions(QUESTIONS_PATH)
    questions.update(load_questions(QUESTIONS_PATH2))  # batch2 covers IDs 382+
    template  = PROMPT_TXT.read_text(encoding="utf-8")

    # ── Compute average token size across ALL .txt files in table_inputs ──
    all_txt_files = list(TABLE_INPUTS.glob("*.txt"))
    all_tokens = []
    for txt_path in all_txt_files:
        content = txt_path.read_text(encoding="utf-8", errors="replace")
        # Use a blank question so template size is consistent
        try:
            prompt = build_prompt(content, "", template)
        except KeyError:
            prompt = content
        all_tokens.append(estimate_tokens(prompt))

    avg_tokens = sum(all_tokens) / len(all_tokens) if all_tokens else 0
    min_tokens = min(all_tokens) if all_tokens else 0
    max_tokens = max(all_tokens) if all_tokens else 0

    print(f"── table_inputs folder stats ({len(all_txt_files)} files) ──────────────────────────")
    print(f"   Average : {avg_tokens:>8,.0f} tokens")
    print(f"   Min     : {min_tokens:>8,} tokens")
    print(f"   Max     : {max_tokens:>8,} tokens")
    print()

    # ── Build rows for inspected IDs ──────────────────────────────────────
    rows = []
    for qid in INSPECT_IDS:
        sid = str(qid)
        q   = questions.get(sid)

        if q is None:
            rows.append((0, qid, "—", "—", f"ID {qid} not found", "", "—"))
            continue

        tid      = q.get("table_id", sid)
        question = q.get("question", "")
        txt_path = TABLE_INPUTS / f"{tid}.txt"

        if not txt_path.exists():
            rows.append((0, qid, "—", "—", f"MISSING: {tid}.txt", "", "—"))
            continue

        content = txt_path.read_text(encoding="utf-8", errors="replace")
        prompt  = build_prompt(content, question, template)

        tokens  = estimate_tokens(prompt)
        chars   = len(prompt)
        q_short = question[:45].replace("\n", " ")

        # vs average
        delta   = tokens - avg_tokens
        vs_avg  = f"{delta:+,.0f} ({delta / avg_tokens * 100:+.1f}%)"

        rows.append((tokens, qid, f"{tokens:,}", f"{chars:,}", f"{tid}.txt", q_short, vs_avg))

    # Sort descending by token count
    rows.sort(key=lambda r: r[0], reverse=True)

    header = f"{'ID':>6}  {'Tokens':>8}  {'Chars':>10}  {'vs Avg':>20}  {'File':<35}  Question (truncated)"
    print(header)
    print("-" * 115)
    for _, qid, tokens, chars, fname, q_short, vs_avg in rows:
        print(f"{qid:>6}  {tokens:>8}  {chars:>10}  {vs_avg:>20}  {fname:<35}  {q_short}")

    # ── Write markdown report ─────────────────────────────────────────────
    md_path = PROJECT_ROOT / "inspect_output.md"
    with open(md_path, "w", encoding="utf-8") as md:
        md.write("# Token Size Inspection\n\n")
        md.write(f"## Folder Stats — `table_inputs/` ({len(all_txt_files)} files)\n\n")
        md.write("| Stat    |       Tokens |\n")
        md.write("|---------|-------------:|\n")
        md.write(f"| Average | {avg_tokens:>12,.0f} |\n")
        md.write(f"| Min     | {min_tokens:>12,} |\n")
        md.write(f"| Max     | {max_tokens:>12,} |\n")
        md.write("\n")
        md.write("## Inspected IDs (ranked by token size)\n\n")
        md.write("| ID | Tokens | Chars | vs Average | File | Question |\n")
        md.write("|---:|-------:|------:|:----------:|:-----|:---------|\n")
        for _, qid, tokens, chars, fname, q_short, vs_avg in rows:
            md.write(f"| {qid} | {tokens} | {chars} | {vs_avg} | `{fname}` | {q_short} |\n")

    print(f"\nMarkdown report written to: {md_path.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    main()