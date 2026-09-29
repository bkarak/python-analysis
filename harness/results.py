#!/usr/bin/env python3
"""Print the tables in RESULTS.md from data/ (markdown on stdout)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from versions import is_prerelease, minor_of, select_series, vkey  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
MEASUREMENTS = DATA / 'measurements'
CATEGORIES = ('stdlib', 'tests', 'generated')
FAMILIES = ('E1', 'E2', 'E3', 'E4', 'E5', 'E7', 'W1', 'W2', 'W3', 'W5', 'W6')
# Rules about what the code does rather than how it is laid out: comparisons to
# None/True/False, membership and identity tests, type comparison, bare except,
# lambda assignment, ambiguous names, and the W6 deprecations (PROTOCOL.md, "Rule severity").
SEMANTIC = re.compile(r'^(E71\d|E72\d|E731|E74\d|W6\d\d)$')


def major(v: str) -> int:
    return int(v.split('.')[0])


def is_error(code: str) -> bool:
    return code.startswith('E9') or code == 'invalid-syntax'


def per_k(n: float, lines: int) -> str:
    return f'{n / lines * 1000:.1f}' if lines else 'n/a'


def pct(n: float, total: int) -> str:
    return f'{n / total * 100:.1f}%' if total else 'n/a'


def style_in(inst: dict, cat: str, prefix: str = '') -> int:
    return sum(n for c, n in inst['by_category_code'].get(cat, {}).items()
               if not is_error(c) and c.startswith(prefix))


def semantic_in(inst: dict, cat: str) -> int:
    return sum(n for c, n in inst['by_category_code'].get(cat, {}).items() if SEMANTIC.match(c))


def clean(msg: str) -> str:
    msg = re.sub(r"\s*(\(.*\)|'\\.*')$", '', msg)
    return re.sub(r'`[^`]*`', '…', msg)


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ['| ' + ' | '.join(headers) + ' |',
           '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(headers))) + '|']
    out += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return '\n'.join(out)


def load_dir(name: str) -> dict[str, dict]:
    d = DATA / name
    return {p.stem: json.loads(p.read_text()) for p in d.glob('*.json')} if d.is_dir() else {}


# ---------------------------------------------------------------- the series

def series_tables(data: dict, series: list[str], patches: list[str], final: str) -> None:
    first3 = next(v for v in series if major(v) >= 3)
    first, last = data[first3], data[final]
    ins = last['instruments']
    print(f"Instruments: pycodestyle {ins['pycodestyle']['version']} at 79 columns with its defaults, "
          f"and ruff {ins['ruff']['version']} with `--isolated --preview --select E,W --line-length 79` "
          f"and the target version matched to the release; Python {last['python']}; "
          f"last measured {last['measured']}. Counts are style diagnostics only; syntax and I/O "
          f"failures are the `non-style` column. Rates are per thousand physical lines of `.py` under `Lib/`. "
          f"Ruff cannot parse Python 2, so its columns are n/a for 2.x.\n")

    print('## The series: one point per minor release\n')
    rows = []
    for v in series:
        d = data[v]
        lines = sum(d['lines'].values())
        p, r = d['pycodestyle'], d['ruff']
        py2 = major(v) < 3
        rows.append([v + (' (pre-release)' if is_prerelease(v) else ''), sum(d['files'].values()), lines, p['style'], per_k(p['style'], lines),
                     per_k(style_in(p, 'stdlib'), d['lines']['stdlib']),
                     per_k(style_in(p, 'tests'), d['lines']['tests']),
                     per_k(style_in(p, 'generated'), d['lines']['generated']),
                     'n/a' if py2 else r['style'], 'n/a' if py2 else per_k(r['style'], lines),
                     f"{p['errors']} / {r['errors']}"])
    print(md_table(['release', 'files', 'lines', 'pycodestyle', '/k', 'stdlib /k', 'tests /k',
                    'generated /k', 'ruff', '/k', 'non-style pcs / ruff'], rows))

    print('\n## Rule families in the stdlib proper (pycodestyle, per thousand lines)\n')
    rows = [[v] + [per_k(style_in(data[v]['pycodestyle'], 'stdlib', f), data[v]['lines']['stdlib'])
                   for f in FAMILIES] for v in series]
    print(md_table(['release', *FAMILIES], rows))

    print(f'\n## Rules in the stdlib proper: {final} against {first3} (pycodestyle)\n')
    f_codes = first['pycodestyle']['by_category_code'].get('stdlib', {})
    l_codes = last['pycodestyle']['by_category_code'].get('stdlib', {})
    codes = [c for c in sorted(set(f_codes) | set(l_codes),
                               key=lambda c: -max(f_codes.get(c, 0), l_codes.get(c, 0))) if not is_error(c)][:20]
    msgs = {**first['pycodestyle']['messages'], **last['pycodestyle']['messages']}
    rows = [[c, f_codes.get(c, 0), per_k(f_codes.get(c, 0), first['lines']['stdlib']),
             l_codes.get(c, 0), per_k(l_codes.get(c, 0), last['lines']['stdlib']), clean(msgs.get(c, ''))] for c in codes]
    print(md_table(['rule', f'{first3}', '/k', f'{final}', '/k', 'what it is'], rows))

    print(f'\n## Where the diagnostics are in {final}\n')
    rows = []
    for cat in CATEGORIES:
        p, r = style_in(last['pycodestyle'], cat), style_in(last['ruff'], cat)
        rows.append([cat, last['files'][cat], last['lines'][cat],
                     p, f"{p / last['pycodestyle']['style'] * 100:.0f}%", per_k(p, last['lines'][cat]),
                     r, f"{r / last['ruff']['style'] * 100:.0f}%", per_k(r, last['lines'][cat])])
    print(md_table(['category', 'files', 'lines', 'pycodestyle', 'share', '/k', 'ruff', 'share', '/k'], rows))

    if patches:
        print('\n## Sensitivity: every other release of a minor against its first\n')
        print('All the releases of a minor that are measured besides its first (patch releases, and pre-releases '
              'where a final is measured too): how far the whole-`Lib/` pycodestyle density strays from the '
              "minor's first release.\n")
        rows = []
        for base in series:
            others = sorted((v for v in patches if minor_of(v) == minor_of(base)), key=vkey)
            if not others:
                continue
            dens = {v: data[v]['pycodestyle']['style'] / sum(data[v]['lines'].values()) * 1000 for v in others}
            blines = sum(data[base]['lines'].values())
            bdens = data[base]['pycodestyle']['style'] / blines * 1000
            lo, hi = min(dens, key=dens.get), max(dens, key=dens.get)
            last = others[-1]
            rows.append([minor_of(base), base, f'{bdens:.1f}', len(others), f'{dens[lo]:.1f} ({lo})', f'{dens[hi]:.1f} ({hi})',
                         f'{dens[last]:.1f} ({last})', f'{max(abs(dens[v] - bdens) for v in others):.1f}'])
        print(md_table(['minor', 'first', '/k', 'others', 'lowest /k', 'highest /k', 'latest /k', 'largest drift'], rows))


def severity_table(data: dict, series: list[str], final: str) -> None:
    print('\n## Semantic against cosmetic rules, stdlib proper (pycodestyle, per thousand lines)\n')
    print('Semantic: E711 to E714, E721, E722, E731, E741 to E743 and the W6 deprecations, the rules about what '
          'the code does. Cosmetic: every other style rule, about how it is laid out.\n')
    rows = []
    for v in series:
        p, lines = data[v]['pycodestyle'], data[v]['lines']['stdlib']
        sem = semantic_in(p, 'stdlib')
        cos = style_in(p, 'stdlib') - sem
        rows.append([v, sem, per_k(sem, lines), cos, per_k(cos, lines)])
    print(md_table(['release', 'semantic', '/k', 'cosmetic', '/k'], rows))
    last = data[final]
    codes = {c: n for c, n in last['pycodestyle']['by_category_code'].get('stdlib', {}).items() if SEMANTIC.match(c)}
    rows = [[c, n, per_k(n, last['lines']['stdlib']), clean(last['pycodestyle']['messages'].get(c, ''))]
            for c, n in sorted(codes.items(), key=lambda kv: -kv[1])]
    print(f'\n### The semantic rules in {final}, stdlib proper\n')
    print(md_table(['rule', 'count', '/k', 'what it is'], rows))


def naming_tables(data: dict, series: list[str], final: str) -> None:
    if 'naming' not in data[final]:
        return
    last = data[final]
    print("\n## Naming (pep8-naming's rules through ruff, per thousand lines)\n")
    print(f"ruff {last['instruments']['naming']['version']} with `--isolated --select N` on the same files; "
          "pycodestyle has no naming rules. n/a where ruff cannot parse the release.\n")
    rows = []
    for v in series:
        d = data[v]
        if 'naming' not in d:
            continue
        if major(v) < 3:
            rows.append([v, 'n/a', 'n/a', 'n/a'])
            continue
        n = d['naming']
        rows.append([v, style_in(n, 'stdlib'), per_k(style_in(n, 'stdlib'), d['lines']['stdlib']),
                     per_k(style_in(n, 'tests'), d['lines']['tests'])])
    print(md_table(['release', 'stdlib', '/k', 'tests /k'], rows))
    codes = last['naming']['by_category_code'].get('stdlib', {})
    rows = [[c, n, per_k(n, last['lines']['stdlib']), clean(last['naming']['messages'].get(c, ''))]
            for c, n in sorted(codes.items(), key=lambda kv: -kv[1]) if not is_error(c)][:10]
    print(f'\n### Naming rules in the stdlib proper of {final}\n')
    print(md_table(['rule', 'count', '/k', 'what it is'], rows))


# --------------------------------------------------------------- the cohorts

def bucket_style(b: dict, inst: str = 'pycodestyle', prefix: str = '') -> int:
    return sum(n for code, n in b.get(inst, {}).get('by_code', {}).items() if code.startswith(prefix))


def bucket_semantic(b: dict) -> int:
    return sum(n for code, n in b['pycodestyle']['by_code'].items() if SEMANTIC.match(code))


def cohort_tables(version: str) -> None:
    path = DATA / 'cohorts' / f'{version}.json'
    if not path.exists():
        return
    c = json.loads(path.read_text())
    fam = ('E1', 'E2', 'E3', 'E5', 'E7')
    bl = c['blame']
    print(f"\n## Age cohorts of {version}: density by the date a line was last edited\n")
    print(f"Every line of `Lib/` at tag `{c['tag']}` (commit `{c['commit'][:10]}`) blamed with "
          f"`{bl['command']}`, dated by the commit's author time; a diagnostic belongs to the cohort of the "
          f"line it is reported on. {bl['files']} files blamed, {len(bl['skipped'])} skipped, "
          f"{bl['unattributed']['pycodestyle']} pycodestyle and {bl['unattributed']['ruff']} ruff diagnostics "
          f"unattributed. Rates are style diagnostics per thousand lines of the cohort.\n")
    stdlib, tests = c['by_category']['stdlib'], c['by_category']['tests']
    total = sum(b['lines'] for b in stdlib['eras'].values())
    names = [e['name'] for e in c['eras'] if e['name'] in stdlib['eras']]
    rows = []
    for era in c['eras']:
        name = era['name']
        if name not in stdlib['eras']:
            continue
        b = stdlib['eras'][name]
        t = tests['eras'].get(name, {'lines': 0, 'pycodestyle': {'by_code': {}}})
        rows.append([name, era['from'] or '', b['lines'], f"{b['lines'] / total * 100:.0f}%",
                     per_k(bucket_style(b), b['lines']), per_k(bucket_style(b) - bucket_style(b, prefix='E5'), b['lines']),
                     per_k(bucket_style(b, 'ruff'), b['lines']),
                     *[per_k(bucket_style(b, prefix=f), b['lines']) for f in fam],
                     t['lines'], per_k(bucket_style(t), t['lines']) if t['lines'] else 'n/a'])
    print('### By era, stdlib proper (and the test suite)\n')
    print(md_table(['era', 'from', 'lines', 'share', 'pycodestyle /k', 'excl. E5 /k', 'ruff /k', *fam,
                    'test lines', 'tests /k'], rows))

    print('\n### By year, stdlib proper\n')
    rows = []
    for year, b in stdlib['years'].items():
        t = tests['years'].get(year)
        rows.append([year, b['lines'], f"{b['lines'] / total * 100:.1f}%", bucket_style(b), per_k(bucket_style(b), b['lines']),
                     *[per_k(bucket_style(b, prefix=f), b['lines']) for f in fam],
                     t['lines'] if t else 0, per_k(bucket_style(t), t['lines']) if t and t['lines'] else 'n/a'])
    print(md_table(['year', 'lines', 'share', 'pycodestyle', '/k', *fam, 'test lines', 'tests /k'], rows))

    print('\n### Rules by era, stdlib proper (pycodestyle, per thousand lines of the era)\n')
    overall: dict[str, int] = {}
    for b in stdlib['eras'].values():
        for code, n in b['pycodestyle']['by_code'].items():
            overall[code] = overall.get(code, 0) + n
    top = sorted(overall, key=lambda k: -overall[k])[:12]
    rows = [[code, *[per_k(stdlib['eras'][n]['pycodestyle']['by_code'].get(code, 0), stdlib['eras'][n]['lines'])
                     for n in names]] for code in top]
    print(md_table(['rule', *names], rows))

    has_naming = any('naming' in b for b in stdlib['eras'].values())
    print('\n### Semantic, cosmetic and naming rules by era, stdlib proper (per thousand lines)\n')
    rows = []
    for n in names:
        b = stdlib['eras'][n]
        sem = bucket_semantic(b)
        row = [n, per_k(sem, b['lines']), per_k(bucket_style(b) - sem, b['lines'])]
        row.append(per_k(bucket_style(b, 'naming'), b['lines']) if has_naming else 'n/a')
        rows.append(row)
    print(md_table(['era', 'semantic /k', 'cosmetic /k', 'naming /k'], rows))


def dating_table(version: str) -> None:
    a_path, b_path = DATA / 'cohorts' / f'{version}.json', DATA / 'cohorts' / f'{version}-content.json'
    if not (a_path.exists() and b_path.exists()):
        return
    a, b = json.loads(a_path.read_text()), json.loads(b_path.read_text())
    print(f"\n### Two datings of {version}, stdlib proper: last edit against content\n")
    print(f"Content dating blames with `{' '.join(b['dating']['flags'])}`: whitespace-only edits are ignored and "
          "lines moved or copied between files keep their origin. A line changes era when the edit that last "
          "touched it was cosmetic, or when it arrived by a move.\n")
    sa, sb = a['by_category']['stdlib']['eras'], b['by_category']['stdlib']['eras']
    ta, tb = sum(x['lines'] for x in sa.values()), sum(x['lines'] for x in sb.values())
    rows = []
    for e in a['eras']:
        n = e['name']
        if n not in sa or n not in sb:
            continue
        x, y = sa[n], sb[n]
        rows.append([n, x['lines'], f"{x['lines'] / ta * 100:.0f}%", y['lines'], f"{y['lines'] / tb * 100:.0f}%",
                     per_k(bucket_style(x), x['lines']), per_k(bucket_style(y), y['lines']),
                     per_k(bucket_style(x) - bucket_style(x, prefix='E5'), x['lines']),
                     per_k(bucket_style(y) - bucket_style(y, prefix='E5'), y['lines'])])
    print(md_table(['era', 'lines (last edit)', 'share', 'lines (content)', 'share', '/k (last edit)', '/k (content)',
                    'excl. E5 (last edit)', 'excl. E5 (content)'], rows))


def sensitivity_table(version: str) -> None:
    path = DATA / 'sensitivity' / f'{version}.json'
    if not path.exists():
        return
    s = json.loads(path.read_text())
    print(f"\n### Sensitivity of the era densities, stdlib proper of {version}\n")
    print(f"Bootstrap over files ({s['resamples']} resamples of the {s['files']} files with replacement, seed {s['seed']}): "
          "the 95% interval is the 2.5th to 97.5th percentile of the resampled density. `earlier` and `later` move "
          "every era boundary a year that way. `per k source lines` leaves out blank and comment lines.\n")
    rows = []
    for name, e in s['eras'].items():
        rows.append([name, e['per_k'], f"[{e['ci95'][0]}, {e['ci95'][1]}]", e['per_k_excl_e5'],
                     f"[{e['ci95_excl_e5'][0]}, {e['ci95_excl_e5'][1]}]",
                     s['shifted']['earlier'][name]['per_k'], s['shifted']['later'][name]['per_k'], e['per_k_sloc']])
    print(md_table(['era', '/k', '95% interval', 'excl. E5 /k', '95% interval', 'earlier', 'later', 'per k source lines'], rows))


# ------------------------------------------------------------ the other views

def linelength_tables(data: dict, series: list[str], version: str) -> None:
    ll = load_dir('linelength')
    if not ll:
        return
    print('\n## Line length: where the long lines sit\n')
    print("Physical line length in characters after decoding, trailing whitespace stripped, a tab counting one, "
          "as pycodestyle measures E501; stdlib proper. `doc > 72` is pycodestyle's W505 with "
          "`--max-doc-length=72`, PEP 8's limit for docstrings and comments, per thousand lines.\n")
    rows = []
    for v in series:
        if v not in ll:
            continue
        s = ll[v]['by_category']['stdlib']
        L = s['lines']
        q = s['long_percentiles']
        rows.append([v, L, pct(s['over']['79'], L), pct(s['over']['88'], L), pct(s['over']['99'], L), pct(s['over']['120'], L),
                     q['p50'], q['p90'], q['max'], per_k(s['doc_over_72'], L)])
    print(md_table(['release', 'lines', '> 79', '> 88', '> 99', '> 120', 'p50 of long', 'p90 of long', 'longest', 'doc > 72 /k'], rows))
    if version in ll and ll[version].get('by_era'):
        print(f'\n### By era of last edit, stdlib proper of {version}\n')
        rows = []
        for name, s in ll[version]['by_era']['stdlib'].items():
            L = s['lines']
            q = s['long_percentiles']
            rows.append([name, L, pct(s['over']['79'], L), pct(s['over']['88'], L), pct(s['over']['99'], L), pct(s['over']['120'], L),
                         q['p50'], q['p90'], q['max'], per_k(s['doc_over_72'], L)])
        print(md_table(['era', 'lines', '> 79', '> 88', '> 99', '> 120', 'p50 of long', 'p90 of long', 'longest', 'doc > 72 /k'], rows))


def enforcement_table(version: str) -> None:
    path = DATA / 'enforcement' / f'{version}.json'
    if not path.exists():
        return
    e = json.loads(path.read_text())
    print(f"\n## What CPython enforces: its ruff hooks in {version}\n")
    print(f"From `.pre-commit-config.yaml` (ruff-pre-commit `{e['ruff_pre_commit_rev']}`), each ruff hook, the tree it covers, "
          "and the rules the tree's own `.ruff.toml` chain selects (ruff's defaults E4, E7, E9, F where none does). "
          "Counted with the ruff pinned here: in the tree under CPython's configuration (what the hook checks), in the "
          "tree with the configuration ignored, and in the library proper, where no hook runs.\n")
    rows = []
    for h in e['hooks']:
        if 'select' not in h:
            rows.append([h['name'] or '', h['files'] or '', h.get('note', ''), '', '', '', '', ''])
            continue
        rows.append([h['name'] or '', h['tree'], ', '.join(h['select']) + (f" minus {', '.join(h['ignore'])}" if h['ignore'] else '')
                     + f" at {h.get('line_length', 88)} columns",
                     h['tree_lines'], h['in_tree_own_config'], h['in_tree_isolated'],
                     h['in_stdlib_isolated'], per_k(h['in_stdlib_isolated'], h['stdlib_lines'])])
    print(md_table(['hook', 'tree', 'rules', 'tree lines', 'own config', 'isolated', 'Lib proper', '/k'], rows))


def survival_tables() -> None:
    sv = load_dir('survival')
    if not sv:
        return
    for key, s in sorted(sv.items()):
        st, L = s['start'], s['lines']['stdlib']
        print(f"\n## Survival: the violations of the {s['from']} branch point in {s['to']}\n")
        print(f"Start: commit `{st['commit'][:10]}` ({st['date']}{', tag ' + st['tag'] if st.get('tag') else ''}), the merge base of "
              f"v{s['from']} and v{s['to']}; its `Lib/` measured with pycodestyle as everywhere else. Every line reverse-blamed with "
              f"`{s['blame']['command']}`: a line reported under the end commit is unchanged in {s['to']}, at a known place; "
              f"otherwise it was edited or removed. A surviving violation is one whose line is unchanged and still carries the same "
              f"rule in {s['to']}'s own diagnostics. Stdlib proper of the start; {s['blame']['files']} files, {len(s['blame']['skipped'])} skipped.\n")
        rules = s['rules']
        n_all = sum(r['n'] for r in rules.values())
        ls_all = sum(r.get('line_survived', 0) for r in rules.values())
        vs_all = sum(r.get('violation_survived', 0) for r in rules.values())
        rows = [['all lines', L['total'], L['survived'], pct(L['survived'], L['total']), '', ''],
                ['all violations', n_all, ls_all, pct(ls_all, n_all), vs_all, pct(vs_all, n_all)]]
        for code, r in sorted(rules.items(), key=lambda kv: -kv[1]['n'])[:14]:
            rows.append([code, r['n'], r.get('line_survived', 0), pct(r.get('line_survived', 0), r['n']),
                         r.get('violation_survived', 0), pct(r.get('violation_survived', 0), r['n'])])
        print(md_table(['', 'at start', 'line unchanged', 'share', 'violation still there', 'share'], rows))


def packages_table(version: str) -> None:
    path = DATA / 'packages' / f'{version}.json'
    if not path.exists():
        return
    p = json.loads(path.read_text())
    print(f"\n## Packages of the stdlib proper, {version} (pycodestyle)\n")
    v = p['vendored']
    print(f"Vendored, meaning maintained outside CPython and synced in: {', '.join(f'`{k}` ({o})' for k, o in v['set'].items())}. "
          f"Together {v['lines']} lines at {v['per_k']} per thousand; the library proper without them is "
          f"{p['stdlib_without_vendored']['per_k']} against {p['stdlib']['per_k']} with.\n")
    big = [x for x in p['packages'] if x['lines'] >= 300]
    rows = [[x['name'], x['kind'], x['files'], x['lines'], x['style'], x['per_k']] for x in big[:12]]
    print('### The twelve densest packages and modules of at least 300 lines\n')
    print(md_table(['name', 'kind', 'files', 'lines', 'pycodestyle', '/k'], rows))
    rows = [[x['name'], x['kind'], x['files'], x['lines'], x['style'], x['per_k']] for x in big[-8:]]
    print('\n### The eight cleanest\n')
    print(md_table(['name', 'kind', 'files', 'lines', 'pycodestyle', '/k'], rows))


def baselines_table(data: dict, version: str) -> None:
    bl = load_dir('baselines')
    if not bl:
        return
    print('\n## Baselines: the same instruments on other code bases\n')
    print("Each project's current sdist from PyPI, its own source tree measured exactly as `Lib/` is (same file rules, "
          "categories and flags; ruff's target version py310). `proper` is the tree without its tests and generated files. "
          "pip's `_vendor` is left out. CPython's row is the stdlib proper of the latest series release.\n")
    d = data[version]
    rows = [[f'CPython {version} Lib/', '', d['lines']['stdlib'], per_k(style_in(d['pycodestyle'], 'stdlib'), d['lines']['stdlib']),
             per_k(style_in(d['pycodestyle'], 'stdlib') - style_in(d['pycodestyle'], 'stdlib', 'E5'), d['lines']['stdlib']),
             per_k(style_in(d['ruff'], 'stdlib'), d['lines']['stdlib']),
             per_k(style_in(d['naming'], 'stdlib'), d['lines']['stdlib']) if 'naming' in d else 'n/a',
             per_k(style_in(d['pycodestyle'], 'tests'), d['lines']['tests'])]]
    for name, b in sorted(bl.items()):
        L = b['lines']['stdlib']
        rows.append([name, b['version'], L, per_k(style_in(b['pycodestyle'], 'stdlib'), L),
                     per_k(style_in(b['pycodestyle'], 'stdlib') - style_in(b['pycodestyle'], 'stdlib', 'E5'), L),
                     per_k(style_in(b['ruff'], 'stdlib'), L), per_k(style_in(b['naming'], 'stdlib'), L),
                     per_k(style_in(b['pycodestyle'], 'tests'), b['lines']['tests'])])
    print(md_table(['project', 'version', 'proper lines', 'pycodestyle /k', 'excl. E5 /k', 'ruff /k', 'naming /k', 'tests /k'], rows))


def main() -> None:
    data = {p.stem: json.loads(p.read_text()) for p in MEASUREMENTS.glob('*.json')}
    if not data:
        raise SystemExit('no measurements yet: run `make measure`')
    series = select_series(list(data))
    patches = sorted((v for v in data if v not in series), key=vkey)
    latest = [v for v in series if not is_prerelease(v)][-1]  # the per-release views use the latest final
    series_tables(data, series, patches, latest)
    severity_table(data, series, latest)
    naming_tables(data, series, latest)
    cohort_tables(latest)
    dating_table(latest)
    sensitivity_table(latest)
    linelength_tables(data, series, latest)
    enforcement_table(latest)
    survival_tables()
    packages_table(latest)
    baselines_table(data, latest)


if __name__ == '__main__':
    main()
