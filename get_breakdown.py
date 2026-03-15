import pandas as pd
from collections import Counter
import json
import io
from score.calculate_kappa import normalize_reviewer1, normalize_reviewer2

with open('score/numerical_reasoning_audit (1).csv', 'r', encoding='utf-8', errors='replace') as f:
    df = pd.read_csv(io.StringIO(f.read()))

df['nid'] = pd.to_numeric(df['id'], errors='coerce')
df = df[df['nid'] <= 1258]

r1 = df['Actual Answer'].fillna('').apply(normalize_reviewer1)
r2 = df[df.columns[6]].fillna('').apply(normalize_reviewer2)

def to3(v): return v if v in ['__MATCH__', '__NO_INFO__'] else '__CORRECTION__'

r1c = [to3(v) for v in r1]
r2c = [to3(v) for v in r2]

b = Counter()
for a, c in zip(r1c, r2c):
    if a != c:
        b[f"R1: {a} | R2: {c}"] += 1

both = [(a, b_val) for a, b_val in zip(r1, r2) if to3(a) == '__CORRECTION__' and to3(b_val) == '__CORRECTION__']
mismatches = sum(1 for a, c in both if a != c)
if mismatches > 0:
    b['R1: __CORRECTION__ | R2: __CORRECTION__ (String Mismatch)'] += mismatches

with open('breakdown.json', 'w') as o:
    json.dump(dict(b), o, indent=2)
