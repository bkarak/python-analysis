#!/usr/bin/env python3
"""Baselines: the same instruments on other Python code bases.

    uv run harness/baselines.py [--jobs N] [django numpy pip requests black]

Downloads each project's current sdist from PyPI into work/baselines/ (kept,
gitignored), measures the package's own source tree exactly as measure.py
measures Lib/ (same file rules, same categories, same flags), and writes
data/baselines/<name>.json. Method: PROTOCOL.md, "Baselines".
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from datetime import date
from pathlib import Path

import pycodestyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES  # noqa: E402
from measure import LINE_LENGTH, ROOT, WORK, aggregate, inventory, is_error, run_pycodestyle, run_ruff  # noqa: E402

BASE = WORK / 'baselines'
OUT = ROOT / 'data' / 'baselines'
TARGET = 'py310'  # the oldest Python the five projects support in 2026
# name: PyPI project, the source directory inside the sdist, top-level entries in it to leave out
PROJECTS = {
    'django': ('Django', 'django', ()),
    'numpy': ('numpy', 'numpy', ()),
    'pip': ('pip', 'src/pip', ('_vendor',)),      # pip vendors its dependencies under _vendor
    'requests': ('requests', 'src/requests', ()),
    'black': ('black', 'src/black', ()),          # src/blib2to3, a vendored fork of lib2to3, is outside
}


def pypi_sdist(project: str) -> tuple[str, str, str]:
    with urllib.request.urlopen(f'https://pypi.org/pypi/{project}/json', timeout=60) as r:
        info = json.load(r)
    version = info['info']['version']
    for u in info['urls']:
        if u['packagetype'] == 'sdist':
            return version, u['url'], u['digests']['sha256']
    sys.exit(f'{project} {version}: no sdist on PyPI')


def fetch(name: str, project: str) -> tuple[str, str, str, Path]:
    BASE.mkdir(parents=True, exist_ok=True)
    version, url, sha = pypi_sdist(project)
    tgz = BASE / url.rsplit('/', 1)[-1]
    if not tgz.exists():
        print(f'{name}: downloading {url}', flush=True)
        with urllib.request.urlopen(url, timeout=120) as r, open(tgz, 'wb') as out:
            shutil.copyfileobj(r, out)
    digest = hashlib.sha256(tgz.read_bytes()).hexdigest()
    if digest != sha:
        tgz.unlink()
        sys.exit(f'{name}: sha256 of {tgz.name} does not match PyPI')
    with tarfile.open(tgz) as tf:
        top = tf.getnames()[0].split('/')[0]
        tree = BASE / top
        if not tree.exists():
            tf.extractall(BASE, filter='data')
    return version, url, digest, tree


def measure(name: str, jobs: int) -> None:
    project, subdir, drop = PROJECTS[name]
    version, url, digest, tree = fetch(name, project)
    src = tree / subdir
    if not src.is_dir():
        sys.exit(f'{name}: {src} is not a directory; the sdist layout changed')
    t0 = time.time()
    files = {rel: f for rel, f in inventory(src).items() if rel.split('/')[0] not in drop}
    pcs_rows = run_pycodestyle(src, files, jobs)
    ruff_rows, ruff_args = run_ruff(src, files, TARGET)
    naming_rows, naming_args = run_ruff(src, files, TARGET, select='N', preview=False)
    ruff_version = subprocess.run(['ruff', '--version'], capture_output=True, text=True).stdout.split()[-1]

    def per_category(key: str) -> dict[str, int]:
        return {c: sum(f[key] for f in files.values() if f['category'] == c) for c in CATEGORIES}

    result = {
        'project': name, 'pypi': project, 'version': version,
        'sdist': {'url': url, 'sha256': digest}, 'source_dir': subdir, 'dropped': list(drop),
        'measured': date.today().isoformat(),
        'instruments': {
            'pycodestyle': {'version': pycodestyle.__version__, 'args': [f'--max-line-length={LINE_LENGTH}']},
            'ruff': {'version': ruff_version, 'args': ruff_args},
            'naming': {'version': ruff_version, 'args': naming_args},
        },
        'files': {c: sum(1 for f in files.values() if f['category'] == c) for c in CATEGORIES},
        'lines': per_category('lines'),
        'sloc': per_category('sloc'),
        'generated_files': sorted(r for r, f in files.items() if f['category'] == 'generated'),
        'pycodestyle': aggregate(pcs_rows, files),
        'ruff': aggregate(ruff_rows, files),
        'naming': aggregate(naming_rows, files),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.json').write_text(json.dumps(result, indent=1) + '\n')
    p, lines = result['pycodestyle'], result['lines']
    proper = sum(n for c, n in p['by_category_code'].get('stdlib', {}).items() if not is_error(c))
    print(f"{name:9} {version:8} files {sum(result['files'].values()):5}  lines {sum(lines.values()):7}  "
          f"pycodestyle {p['style']:6}  proper {proper / max(lines['stdlib'], 1) * 1000:6.1f}/k  "
          f"ruff {result['ruff']['style']:6}  naming {result['naming']['style']:5}  {time.time() - t0:5.1f}s", flush=True)


if __name__ == '__main__':
    argv = sys.argv[1:]
    jobs = min(os.cpu_count() or 4, 16)
    if '--jobs' in argv:
        i = argv.index('--jobs')
        jobs = int(argv[i + 1])
        del argv[i:i + 2]
    for name in argv or list(PROJECTS):
        if name not in PROJECTS:
            sys.exit(f'unknown project {name}; known: {", ".join(PROJECTS)}')
        measure(name, jobs)
