#!/usr/bin/env python3
"""Age cohorts: blame every line of a release's Lib/ to the commit that last
edited it, and report PEP 8 density by the date of that edit.

    uv run harness/cohorts.py [--jobs N] [--limit N] 3.14.0

Needs the CPython clone in work/cpython (make cpython) and the release's raw
diagnostics in work/raw/ (make measure). Writes data/cohorts/<v>.json and
work/raw/<v>.blame.tsv. Method and caveats: PROTOCOL.md, "Age cohorts".
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES  # noqa: E402
from measure import RAW, ROOT, WORK, inventory, is_error  # noqa: E402

CPYTHON = WORK / 'cpython'
OUT = ROOT / 'data' / 'cohorts'
INSTRUMENTS = ('pycodestyle', 'ruff')
# Each era starts on the day of an event in how CPython's code was written or reviewed.
ERAS: list[tuple[str, date | None]] = [
    ('before PEP 8', None),
    ('PEP 8 to 3.0', date(2001, 7, 5)),        # PEP 8 created
    ('3.0 to GitHub', date(2008, 12, 3)),       # Python 3.0 released
    ('GitHub to ruff', date(2017, 2, 10)),      # development moved to GitHub pull requests
    ('ruff in pre-commit', date(2023, 9, 12)),  # gh-60283: first ruff hook in .pre-commit-config.yaml
]


def era_of(day: date) -> str:
    name = ERAS[0][0]
    for era, start in ERAS[1:]:
        if start is not None and day >= start:
            name = era
    return name


def git(*args: str) -> str:
    return subprocess.run(['git', '-C', str(CPYTHON), *args], capture_output=True, text=True, check=True).stdout


def blobs_at(tag: str) -> dict[str, str]:
    res = {}
    for entry in git('ls-tree', '-r', '-z', tag, '--', 'Lib').split('\0'):
        if entry:
            meta, path = entry.split('\t', 1)
            _mode, kind, sha = meta.split()
            if kind == 'blob':
                res[path.removeprefix('Lib/')] = sha
    return res


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def blame(tag: str, rel: str) -> list[int]:
    """author-time, in epoch seconds, of the commit that last edited each line."""
    proc = subprocess.run(['git', '-C', str(CPYTHON), 'blame', '--line-porcelain', tag, '--', f'Lib/{rel}'],
                          capture_output=True, text=True, errors='replace')
    times: list[int] = []
    current = 0
    for line in proc.stdout.split('\n'):
        if line.startswith('author-time '):
            current = int(line[12:])
        elif line.startswith('\t'):
            times.append(current)
    return times


def read_raw(version: str, instrument: str) -> list[tuple[str, str, int]]:
    rows = []
    with open(RAW / f'{version}.{instrument}.tsv') as fh:
        for line in fh:
            code, rel, row, _col, _text = line.rstrip('\n').split('\t', 4)
            if not is_error(code):
                rows.append((code, rel, int(row)))
    return rows


class Bucket:
    """One cohort: its lines and, per instrument, its style diagnostics by rule."""

    def __init__(self) -> None:
        self.lines = 0
        self.by_code: dict[str, Counter] = {i: Counter() for i in INSTRUMENTS}

    def as_dict(self) -> dict:
        return {'lines': self.lines,
                **{i: {'style': sum(c.values()), 'by_code': dict(sorted(c.items()))}
                   for i, c in self.by_code.items()}}


def main(version: str, jobs: int, limit: int | None) -> None:
    tag = f'v{version}'
    lib = WORK / f'Python-{version}' / 'Lib'
    if not CPYTHON.is_dir():
        sys.exit('work/cpython is missing: run `make cpython`')
    if not lib.is_dir():
        sys.exit(f'{lib} is missing: run `make fetch VERSIONS={version}`')
    if not (RAW / f'{version}.pycodestyle.tsv').exists():
        sys.exit(f'work/raw/{version}.pycodestyle.tsv is missing: run `make measure VERSIONS={version}`')
    commit = git('rev-parse', f'{tag}^{{commit}}').strip()
    t0 = time.time()
    files = inventory(lib)
    blobs = blobs_at(tag)
    rels = sorted(files)[:limit] if limit else sorted(files)
    skipped: dict[str, str] = {}
    for rel in rels:
        if rel not in blobs:
            skipped[rel] = 'not in git at the tag'
        elif blobs[rel] != blob_sha(lib / rel):
            skipped[rel] = 'tarball content differs from the tag'
    todo = [r for r in rels if r not in skipped]
    with ThreadPoolExecutor(jobs) as pool:
        times = dict(zip(todo, pool.map(lambda r: blame(tag, r), todo)))
    for rel in todo:
        if len(times[rel]) != files[rel]['lines']:
            skipped[rel] = f'blame has {len(times[rel])} lines, the inventory {files[rel]["lines"]}'
            del times[rel]

    day_of: dict[int, date] = {}
    days: dict[str, list[date]] = {}
    years = {c: defaultdict(Bucket) for c in CATEGORIES}
    eras = {c: defaultdict(Bucket) for c in CATEGORIES}
    for rel, ts in times.items():
        cat = files[rel]['category']
        ds = []
        for t in ts:
            d = day_of.get(t)
            if d is None:
                d = day_of[t] = datetime.fromtimestamp(t, timezone.utc).date()
            ds.append(d)
            years[cat][d.year].lines += 1
            eras[cat][era_of(d)].lines += 1
        days[rel] = ds
    unattributed: dict[str, int] = {}
    for inst in INSTRUMENTS:
        lost = 0
        for code, rel, row in read_raw(version, inst):
            ds = days.get(rel)
            if ds is None or not 1 <= row <= len(ds):
                lost += 1
                continue
            d, cat = ds[row - 1], files[rel]['category']
            years[cat][d.year].by_code[inst][code] += 1
            eras[cat][era_of(d)].by_code[inst][code] += 1
        unattributed[inst] = lost

    result = {
        'version': version, 'tag': tag, 'commit': commit,
        'measured': date.today().isoformat(), 'seconds': round(time.time() - t0, 1),
        'blame': {'command': f'git blame --line-porcelain {tag} -- Lib/<file>', 'date': 'author-time',
                  'files': len(times), 'skipped': skipped, 'unattributed': unattributed},
        'eras': [{'name': n, 'from': d.isoformat() if d else None} for n, d in ERAS],
        'by_category': {c: {'years': {str(y): b.as_dict() for y, b in sorted(years[c].items())},
                            'eras': {n: eras[c][n].as_dict() for n, _ in ERAS if n in eras[c]}}
                        for c in CATEGORIES},
    }
    if limit is None:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')
        with open(RAW / f'{version}.blame.tsv', 'w') as fh:
            for rel, ts in sorted(times.items()):
                fh.writelines(f'{rel}\t{i}\t{t}\n' for i, t in enumerate(ts, 1))
    total = sum(b.lines for c in CATEGORIES for b in eras[c].values())
    print(f"{version}: blamed {len(times)} files, {total} lines, skipped {len(skipped)}, "
          f"unattributed {unattributed}, {result['seconds']}s" + ('  (limited: not written)' if limit else ''))
    for era, _ in ERAS:
        b = eras['stdlib'].get(era)
        if b:
            print(f"  {era:20} stdlib lines {b.lines:7}  pycodestyle {b.by_code['pycodestyle'].total():6}"
                  f"  {b.by_code['pycodestyle'].total() / b.lines * 1000:6.1f}/k")


if __name__ == '__main__':
    argv = sys.argv[1:]
    jobs = min(os.cpu_count() or 4, 16)
    limit = None
    if '--jobs' in argv:
        i = argv.index('--jobs'); jobs = int(argv[i + 1]); del argv[i:i + 2]
    if '--limit' in argv:
        i = argv.index('--limit'); limit = int(argv[i + 1]); del argv[i:i + 2]
    if len(argv) != 1:
        sys.exit(__doc__)
    main(argv[0], jobs, limit)
