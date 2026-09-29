#!/usr/bin/env python3
"""Survival: which violations of an older release are still there, line for line.

    uv run harness/survival.py [--jobs N] 3.8.0 3.14.0

Release tags live on release branches, so the start is the merge base of the
two tags, the point where the older minor branched off main (for 3.8.0 that
is v3.8.0b1, 2019-06-04). Its Lib/ is archived to work/survival/, measured
with pycodestyle, and every line is reverse-blamed to the end tag: a line
reported under the end commit still exists there, unchanged, at a known
line; any other line was edited or removed. A violation whose line survived
is then looked up in the end release's own diagnostics. Writes
data/survival/<from>-<to>.json. PROTOCOL.md, "Fix behaviour".
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES  # noqa: E402
from cohorts import CPYTHON, git, read_raw  # noqa: E402
from measure import ROOT, WORK, inventory, run_pycodestyle  # noqa: E402

OUT = ROOT / 'data' / 'survival'
HEADER = re.compile(r'^[0-9a-f]{40} (\d+) (\d+)')


def archive_lib(commit: str, dest: Path) -> Path:
    if not (dest / 'Lib').is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        data = subprocess.run(['git', '-C', str(CPYTHON), 'archive', '--format=tar', commit, 'Lib'],
                              capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(dest, filter='data')
    return dest / 'Lib'


def reverse_blame(start: str, end: str, rel: str) -> list[tuple[str, int, str]]:
    """Per line of the start version: (last commit the line existed in, its line there, its path there)."""
    proc = subprocess.run(['git', '-C', str(CPYTHON), 'blame', '--reverse', '--line-porcelain',
                           f'{start}..{end}', '--', f'Lib/{rel}'], capture_output=True, text=True, errors='replace')
    out: list[tuple[str, int, str]] = []
    sha, orig, fname = '', 0, ''
    for line in proc.stdout.split('\n'):
        m = HEADER.match(line)
        if m:
            sha, orig = line[:40], int(m.group(1))
        elif line.startswith('filename '):
            fname = line[9:]
        elif line.startswith('\t'):
            out.append((sha, orig, fname))
    return out


def main(frm: str, to: str, jobs: int) -> None:
    start = git('merge-base', f'v{frm}', f'v{to}').strip()
    end = git('rev-parse', f'v{to}^{{commit}}').strip()
    start_date = git('log', '-1', '--format=%cs', start).strip()
    start_desc = git('describe', '--tags', '--exact-match', start).strip() if subprocess.run(
        ['git', '-C', str(CPYTHON), 'describe', '--tags', '--exact-match', start], capture_output=True).returncode == 0 else None
    t0 = time.time()
    lib = archive_lib(start, WORK / 'survival' / f'{frm}-branch-point')
    files = inventory(lib)
    rows = run_pycodestyle(lib, files, jobs)
    rels = sorted(files)
    with ThreadPoolExecutor(jobs) as pool:
        blames = dict(zip(rels, pool.map(lambda r: reverse_blame(start, end, r), rels)))
    skipped = [r for r in rels if len(blames[r]) != files[r]['lines']]
    for r in skipped:
        del blames[r]
    end_diags = {(rel, row, code) for code, rel, row in read_raw(to, 'pycodestyle')}
    lines = {c: {'total': 0, 'survived': 0} for c in CATEGORIES}
    for rel, entries in blames.items():
        cat = files[rel]['category']
        lines[cat]['total'] += len(entries)
        lines[cat]['survived'] += sum(1 for sha, _, _ in entries if sha == end)
    rules: dict[str, Counter] = defaultdict(Counter)
    unattributed = 0
    for code, rel, row, _col, _text in rows:
        if code.startswith('E9') or files[rel]['category'] != 'stdlib':
            continue
        entries = blames.get(rel)
        if entries is None or not 1 <= row <= len(entries):
            unattributed += 1
            continue
        sha, orig, fname = entries[row - 1]
        r = rules[code]
        r['n'] += 1
        if sha == end:
            r['line_survived'] += 1
            if (fname.removeprefix('Lib/'), orig, code) in end_diags:
                r['violation_survived'] += 1
    result = {
        'from': frm, 'to': to, 'measured': date.today().isoformat(), 'seconds': round(time.time() - t0, 1),
        'start': {'commit': start, 'date': start_date, 'tag': start_desc,
                  'note': f'merge base of v{frm} and v{to}: the point where the {frm[:3]} branch left main'},
        'end': {'commit': end, 'tag': f'v{to}'},
        'blame': {'command': f'git blame --reverse --line-porcelain {start[:12]}..v{to} -- Lib/<file>',
                  'files': len(blames), 'skipped': skipped, 'unattributed': unattributed},
        'lines': lines,
        'rules': {c: dict(r) for c, r in sorted(rules.items())},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{frm}-{to}.json').write_text(json.dumps(result, indent=1) + '\n')
    s = lines['stdlib']
    total = sum(r['n'] for r in rules.values())
    surv = sum(r['line_survived'] for r in rules.values())
    kept = sum(r['violation_survived'] for r in rules.values())
    print(f"{frm} branch point ({start_date}) -> {to}: stdlib lines {s['total']} of which {s['survived'] / s['total'] * 100:.1f}% unchanged; "
          f"violations {total}: line unchanged {surv / total * 100:.1f}%, violation still there {kept / total * 100:.1f}%; "
          f"skipped {len(skipped)} files, {result['seconds']}s")


if __name__ == '__main__':
    argv = sys.argv[1:]
    jobs = min(os.cpu_count() or 4, 16)
    if '--jobs' in argv:
        i = argv.index('--jobs')
        jobs = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 2:
        sys.exit(__doc__)
    main(argv[0], argv[1], jobs)
