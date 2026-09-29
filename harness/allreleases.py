#!/usr/bin/env python3
"""Measure every 2.x and 3.x release python.org offers, one at a time.

    uv run harness/allreleases.py [--jobs N]

Each release is fetched, measured with the three instruments, and then its
tarball, tree and raw diagnostics are removed again, except for the releases the Makefile keeps
(the series, the sensitivity set and Python 2). Releases already measured are
skipped, so the run resumes where it stopped. A release directory without a
`.tgz` (pre-release-only directories, the oldest 2.x) is reported and skipped.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure import OUT, WORK, measure  # noqa: E402
from releases import BASE, fetch  # noqa: E402
from versions import vkey  # noqa: E402

KEEP = set('2.0.1 2.7 3.0 3.1 3.2 3.3.0 3.4.0 3.5.0 3.6.0 3.7.0 3.8.0 3.9.0 3.10.0 3.11.0 3.12.0 3.13.0 3.14.0 '
           '3.0.1 3.1.1 3.2.1 3.12.11 3.13.9'.split())


def release_dirs() -> list[str]:
    html = urllib.request.urlopen(f'{BASE}/', timeout=60).read().decode()
    found = re.findall(r'href="([23]\.\d+(?:\.\d+)?)/"', html)
    return sorted(set(found), key=vkey)


def purge(v: str) -> None:
    """The tarball, the tree and the raw diagnostics; the measurement JSON stays."""
    shutil.rmtree(WORK / f'Python-{v}', ignore_errors=True)
    (WORK / f'Python-{v}.tgz').unlink(missing_ok=True)
    for raw in (WORK / 'raw').glob(f'{v}.*.tsv'):
        raw.unlink()


def main(jobs: int) -> None:
    todo = [v for v in release_dirs() if not (OUT / f'{v}.json').exists()]
    print(f'{len(todo)} releases to measure', flush=True)
    missing = []
    for v in todo:
        try:
            fetch(v)
        except SystemExit as exc:
            print(f'{v}: skipped ({exc})', flush=True)
            missing.append(v)
            continue
        measure(v, jobs)
        if v not in KEEP:
            purge(v)
    print(f'done; no tarball for: {", ".join(missing) or "none"}', flush=True)


if __name__ == '__main__':
    argv = sys.argv[1:]
    jobs = min(os.cpu_count() or 4, 16)
    if '--jobs' in argv:
        i = argv.index('--jobs')
        jobs = int(argv[i + 1])
        del argv[i:i + 2]
    main(jobs)
