#!/usr/bin/env python3
"""Re-run ruff on each sample release under three settings and break results down."""
import json, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # project root: work/ and pyproject.toml live there
WORK = ROOT / 'work'
RUFF = ['uvx', 'ruff@0.14.4']
VERSIONS = ['3.0.1','3.1.1','3.2.1','3.3.0','3.4.0','3.5.0','3.6.0','3.7.0','3.8.0','3.9.0',
            '3.10.0','3.11.0','3.12.0','3.12.11','3.13.0','3.13.9','3.14.0']
TEST_PARTS = {'test','tests','idle_test','testdata','test_data','tokenizedata'}

def category(rel):
    parts = rel.replace('\\','/').split('/')
    return 'tests' if any(p in TEST_PARTS for p in parts[:-1]) else 'stdlib'

def loc(libdir):
    lines, files = Counter(), Counter()
    for p in list(libdir.rglob('*.py')) + list(libdir.rglob('*.pyi')):
        cat = category(str(p.relative_to(libdir)))
        files[cat] += 1
        try:
            with open(p,'rb') as fh: lines[cat] += sum(1 for _ in fh)
        except OSError: pass
    return lines, files

def run(version, extra):
    lib = f'work/Python-{version}/Lib'
    out = subprocess.run(RUFF + ['check','--output-format','json','--select','E,W',*extra, lib],
                         cwd=ROOT, capture_output=True, text=True)
    try: diags = json.loads(out.stdout)
    except json.JSONDecodeError:
        print('BAD JSON', version, extra, out.stderr[:300], file=sys.stderr); return []
    libabs = str((ROOT/lib).resolve()) + '/'
    res = []
    for d in diags:
        code = d.get('code') or 'invalid-syntax'
        rel = d['filename'].replace(libabs,'')
        res.append((code, rel, category(rel)))
    return res

def tv(version):
    minor = int(version.split('.')[1])
    return f'py3{max(minor,7)}'

VARIANTS = {
    'A_blog':     lambda v: [],                                   # target inferred 3.13 from pyproject
    'B_matched':  lambda v: ['--target-version', tv(v)],
    'C_pep8full': lambda v: ['--target-version', tv(v), '--preview', '--line-length', '79'],
}

result = {}
for v in VERSIONS:
    lines, files = loc(WORK/f'Python-{v}'/'Lib')
    entry = {'loc': dict(lines), 'files': dict(files), 'variants': {}}
    for name, mk in VARIANTS.items():
        res = run(v, mk(v))
        entry['variants'][name] = {
            'total': len(res),
            'by_code': dict(Counter(c for c,_,_ in res)),
            'by_cat': dict(Counter(cat for _,_,cat in res)),
            'syntax': sum(1 for c,_,_ in res if c=='invalid-syntax'),
            'by_file': dict(Counter(f for _,f,_ in res)),
        }
    result[v] = entry
    a, b = entry['variants']['A_blog'], entry['variants']['B_matched']
    print(f"{v:8} files={sum(files.values()):5} loc={sum(lines.values()):8}  "
          f"A={a['total']:6} (syntax {a['syntax']:5}, stdlib {a['by_cat'].get('stdlib',0):5}, tests {a['by_cat'].get('tests',0):5})  "
          f"B={b['total']:6} (syntax {b['syntax']:5})  C={entry['variants']['C_pep8full']['total']:6}", flush=True)

json.dump(result, open(HERE/'breakdown.json','w'), indent=1)
print('WROTE breakdown.json')
