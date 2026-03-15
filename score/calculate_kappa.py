import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score
import os

def normalize_reviewer1(ans):
    ans = str(ans).strip()
    ans_lower = ans.lower()
    
    # "match" means the answer in the benchmark is already correct
    # Reviewer 1 use "x" to indicate a match
    if ans_lower == "x":
        return "__MATCH__"
        
    # If the table is wrong, reviewer 1 will say NO INFO or 'wrong table'
    if ans_lower in ["no info", "no_info", "wrong table"]:
        return "__NO_INFO__"
        
    # Otherwise they write their correct answers
    return ans_lower

def normalize_reviewer2(ans):
    ans = str(ans).strip()
    ans_lower = ans.lower()
    
    # Reviewer 2 use "match" to indicate a match
    if ans_lower == "match":
        return "__MATCH__"
        
    # Reviewer 2 will leave it blank for NO INFO or may explicitly say 'wrong table'
    if ans == "" or ans_lower in ["nan", "none", "wrong table"]:
        return "__NO_INFO__"
        
    # Otherwise they write their correct answers
    return ans_lower

def main():
    file_path = "numerical_reasoning_audit.csv"
    if not os.path.exists(file_path):
        # maybe running from project root
        file_path = os.path.join("score", "numerical_reasoning_audit.csv")
        
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    # Load CSV with fallback encoding to handle potential Windows characters
    import io
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    df = pd.read_csv(io.StringIO(content))
    
    # Filter for first 300 answers (up to id 1258)
    df['numeric_id'] = pd.to_numeric(df['id'], errors='coerce')
    df = df[df['numeric_id'] <= 1258].copy()
    
    # The columns are: id,FileName,Question,Processed Answer,Actual Answer,,Reviewer 2
    # So Actual Answer is col index 4 (0-based) and Reviewer 2 is col index 6
    
    # Get column names dynamically in case they differ slightly
    r1_col = "Reviewer 1"
    
    # Find Reviewer 2 column
    r2_col = None
    for col in df.columns:
        if "Reviewer 2" in str(col):
            r2_col = col
            break
            
    if r2_col is None:
        # Fall back to index if not found
        r2_col = df.columns[6]
        
    # Handle NaN values explicitly
    df[r1_col] = df[r1_col].fillna("")
    df[r2_col] = df[r2_col].fillna("")

    # Map the answers
    r1_mapped = df[r1_col].apply(normalize_reviewer1).tolist()
    r2_mapped = df[r2_col].apply(normalize_reviewer2).tolist()
    
    print(f"Total annotations: {len(r1_mapped)}")
    
    # Compute Exact Agreement
    agreements = sum(1 for a, b in zip(r1_mapped, r2_mapped) if a == b)
    print(f"Exact Agreement (Absolute Text Match): {agreements}/{len(r1_mapped)} ({(agreements/len(r1_mapped))*100:.2f}%)")
    
    # 3-Class Mapping for Cohen's Kappa
    def to_3_class(val):
        if val in ["__MATCH__", "__NO_INFO__"]:
            return val
        return "__CORRECTION__"
        
    r1_class = [to_3_class(v) for v in r1_mapped]
    r2_class = [to_3_class(v) for v in r2_mapped]
    
    # Compute 3-class Cohen's Kappa score
    kappa_3class = cohen_kappa_score(r1_class, r2_class)
    print(f"\nStage 1: Error Discovery (3-Class: Match, No Info, Correction)")
    print(f"Cohen's Kappa Score: {kappa_3class:.4f}")
    
    # Compute Exact Agreement on Corrections
    both_correction = [(a, b) for a, b in zip(r1_mapped, r2_mapped) if to_3_class(a) == "__CORRECTION__" and to_3_class(b) == "__CORRECTION__"]
    if both_correction:
        corr_agreements = sum(1 for a, b in both_correction if a == b)
        print(f"\nStage 2: Exact Match of Corrections")
        print(f"When both reviewers provided a correction, they wrote the exact same string {corr_agreements}/{len(both_correction)} times ({(corr_agreements/len(both_correction))*100:.2f}%)")
        print("Note: This string match is lossy and penalizes formatting differences.")
        
    print("\n--- Disagreement Breakdown ---")
    from collections import Counter
    breakdown = Counter()
    for r1, r2 in zip(r1_class, r2_class):
        if r1 != r2:
            key = f"R1: {r1.replace('__', '')} | R2: {r2.replace('__', '')}"
            breakdown[key] += 1
            
    # Add exact string mismatches when both corrected
    str_mismatch = len(both_correction) - (corr_agreements if both_correction else 0)
    if str_mismatch > 0:
        breakdown["R1: CORRECTION | R2: CORRECTION (String Mismatch)"] += str_mismatch

    for k, v in breakdown.most_common():
        print(f"{v:3d} cases - {k}")
        
    print("\n--- Confusion Matrix ---")
    from sklearn.metrics import confusion_matrix
    labels = ["__MATCH__", "__CORRECTION__", "__NO_INFO__"]
    cm = confusion_matrix(r1_class, r2_class, labels=labels)
    print("                    Reviewer 2")
    print("                 MATCH  CORR  NO_INFO")
    print(f"R1 MATCH         {cm[0,0]:<5}  {cm[0,1]:<5} {cm[0,2]:<5}")
    print(f"   CORR          {cm[1,0]:<5}  {cm[1,1]:<5} {cm[1,2]:<5}")
    print(f"   NO_INFO       {cm[2,0]:<5}  {cm[2,1]:<5} {cm[2,2]:<5}")
    
    # Optional: Print out disagreements for review and save to CSV
    # print("\n--- Disagreements ---")
    disagreements = []
    for i, (r1, r2) in enumerate(zip(r1_mapped, r2_mapped)):
        if r1 != r2:
            row_id = df.iloc[i]['id']
            q_text = df.iloc[i].get('Question', '')
            model_ans = df.iloc[i].get('Processed Answer', '')
            r1_orig = df.iloc[i][r1_col]
            r2_orig = df.iloc[i][r2_col]
            disagreements.append({
                'csv_row': i + 2,
                'id': row_id,
                'Question': q_text,
                'Model_Answer': model_ans,
                'R1_original': r1_orig,
                'R1_mapped': r1,
                'R2_original': r2_orig,
                'R2_mapped': r2
            })
            
    # Save to CSV
    out_csv = os.path.join(os.path.dirname(file_path), "kappa_disagreements_with_model.csv")
    try:
        pd.DataFrame(disagreements).to_csv(out_csv, index=False)
        print(f"\nSaved {len(disagreements)} disagreements to: {out_csv}")
    except PermissionError:
        print(f"\nError: Could not save to {out_csv}. Is the file open in Excel?")
        alt_csv = os.path.join(os.path.dirname(file_path), "kappa_disagreements_with_model_alt.csv")
        pd.DataFrame(disagreements).to_csv(alt_csv, index=False)
        print(f"Saved to alternative path: {alt_csv}")

if __name__ == "__main__":
    main()
