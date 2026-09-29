#!/usr/bin/env python3
"""Line-length distribution: where the long lines sit, not just how many pass 79.

    uv run harness/linelength.py [--jobs N] 3.14.0 3.13.0 ...

For every release given: the distribution of physical line lengths per
category (characters after decoding, a tab counting one, trailing whitespace
stripped, as pycodestyle measures E501), and the docstring or comment lines
over 72 columns (pycodestyle W505 with --max-doc-length=72). For a release that
has a blame dump (make cohorts), the same by era. Writes
data/linelength/<v>.json. PROTOCOL.md, "Line length".
"""
from __future__ import annotations

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
from cohorts import ERAS, era_of, read_blame  # noqa: E402
from measure import RAW, ROOT, WORK, balanced_chunks, inventory  # noqa: E402

OUT = ROOT / 'data' / 'linelength'
THRESHOLDS = (79, 88, 99, 120)
DOC_LENGTH = 72


class Dist:
    def __init__(self) -> None:
        self.lines = 0
        self.over: Counter = Counter()
        self.long: list[int] = []
        self.doc_over = 0

    def add(self, n: int) -> None:
        self.lines += 1
        for t in THRESHOLDS:
            if n > t:
                self.over[t] += 1
        if n > THRESHOLDS[0]:
            self.long.append(n)

    def as_dict(self) -> dict:
        long = sorted(self.long)

        def pct(q: float) -> int | None:
            return long[min(len(long) - 1, int(q * len(long)))] if long else None

        return {'lines': self.lines, 'over': {str(t): self.over[t] for t in THRESHOLDS},
                'long_percentiles': {'p50': pct(0.5), 'p90': pct(0.9), 'p99': pct(0.99),
                                     'max': long[-1] if long else None},
                'doc_over_72': self.doc_over}


def doc_rows(lib: Path, files: dict[str, dict], jobs: int) -> list[tuple[str, int]]:
    fmt = '%(path)s\t%(row)d\t%(code)s'

    def one(batch: list[str]) -> str:
        return subprocess.run(
            [sys.executable, '-P', '-m', 'pycodestyle', '--select=W505', f'--max-doc-length={DOC_LENGTH}',
             f'--format={fmt}', *batch], cwd=lib, capture_output=True, text=True, errors='replace').stdout

    with ThreadPoolExecutor(jobs) as pool:
        outputs = list(pool.map(one, balanced_chunks(files, jobs)))
    rows = []
    for out in outputs:
        for line in out.splitlines():
            parts = line.split('\t')
            if len(parts) == 3 and parts[2] == 'W505':
                rows.append((parts[0], int(parts[1])))
    return rows


def run(version: str, jobs: int) -> None:
    lib = WORK / f'Python-{version}' / 'Lib'
    if not lib.is_dir():
        sys.exit(f'{lib} is missing: make fetch VERSIONS={version}')
    t0 = time.time()
    files = inventory(lib)
    blame = read_blame(version) if (RAW / f'{version}.blame.tsv').exists() else None
    by_cat = {c: Dist() for c in CATEGORIES}
    by_era: dict[tuple[str, str], Dist] = defaultdict(Dist)
    day_of: dict[int, date] = {}
    eras_of: dict[str, list[str]] = {}
    for rel, f in files.items():
        cat = f['category']
        text = (lib / rel).read_bytes().decode('utf-8', 'replace')
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        ts = blame.get(rel) if blame else None
        if ts is not None and len(ts) == len(lines):
            names = []
            for t in ts:
                d = day_of.get(t)
                if d is None:
                    d = day_of[t] = datetime.fromtimestamp(t, timezone.utc).date()
                names.append(era_of(d))
            eras_of[rel] = names
        for i, line in enumerate(lines):
            n = len(line.rstrip())
            by_cat[cat].add(n)
            if rel in eras_of:
                by_era[(cat, eras_of[rel][i])].add(n)
    for rel, row in doc_rows(lib, files, jobs):
        cat = files[rel]['category']
        by_cat[cat].doc_over += 1
        if rel in eras_of and row <= len(eras_of[rel]):
            by_era[(cat, eras_of[rel][row - 1])].doc_over += 1
    result = {
        'version': version, 'measured': date.today().isoformat(),
        'thresholds': list(THRESHOLDS), 'doc_length': DOC_LENGTH,
        'by_category': {c: by_cat[c].as_dict() for c in CATEGORIES},
        'by_era': ({c: {name: by_era[(c, name)].as_dict() for name, _ in ERAS if (c, name) in by_era}
                    for c in CATEGORIES} if blame else None),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')
    s = by_cat['stdlib']
    print(f"{version:8} stdlib lines {s.lines:7}  over 79: {s.over[79] / s.lines * 100:5.1f}%  over 88: "
          f"{s.over[88] / s.lines * 100:5.1f}%  over 99: {s.over[99] / s.lines * 100:5.1f}%  "
          f"doc>72: {s.doc_over:5}  eras: {'yes' if blame else 'no'}  {time.time() - t0:4.1f}s", flush=True)


if __name__ == '__main__':
    argv = sys.argv[1:]
    jobs = min(os.cpu_count() or 4, 16)
    if '--jobs' in argv:
        i = argv.index('--jobs')
        jobs = int(argv[i + 1])
        del argv[i:i + 2]
    if not argv:
        sys.exit(__doc__)
    for version in argv:
        run(version, jobs)
