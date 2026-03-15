import csv
import json
import os
from pathlib import Path
import html

def extract_html_from_txt(txt_path):
    if not os.path.exists(txt_path):
        return "<i>Table file missing</i>"
    content = Path(txt_path).read_text(encoding="utf-8", errors="ignore")
    marker = "[TABLE HTML]"
    idx = content.find(marker)
    if idx != -1:
        return content[idx + len(marker):].strip()
    return "<i>Marker not found</i>"

def generate_report():
    results_csv = "results_fixed.csv"
    if not os.path.exists(results_csv):
        print(f"{results_csv} not found.")
        return

    failed_cases = []
    with open(results_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("EM") == "0":
                failed_cases.append(row)

    if not failed_cases:
        print("No failed cases found! (EM == 0)")
        return

    html_out = [
        "<html><head><title>Error Analysis Dashboard</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #f5f7fa; }",
        ".card { background: white; margin-bottom: 30px; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "h2 { margin-top: 0; color: #2c3e50; }",
        ".metadata { display: flex; gap: 20px; margin-bottom: 15px; font-size: 14px; color: #666; }",
        ".qa-box { background: #f8f9fc; padding: 15px; border-left: 4px solid #4e73df; margin-bottom: 15px; font-size: 16px; }",
        ".answers { display: flex; gap: 20px; margin-bottom: 15px; }",
        ".expected { flex: 1; padding: 15px; background: #e8f4f8; border-left: 4px solid #36b9cc; }",
        ".actual { flex: 1; padding: 15px; background: #fcebeb; border-left: 4px solid #e74a3b; }",
        ".response-box { max-height: 250px; overflow-y: auto; background: #2b2b2b; color: #f8f8f2; padding: 15px; font-family: monospace; white-space: pre-wrap; font-size: 13px; border-radius: 4px; border: 1px solid #444; margin-bottom: 15px; }",
        ".table-box { max-height: 400px; overflow: auto; border: 1px solid #ddd; padding: 10px; background: #fff; }",
        "table { border-collapse: collapse; width: max-content; }",
        "th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }",
        "th { background-color: #f2f2f2; }",
        "</style></head><body>",
        f"<h1>Error Analysis Dashboard: {len(failed_cases)} Failed Questions</h1>"
    ]

    for row in failed_cases:
        qid = row.get("id", "N/A")
        tid = row.get("filename", "").replace("table_inputs\\", "").replace("table_inputs/", "").replace(".txt", "")
        question = row.get("question", "")
        expected = row.get("correct_answer", "")
        actual = row.get("model_answer", "")
        subtype = row.get("sub_type", "N/A")
        response = row.get("full_response", "")

        table_html = extract_html_from_txt(f"table_inputs/{tid}.txt")

        html_out.append(f"""
        <div class="card">
            <h2>Q{qid} <span style="font-size:14px; color:#888;">(Table: {tid} | Type: {subtype})</span></h2>
            <div class="qa-box"><strong>Q:</strong> {html.escape(question)}</div>
            <div class="answers">
                <div class="expected"><strong>Expected Answer (Ground Truth):</strong><br><br><span style="font-size:18px; font-weight:bold;">{html.escape(expected)}</span></div>
                <div class="actual"><strong>Gemini Answer:</strong><br><br><span style="font-size:18px; font-weight:bold;">{html.escape(actual)}</span></div>
            </div>
            
            <h4>Full Reasoning Trace:</h4>
            <div class="response-box">{html.escape(response)}</div>

            <h4>Source Table HTML:</h4>
            <div class="table-box">{table_html}</div>
        </div>
        """)

    html_out.append("</body></html>")

    out_file = "error_review_dashboard.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html_out))

    print(f"Generated {out_file} with {len(failed_cases)} errors.")

if __name__ == "__main__":
    generate_report()
