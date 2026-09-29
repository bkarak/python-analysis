#!/usr/bin/env python3
"""CPython releases: list what python.org offers; fetch and extract source tarballs.

    uv run harness/releases.py list
    uv run harness/releases.py fetch 3.0 3.14.0 ...

A release lives at work/Python-<v>.tgz and work/Python-<v>/ (both gitignored).
The tarball's SHA-256 is recorded in data/tarballs.sha256 so a later run can
tell whether it measured the same bytes.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from versions import numeric, vkey  # noqa: E402

BASE = 'https://www.python.org/ftp/python'
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
SUMS = ROOT / 'data' / 'tarballs.sha256'


def list_releases() -> None:
    html = urllib.request.urlopen(f'{BASE}/', timeout=60).read().decode()
    rows = re.findall(r'href="(\d+\.\d+(?:\.\d+)?)/">[^<]*</a>\s+(\d{2}-\w{3}-\d{4})', html)
    for v, day in sorted(rows, key=lambda r: vkey(r[0])):
        print(f'{v:10} {day}')


def record(line: str) -> None:
    SUMS.parent.mkdir(exist_ok=True)
    lines = set(SUMS.read_text().splitlines()) if SUMS.exists() else set()
    lines.add(line)
    key = lambda l: vkey(re.search(r'Python-(\d+\.\d+(?:\.\d+)?(?:(?:a|b|rc)\d+)?)\.tgz', l).group(1))  # noqa: E731
    SUMS.write_text('\n'.join(sorted(lines, key=key)) + '\n')


def fetch(v: str) -> None:
    WORK.mkdir(exist_ok=True)
    tgz, tree = WORK / f'Python-{v}.tgz', WORK / f'Python-{v}'
    if not tgz.exists():
        url = f'{BASE}/{numeric(v)}/Python-{v}.tgz'
        print(f'{v}: downloading {url}', flush=True)
        try:
            with urllib.request.urlopen(url, timeout=120) as resp, open(tgz, 'wb') as out:
                shutil.copyfileobj(resp, out)
        except (urllib.error.URLError, OSError) as exc:
            tgz.unlink(missing_ok=True)
            sys.exit(f'{v}: download failed: {exc}')
    digest = hashlib.sha256(tgz.read_bytes()).hexdigest()
    record(f'{digest}  {tgz.name}')
    if not tree.exists():
        print(f'{v}: extracting', flush=True)
        with tarfile.open(tgz) as tf:
            tf.extractall(WORK, filter='data')
    if not (tree / 'Lib').is_dir():
        sys.exit(f'{v}: no Lib/ under {tree}')
    print(f'{v}: ok  {tgz.stat().st_size:>10} bytes  sha256 {digest[:16]}', flush=True)


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'list':
        list_releases()
    elif len(sys.argv) >= 3 and sys.argv[1] == 'fetch':
        for version in sys.argv[2:]:
            fetch(version)
    else:
        sys.exit(__doc__)
