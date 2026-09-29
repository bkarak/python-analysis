#!/usr/bin/env python3
"""Density per package of the library proper, and the vendored packages.

    uv run harness/packages.py 3.14.0

Groups the stdlib-category files of a measured release by top-level package
(or single-file module) and reports pycodestyle style density for each; also
the density of the code maintained outside CPython and synced in, listed in
VENDORED with its origin, and of the library proper without it. Writes
data/packages/<v>.json. PROTOCOL.md, "Packages and vendored code".
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cohorts import read_raw  # noqa: E402
from measure import ROOT, WORK, inventory  # noqa: E402

OUT = ROOT / 'data' / 'packages'
# path prefix under Lib/ -> where the code is maintained
VENDORED = {
    'tomllib': 'tomli, Taneli Hukkinen; added in 3.11',
    '_pyrepl': 'pyrepl, from PyPy; added in 3.13',
    'importlib/metadata': 'importlib_metadata, Jason R. Coombs; synced since 3.8',
    'importlib/resources': 'importlib_resources; synced since 3.7',
    'zipfile/_path': 'zipp; synced since 3.12',
}


def vendored_origin(rel: str) -> str | None:
    for prefix, origin in VENDORED.items():
        if rel == prefix + '.py' or rel.startswith(prefix + '/'):
            return origin
    return None


def main(version: str) -> None:
    lib = WORK / f'Python-{version}' / 'Lib'
    files = {r: f for r, f in inventory(lib).items() if f['category'] == 'stdlib'}
    style: Counter = Counter()
    for _code, rel, _row in read_raw(version, 'pycodestyle'):
        if rel in files:
            style[rel] += 1
    groups: dict[str, dict] = defaultdict(lambda: {'files': 0, 'lines': 0, 'style': 0, 'kind': 'package'})
    vend = {'lines': 0, 'style': 0, 'files': 0}
    for rel, f in files.items():
        name = rel.split('/')[0] if '/' in rel else rel.removesuffix('.py')
        g = groups[name]
        g['files'] += 1
        g['lines'] += f['lines']
        g['style'] += style[rel]
        if '/' not in rel:
            g['kind'] = 'module'
        if vendored_origin(rel):
            vend['files'] += 1
            vend['lines'] += f['lines']
            vend['style'] += style[rel]
    packages = [{'name': n, **g, 'per_k': round(g['style'] / g['lines'] * 1000, 1) if g['lines'] else None,
                 'vendored': vendored_origin(n if any(r.startswith(n + '/') for r in files) else n + '.py')}
                for n, g in groups.items()]
    packages.sort(key=lambda p: -(p['per_k'] or 0))
    total_lines = sum(f['lines'] for f in files.values())
    total_style = sum(style.values())
    result = {
        'version': version, 'measured': date.today().isoformat(), 'instrument': 'pycodestyle',
        'stdlib': {'lines': total_lines, 'style': total_style, 'per_k': round(total_style / total_lines * 1000, 1)},
        'vendored': {'set': VENDORED, **vend, 'per_k': round(vend['style'] / vend['lines'] * 1000, 1) if vend['lines'] else None},
        'stdlib_without_vendored': {'lines': total_lines - vend['lines'], 'style': total_style - vend['style'],
                                    'per_k': round((total_style - vend['style']) / (total_lines - vend['lines']) * 1000, 1)},
        'packages': packages,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')
    print(f"{version}: {len(packages)} packages/modules; stdlib {result['stdlib']['per_k']}/k, vendored "
          f"{result['vendored']['per_k']}/k on {vend['lines']} lines, without vendored {result['stdlib_without_vendored']['per_k']}/k")
    big = [p for p in packages if p['lines'] >= 300]
    print('  densest:', ', '.join(f"{p['name']} {p['per_k']}" for p in big[:8]))
    print('  cleanest:', ', '.join(f"{p['name']} {p['per_k']}" for p in big[-8:]))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
