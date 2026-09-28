#!/usr/bin/env python3
"""Config-neutral rerun: --isolated ignores every config file (the repo's pyproject.toml and CPython's shipped .ruff.toml files)."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # project root: work/ and pyproject.toml live there
RUFF = ['uvx','ruff@0.14.4']
R = json.load(open(HERE/'breakdown.json'))
TEST_PARTS = {'test','tests','idle_test','testdata','test_data','tokenizedata'}
def category(rel):
    return 'tests' if any(p in TEST_PARTS for p in rel.split('/')[:-1]) else 'stdlib'
def tv(v): return f'py3{max(int(v.split(".")[1]),7)}'
def run(v, ll):
    lib = f'work/Python-{v}/Lib'
    out = subprocess.run(RUFF+['check','--isolated','--output-format','json','--select','E,W','--target-version',tv(v),'--line-length',str(ll),lib], cwd=ROOT, capture_output=True, text=True)
    diags = json.loads(out.stdout)
    libabs = str((ROOT/lib).resolve())+'/'
    return [((d.get('code') or 'invalid-syntax'), d['filename'].replace(libabs,'')) for d in diags]
out = {}
print(f"{'ver':8} {'LOC':>7} | {'iso88':>6} {'/KLOC':>6} {'stdlib/K':>8} {'tests/K':>7} {'syntax':>6} | {'iso79':>6} {'/KLOC':>6} {'E501@79':>7}")
for v in R:
    loc = R[v]['loc']; tot = sum(loc.values())
    row = {}
    for ll in (88, 79):
        res = run(v, ll)
        by_cat = Counter(category(f) for _,f in res)
        row[ll] = {'total': len(res), 'by_code': dict(Counter(c for c,_ in res)), 'by_cat': dict(by_cat),
                   'by_file': dict(Counter(f for _,f in res)), 'syntax': sum(1 for c,_ in res if c=='invalid-syntax')}
    out[v] = row
    a, b = row[88], row[79]
    print(f"{v:8} {tot:7} | {a['total']:6} {a['total']/tot*1000:6.1f} {a['by_cat'].get('stdlib',0)/loc['stdlib']*1000:8.1f} {a['by_cat'].get('tests',0)/loc['tests']*1000:7.1f} {a['syntax']:6} | {b['total']:6} {b['total']/tot*1000:6.1f} {b['by_code'].get('E501',0):7}", flush=True)
json.dump(out, open(HERE/'isolated.json','w'), indent=1)
print("WROTE isolated.json")
