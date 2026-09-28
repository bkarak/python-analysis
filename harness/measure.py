#!/usr/bin/env python3
"""Measure extracted CPython releases with both instruments.

    uv run harness/measure.py [--jobs N] 3.14.0 3.13.0 ...

Reads work/Python-<v>/Lib, writes data/measurements/<v>.json and the raw
diagnostics to work/raw/<v>.<instrument>.tsv. The instrument definitions here
are the ones PROTOCOL.md describes; change both together.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pycodestyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import CATEGORIES, category, head_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
RAW = WORK / 'raw'
OUT = ROOT / 'data' / 'measurements'
LINE_LENGTH = 79
TOP_FILES = 25
PYCODESTYLE_FORMAT = '%(path)s\t%(row)d\t%(col)d\t%(code)s\t%(text)s'


def is_error(code: str) -> bool:
    """Diagnostics that are not style: syntax and I/O failures."""
    return code.startswith('E9') or code == 'invalid-syntax'


def ruff_target(version: str) -> str:
    major, minor = (int(x) for x in version.split('.')[:2])
    return f'py3{max(minor, 7)}' if major == 3 else 'py37'


def inventory(lib: Path) -> dict[str, dict]:
    """Every .py file under Lib/ (symlinks skipped): line counts and category."""
    files: dict[str, dict] = {}
    for p in sorted(lib.rglob('*.py')):
        if p.is_symlink() or not p.is_file():
            continue
        rel = p.relative_to(lib).as_posix()
        data = p.read_bytes()
        raw_lines = data.splitlines()
        files[rel] = {
            'lines': len(raw_lines),
            'sloc': sum(1 for ln in raw_lines if ln.strip() and not ln.lstrip().startswith(b'#')),
            'size': len(data),
            'category': category(rel, head_text(data)),
        }
    return files


def balanced_chunks(files: dict[str, dict], n: int) -> list[list[str]]:
    buckets: list[list[str]] = [[] for _ in range(n)]
    loads = [0] * n
    for rel in sorted(files, key=lambda f: -files[f]['size']):
        i = loads.index(min(loads))
        buckets[i].append(rel)
        loads[i] += files[rel]['size']
    return [b for b in buckets if b]


def run_pycodestyle(lib: Path, files: dict[str, dict], jobs: int) -> list[tuple[str, str, str]]:
    def one(batch: list[str]) -> str:
        proc = subprocess.run(
            # -P keeps the release's own Lib/ (the cwd) off sys.path; without it the 2008
            # stdlib shadows the interpreter's runpy and tokenize and pycodestyle dies.
            [sys.executable, '-P', '-m', 'pycodestyle', f'--max-line-length={LINE_LENGTH}',
             f'--format={PYCODESTYLE_FORMAT}', *batch],
            cwd=lib, capture_output=True, text=True, errors='replace')
        if proc.stderr.strip():
            print(f'  pycodestyle stderr: {proc.stderr.strip()[:300]}', file=sys.stderr)
        return proc.stdout

    with ThreadPoolExecutor(jobs) as pool:
        outputs = list(pool.map(one, balanced_chunks(files, jobs)))
    rows = []
    for out in outputs:
        for line in out.splitlines():
            parts = line.split('\t', 4)
            if len(parts) == 5:
                path, _row, _col, code, text = parts
                rows.append((code, path, text))
    return rows


def run_ruff(lib: Path, files: dict[str, dict], target: str) -> tuple[list[tuple[str, str, str]], list[str]]:
    args = ['check', '--isolated', '--no-cache', '--preview', '--select', 'E,W',
            f'--line-length={LINE_LENGTH}', f'--target-version={target}',
            '--output-format', 'json', '--exit-zero']
    proc = subprocess.run(['ruff', *args, *files], cwd=lib, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'ruff failed: {proc.stderr[:500]}')
    prefix = str(lib.resolve()) + '/'
    rows = []
    for d in json.loads(proc.stdout):
        code = d.get('code') or 'invalid-syntax'
        rows.append((code, d['filename'].removeprefix(prefix), d['message']))
    return rows, args


def aggregate(rows: list[tuple[str, str, str]], files: dict[str, dict]) -> dict:
    by_code: Counter = Counter()
    by_cat: Counter = Counter()
    by_file: Counter = Counter()
    by_cat_code: dict[str, Counter] = defaultdict(Counter)
    messages: dict[str, str] = {}
    for code, rel, text in rows:
        cat = files[rel]['category'] if rel in files else 'unknown'
        by_code[code] += 1
        by_cat[cat] += 1
        by_cat_code[cat][code] += 1
        by_file[rel] += 1
        messages.setdefault(code, text)
    errors = sum(n for c, n in by_code.items() if is_error(c))
    return {
        'total': len(rows),
        'style': len(rows) - errors,
        'errors': errors,
        'by_code': dict(sorted(by_code.items())),
        'by_category': dict(sorted(by_cat.items())),
        'by_category_code': {c: dict(sorted(v.items())) for c, v in sorted(by_cat_code.items())},
        'top_files': by_file.most_common(TOP_FILES),
        'messages': dict(sorted(messages.items())),
    }


def measure(version: str, jobs: int) -> None:
    lib = WORK / f'Python-{version}' / 'Lib'
    if not lib.is_dir():
        sys.exit(f'{version}: {lib} is missing; run `make fetch VERSIONS={version}` first')
    t0 = time.time()
    files = inventory(lib)
    pcs_rows = run_pycodestyle(lib, files, jobs)
    ruff_rows, ruff_args = run_ruff(lib, files, ruff_target(version))
    ruff_version = subprocess.run(['ruff', '--version'], capture_output=True, text=True).stdout.split()[-1]

    def per_category(key: str) -> dict[str, int]:
        return {c: sum(f[key] for f in files.values() if f['category'] == c) for c in CATEGORIES}

    result = {
        'version': version,
        'measured': date.today().isoformat(),
        'python': platform.python_version(),
        'instruments': {
            'pycodestyle': {'version': pycodestyle.__version__,
                            'args': [f'--max-line-length={LINE_LENGTH}'],
                            'note': 'defaults otherwise, including the default ignore list'},
            'ruff': {'version': ruff_version, 'args': ruff_args},
        },
        'files': {c: sum(1 for f in files.values() if f['category'] == c) for c in CATEGORIES},
        'lines': per_category('lines'),
        'sloc': per_category('sloc'),
        'generated_files': sorted(r for r, f in files.items() if f['category'] == 'generated'),
        'pycodestyle': aggregate(pcs_rows, files),
        'ruff': aggregate(ruff_rows, files),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')
    for name, rows in (('pycodestyle', pcs_rows), ('ruff', ruff_rows)):
        with open(RAW / f'{version}.{name}.tsv', 'w') as fh:
            fh.writelines(f'{c}\t{r}\t{t}\n' for c, r, t in sorted(rows))
    p, r = result['pycodestyle'], result['ruff']
    print(f"{version:8} files {sum(result['files'].values()):5}  lines {sum(result['lines'].values()):8}  "
          f"pycodestyle {p['style']:6} (+{p['errors']:3} non-style)  ruff {r['style']:6} (+{r['errors']:3})  "
          f"{time.time() - t0:5.1f}s", flush=True)


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
        measure(version, jobs)
