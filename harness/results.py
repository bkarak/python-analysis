#!/usr/bin/env python3
"""Print the tables in RESULTS.md from data/measurements/*.json (markdown on stdout)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEASUREMENTS = ROOT / 'data' / 'measurements'
CATEGORIES = ('stdlib', 'tests', 'generated')
FAMILIES = ('E1', 'E2', 'E3', 'E4', 'E5', 'E7', 'W1', 'W2', 'W3', 'W5', 'W6')


def vkey(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split('.'))


def is_series(v: str) -> bool:
    parts = v.split('.')
    return len(parts) == 2 or parts[2] == '0'


def is_error(code: str) -> bool:
    return code.startswith('E9') or code == 'invalid-syntax'


def per_k(n: int, lines: int) -> str:
    return f'{n / lines * 1000:.1f}' if lines else 'n/a'


def style_in(inst: dict, cat: str, prefix: str = '') -> int:
    return sum(n for c, n in inst['by_category_code'].get(cat, {}).items()
               if not is_error(c) and c.startswith(prefix))


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ['| ' + ' | '.join(headers) + ' |',
           '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(headers))) + '|']
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return '\n'.join(out)


def main() -> None:
    data = {p.stem: json.loads(p.read_text()) for p in MEASUREMENTS.glob('*.json')}
    if not data:
        raise SystemExit('no measurements yet: run `make measure`')
    series = sorted((v for v in data if is_series(v)), key=vkey)
    patches = sorted((v for v in data if not is_series(v)), key=vkey)
    first, last = data[series[0]], data[series[-1]]
    ins = last['instruments']
    print(f"Instruments: pycodestyle {ins['pycodestyle']['version']} at 79 columns with its defaults, "
          f"and ruff {ins['ruff']['version']} with `--isolated --preview --select E,W --line-length 79` "
          f"and the target version matched to the release; Python {last['python']}; "
          f"last measured {last['measured']}. Counts are style diagnostics only; syntax and I/O "
          f"failures are the `non-style` column. Rates are per thousand physical lines of `.py` under `Lib/`.\n")

    print('## The series: one point per minor release\n')
    rows = []
    for v in series:
        d = data[v]
        lines = sum(d['lines'].values())
        p, r = d['pycodestyle'], d['ruff']
        rows.append([v, sum(d['files'].values()), lines, p['style'], per_k(p['style'], lines),
                     per_k(style_in(p, 'stdlib'), d['lines']['stdlib']),
                     per_k(style_in(p, 'tests'), d['lines']['tests']),
                     per_k(style_in(p, 'generated'), d['lines']['generated']),
                     r['style'], per_k(r['style'], lines), f"{p['errors']} / {r['errors']}"])
    print(md_table(['release', 'files', 'lines', 'pycodestyle', '/k', 'stdlib /k', 'tests /k',
                    'generated /k', 'ruff', '/k', 'non-style pcs / ruff'], rows))

    print('\n## Rule families in the stdlib proper (pycodestyle, per thousand lines)\n')
    rows = [[v] + [per_k(style_in(data[v]['pycodestyle'], 'stdlib', f), data[v]['lines']['stdlib'])
                   for f in FAMILIES] for v in series]
    print(md_table(['release', *FAMILIES], rows))

    print(f'\n## Rules in the stdlib proper: {series[-1]} against {series[0]} (pycodestyle)\n')
    f_codes = first['pycodestyle']['by_category_code'].get('stdlib', {})
    l_codes = last['pycodestyle']['by_category_code'].get('stdlib', {})
    codes = [c for c in sorted(set(f_codes) | set(l_codes),
                               key=lambda c: -max(f_codes.get(c, 0), l_codes.get(c, 0))) if not is_error(c)][:20]
    msgs = {**first['pycodestyle']['messages'], **last['pycodestyle']['messages']}
    rows = [[c, f_codes.get(c, 0), per_k(f_codes.get(c, 0), first['lines']['stdlib']),
             l_codes.get(c, 0), per_k(l_codes.get(c, 0), last['lines']['stdlib']),
             re.sub(r"\s*(\(.*\)|'\\.*')$", '', msgs.get(c, ''))] for c in codes]
    print(md_table(['rule', f'{series[0]}', '/k', f'{series[-1]}', '/k', 'what it is'], rows))

    print(f'\n## Where the diagnostics are in {series[-1]}\n')
    rows = []
    for cat in CATEGORIES:
        p, r = style_in(last['pycodestyle'], cat), style_in(last['ruff'], cat)
        rows.append([cat, last['files'][cat], last['lines'][cat],
                     p, f"{p / last['pycodestyle']['style'] * 100:.0f}%", per_k(p, last['lines'][cat]),
                     r, f"{r / last['ruff']['style'] * 100:.0f}%", per_k(r, last['lines'][cat])])
    print(md_table(['category', 'files', 'lines', 'pycodestyle', 'share', '/k', 'ruff', 'share', '/k'], rows))

    if patches:
        print('\n## Sensitivity: patch releases against their minor\'s first release\n')
        rows = []
        for v in patches:
            minor = '.'.join(v.split('.')[:2])
            base = next((s for s in series if '.'.join(s.split('.')[:2]) == minor), None)
            d, b = data[v], data[base] if base else None
            lines = sum(d['lines'].values())
            row = [v, lines, per_k(d['pycodestyle']['style'], lines), per_k(d['ruff']['style'], lines)]
            if b:
                blines = sum(b['lines'].values())
                row += [base, per_k(b['pycodestyle']['style'], blines), per_k(b['ruff']['style'], blines)]
            else:
                row += ['n/a', 'n/a', 'n/a']
            rows.append(row)
        print(md_table(['release', 'lines', 'pycodestyle /k', 'ruff /k', 'x.y.0', 'pycodestyle /k', 'ruff /k'], rows))


if __name__ == '__main__':
    main()
