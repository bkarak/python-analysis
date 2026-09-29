#!/usr/bin/env python3
"""Sensitivity of the cohort result: era boundaries a year either way, source
lines as the denominator, and a bootstrap over files.

    uv run harness/sensitivity.py 3.14.0

Needs work/raw/<v>.blame.tsv (make cohorts) and the release's raw
diagnostics. Library proper only, pycodestyle only. Writes
data/sensitivity/<v>.json. PROTOCOL.md, "Sensitivity".
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cohorts import ERAS, read_blame, read_raw  # noqa: E402
from measure import ROOT, WORK, inventory  # noqa: E402

OUT = ROOT / 'data' / 'sensitivity'
RESAMPLES = 1000
SEED = 20260929
SHIFTS = {'earlier': -365, 'base': 0, 'later': 365}


def era_function(shift_days: int):
    bounds = [(n, d + timedelta(days=shift_days) if d else None) for n, d in ERAS]

    def era_of(day: date) -> str:
        name = bounds[0][0]
        for n, start in bounds[1:]:
            if start and day >= start:
                name = n
        return name

    return era_of, bounds


def main(version: str) -> None:
    lib = WORK / f'Python-{version}' / 'Lib'
    files = {r: f for r, f in inventory(lib).items() if f['category'] == 'stdlib'}
    blame = read_blame(version)
    diags = defaultdict(list)
    for code, rel, row in read_raw(version, 'pycodestyle'):
        if rel in files:
            diags[rel].append((row, code))
    day_of: dict[int, date] = {}
    per_file: dict[str, dict] = {}   # rel -> {'days': [...], 'sloc': [bool], 'diags': [(row, code)]}
    for rel in files:
        ts = blame.get(rel)
        if ts is None or len(ts) != files[rel]['lines']:
            continue
        raw = (lib / rel).read_bytes().splitlines()
        days = []
        for t in ts:
            d = day_of.get(t)
            if d is None:
                d = day_of[t] = datetime.fromtimestamp(t, timezone.utc).date()
            days.append(d)
        per_file[rel] = {'days': days, 'sloc': [bool(ln.strip()) and not ln.lstrip().startswith(b'#') for ln in raw],
                         'diags': diags.get(rel, [])}
    names = [n for n, _ in ERAS]

    def tally(era_of):
        """rel -> era -> [lines, sloc, style, style without E5]"""
        out = {}
        for rel, f in per_file.items():
            t = {n: [0, 0, 0, 0] for n in names}
            for d, is_sloc in zip(f['days'], f['sloc']):
                b = t[era_of(d)]
                b[0] += 1
                b[1] += is_sloc
            for row, code in f['diags']:
                if 1 <= row <= len(f['days']):
                    b = t[era_of(f['days'][row - 1])]
                    b[2] += 1
                    b[3] += not code.startswith('E5')
            out[rel] = t
        return out

    result = {'version': version, 'measured': date.today().isoformat(), 'unit': 'file',
              'resamples': RESAMPLES, 'seed': SEED, 'files': len(per_file), 'boundaries': {}, 'eras': {}, 'shifted': {}}
    for label, shift in SHIFTS.items():
        era_of, bounds = era_function(shift)
        result['boundaries'][label] = [{'name': n, 'from': d.isoformat() if d else None} for n, d in bounds]
        t = tally(era_of)
        totals = {n: [sum(t[r][n][i] for r in t) for i in range(4)] for n in names}
        if label != 'base':
            result['shifted'][label] = {n: {'lines': v[0], 'per_k': round(v[2] / v[0] * 1000, 1) if v[0] else None,
                                            'per_k_excl_e5': round(v[3] / v[0] * 1000, 1) if v[0] else None}
                                        for n, v in totals.items()}
            continue
        rels = list(t)
        rng = random.Random(SEED)
        samples = {n: ([], []) for n in names}
        for _ in range(RESAMPLES):
            acc = {n: [0, 0, 0] for n in names}
            for r in rng.choices(rels, k=len(rels)):
                for n in names:
                    v = t[r][n]
                    a = acc[n]
                    a[0] += v[0]
                    a[1] += v[2]
                    a[2] += v[3]
            for n in names:
                if acc[n][0]:
                    samples[n][0].append(acc[n][1] / acc[n][0] * 1000)
                    samples[n][1].append(acc[n][2] / acc[n][0] * 1000)

        def ci(xs):
            xs = sorted(xs)
            return [round(xs[int(0.025 * len(xs))], 1), round(xs[int(0.975 * len(xs)) - 1], 1)] if xs else None

        for n, v in totals.items():
            result['eras'][n] = {
                'lines': v[0], 'sloc': v[1], 'style': v[2], 'style_excl_e5': v[3],
                'per_k': round(v[2] / v[0] * 1000, 1) if v[0] else None,
                'per_k_excl_e5': round(v[3] / v[0] * 1000, 1) if v[0] else None,
                'per_k_sloc': round(v[2] / v[1] * 1000, 1) if v[1] else None,
                'ci95': ci(samples[n][0]), 'ci95_excl_e5': ci(samples[n][1]),
            }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')
    for n in names:
        e = result['eras'][n]
        print(f"  {n:20} {e['per_k']:6} [{e['ci95'][0]}, {e['ci95'][1]}]  excl. E5 {e['per_k_excl_e5']:6} "
              f"[{e['ci95_excl_e5'][0]}, {e['ci95_excl_e5'][1]}]  per k sloc {e['per_k_sloc']:6}  "
              f"earlier {result['shifted']['earlier'][n]['per_k']}  later {result['shifted']['later'][n]['per_k']}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
