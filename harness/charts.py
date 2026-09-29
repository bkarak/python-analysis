#!/usr/bin/env python3
"""The charts of RESULTS.md and the follow-up post, as SVG, from data/.

    uv run harness/charts.py [--hero DIR]

Writes data/charts/*.svg (light, for RESULTS.md and the post's figures) and,
with --hero, a dark 1600x900 hero image into DIR. Hand-written SVG, no
dependencies. Colours are the validated default palette of the dataviz
method (blue, orange, aqua; validated for light and dark surfaces); text
wears ink tokens, never a series colour. Release dates are the CPython tag
dates in work/cpython, cached in data/release-dates.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from versions import is_prerelease, numeric, select_series, vkey  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
OUT = DATA / 'charts'
CPYTHON = ROOT / 'work' / 'cpython'
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

LIGHT = {'surface': '#fcfcfb', 'ink': '#0b0b0b', 'ink2': '#52514e', 'muted': '#898781', 'grid': '#e1e0d9',
         'axis': '#c3c2b7', 'blue': '#2a78d6', 'orange': '#eb6834', 'aqua': '#1baf7a'}
DARK = {'surface': '#0b1220', 'ink': '#e2e8f0', 'ink2': '#94a3b8', 'muted': '#64748b', 'grid': '#1e293b',
        'axis': '#334155', 'blue': '#3987e5', 'orange': '#d95926', 'aqua': '#199e70'}

# The November 2025 post's per-minor averages ("Found N errors" of ruff 0.14.4
# --select E,W on Lib/, averaged over the patch releases of each minor), as
# published; validation/README.md reproduces them.
NOVEMBER = {'3.0': 4479, '3.1': 4619, '3.2': 4811.83, '3.3': 4999.75, '3.4': 5278, '3.5': 5377.36,
            '3.6': 4937.81, '3.7': 5134.17, '3.8': 5461, '3.9': 5745.69, '3.10': 5964.4, '3.11': 6130.53,
            '3.12': 6112.54, '3.13': 8403, '3.14': 16560}


# ------------------------------------------------------------------ helpers

def esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text(x: float, y: float, s: str, size: int = 14, fill: str = '#000', anchor: str = 'start',
         weight: str = 'normal', extra: str = '') -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


def line(x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 1, extra: str = '') -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}" {extra}/>'


def polyline(points: list[tuple[float, float]], stroke: str, width: float = 2) -> str:
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'


def dot(x: float, y: float, r: float, fill: str, extra: str = '') -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" {extra}/>'


def bar_top_rounded(x: float, y: float, w: float, h: float, fill: str, r: float = 4) -> str:
    """A vertical bar with 4px rounded data-ends (the top) anchored to the baseline."""
    if h <= 0:
        return ''
    r = min(r, w / 2, h)
    return (f'<path d="M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + w - r:.1f} '
            f'Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z" fill="{fill}"/>')


def bar_right_rounded(x: float, y: float, w: float, h: float, fill: str, r: float = 4) -> str:
    if w <= 0:
        return ''
    r = min(r, h / 2, w)
    return (f'<path d="M{x:.1f},{y:.1f} H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h - r:.1f} '
            f'Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f} H{x:.1f} Z" fill="{fill}"/>')


def svg(width: int, height: int, body: list[str], surface: str, title: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n'
            f'<rect width="{width}" height="{height}" fill="{surface}"/>\n' + '\n'.join(b for b in body if b) + '\n</svg>\n')


def nice_ticks(vmax: float, n: int = 5) -> list[float]:
    raw = vmax / n
    step = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= step * m:
            step *= m
            break
    ticks, t = [], 0.0
    while t <= vmax + 1e-9:
        ticks.append(t)
        t += step
    return ticks


def legend(x: float, y: float, items: list[tuple[str, str]], c: dict, size: int = 14) -> list[str]:
    out = []
    for label, colour in items:
        out.append(f'<rect x="{x:.1f}" y="{y - 10:.1f}" width="14" height="14" rx="3" fill="{colour}"/>')
        out.append(text(x + 20, y + 2, label, size, c['ink2']))
        x += 20 + len(label) * size * 0.56 + 24
    return out


# --------------------------------------------------------------------- data

def load_measurements() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in (DATA / 'measurements').glob('*.json')}


def style_in(inst: dict, cat: str, prefix: str = '') -> int:
    return sum(n for c, n in inst['by_category_code'].get(cat, {}).items()
               if not (c.startswith('E9') or c == 'invalid-syntax') and c.startswith(prefix))


STAND_IN = {'2.0.1': 'v2.0'}  # 2.0.1 stands in for 2.0 and is plotted at 2.0's release


def tag_date(tag: str) -> str | None:
    proc = subprocess.run(['git', '-C', str(CPYTHON), 'log', '-1', '--format=%cs', tag], capture_output=True, text=True)
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def upload_date(v: str) -> str | None:
    """The tarball's Last-Modified on python.org, for the few releases whose tag is missing."""
    req = urllib.request.Request(f'https://www.python.org/ftp/python/{numeric(v)}/Python-{v}.tgz', method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            lm = r.headers.get('Last-Modified')
        return parsedate_to_datetime(lm).date().isoformat() if lm else None
    except OSError:
        return None


def release_dates(versions: list[str]) -> dict[str, date]:
    cache = DATA / 'release-dates.json'
    known = json.loads(cache.read_text()) if cache.exists() else {}
    changed = False
    for v in versions:
        if v in known:
            continue
        found = tag_date(STAND_IN.get(v, f'v{v}')) or upload_date(v)
        if found:
            known[v] = found
            changed = True
    if changed:
        cache.write_text(json.dumps(dict(sorted(known.items(), key=lambda kv: vkey(kv[0]))), indent=1) + '\n')
    return {v: date.fromisoformat(d) for v, d in known.items() if v in versions}


def dens(d: dict, cat: str, prefix: str = '') -> float:
    return style_in(d['pycodestyle'], cat, prefix) / d['lines'][cat] * 1000


# ------------------------------------------------------------------ figures

def fig_series(data: dict, c: dict = LIGHT) -> str:
    W, H = 1200, 640
    L, R, T, B = 70, 90, 70, 60
    series = select_series(list(data))
    others = [v for v in data if v not in series]
    dates = release_dates(list(data))
    versions = [v for v in data if v in dates]
    d0, d1 = date(2000, 7, 1), date(2027, 1, 1)
    span = (d1 - d0).days
    ymax = 280

    def X(dt: date) -> float:
        return L + (dt - d0).days / span * (W - L - R)

    def Y(v: float) -> float:
        return T + (H - T - B) * (1 - v / ymax)

    body = [text(L, 36, 'PEP 8 style diagnostics per thousand lines of Lib/, pycodestyle at 79 columns', 18, c['ink'], weight='600'),
            text(L, 56, 'One point per minor release, first release of each; small dots are every other release measured', 13, c['ink2'])]
    for t in nice_ticks(ymax, 6):
        body.append(line(L, Y(t), W - R, Y(t), c['grid']))
        body.append(text(L - 8, Y(t) + 5, f'{t:.0f}', 12, c['muted'], 'end', extra='style="font-variant-numeric: tabular-nums"'))
    for yr in range(2002, 2027, 4):
        x = X(date(yr, 1, 1))
        body.append(line(x, H - B, x, H - B + 5, c['axis']))
        body.append(text(x, H - B + 20, str(yr), 12, c['muted'], 'middle'))
    body.append(line(L, H - B, W - R, H - B, c['axis']))
    for cat, colour, label in (('stdlib', c['blue'], 'Library proper'), ('tests', c['orange'], 'Test suite')):
        for v in others:
            if v in dates:
                body.append(dot(X(dates[v]), Y(dens(data[v], cat)), 3.5, colour, 'opacity="0.4"'))
        for major_ in ('2', '3'):
            branch = sorted((v for v in series if v in dates and v.startswith(major_ + '.')), key=lambda v: dates[v])
            body.append(polyline([(X(dates[v]), Y(dens(data[v], cat))) for v in branch], colour))
        for v in series:
            if v not in dates:
                continue
            x, y = X(dates[v]), Y(dens(data[v], cat))
            body.append(dot(x, y, 4.5, c['surface'], f'stroke="{colour}" stroke-width="2"')
                        if is_prerelease(v) else dot(x, y, 4.5, colour))
        first, last = series[0], series[-1]
        body.append(text(X(dates[first]) + 10, Y(dens(data[first], cat)) + 5, f'{dens(data[first], cat):.0f}', 13, c['ink2']))
        body.append(text(X(dates[last]) + 12, Y(dens(data[last], cat)) + 5, f'{dens(data[last], cat):.1f}', 13, c['ink2']))
    for v, label in (('2.0.1', '2.0 (as 2.0.1)'), ('2.7', '2.7'), ('3.0', '3.0'), ('3.14.0', '3.14.0')):
        if v in dates and v in data:
            body.append(text(X(dates[v]), H - B + 38, label, 12, c['ink2'], 'middle'))
    body += legend(W - R - 320, T + 8, [('Library proper', c['blue']), ('Test suite', c['orange'])], c)
    return svg(W, H, body, c['surface'], 'PEP 8 style diagnostics per thousand lines of Lib/, by release')


def fig_families(data: dict, c: dict = LIGHT) -> str:
    W, H = 1200, 420
    fams = [('E1', 'Indentation'), ('E2', 'Whitespace'), ('E3', 'Blank lines'), ('E5', 'Line length'), ('E7', 'Statements')]
    series = select_series(list(data))
    dates = release_dates(series)
    series = [v for v in series if v in dates]
    d0, d1 = date(2000, 7, 1), date(2027, 1, 1)
    ymax = 110
    n = len(fams)
    gap, L, R, T, B = 28, 50, 20, 100, 50
    pw = (W - L - R - gap * (n - 1)) / n
    body = [text(L, 36, 'Rule families in the library proper, per thousand lines', 18, c['ink'], weight='600'),
            text(L, 56, 'pycodestyle at 79 columns, first release of each minor, 2.0.1 to 3.15rc2; the one family that rises is line length', 13, c['ink2'])]
    for i, (fam, name) in enumerate(fams):
        x0 = L + i * (pw + gap)
        colour = c['orange'] if fam == 'E5' else c['blue']

        def X(dt: date) -> float:
            return x0 + (dt - d0).days / (d1 - d0).days * pw

        def Y(v: float) -> float:
            return T + (H - T - B) * (1 - v / ymax)

        for t in (0, 25, 50, 75, 100):
            body.append(line(x0, Y(t), x0 + pw, Y(t), c['grid']))
            if i == 0:
                body.append(text(x0 - 8, Y(t) + 4, str(t), 11, c['muted'], 'end'))
        body.append(line(x0, H - B, x0 + pw, H - B, c['axis']))
        body.append(text(x0, T - 12, f'{fam}  {name}', 13, c['ink2'], weight='600'))
        for major_ in ('2', '3'):
            branch = sorted((v for v in series if v.startswith(major_ + '.')), key=lambda v: dates[v])
            body.append(polyline([(X(dates[v]), Y(dens(data[v], 'stdlib', fam))) for v in branch], colour))
        for v in series:
            body.append(dot(X(dates[v]), Y(dens(data[v], 'stdlib', fam)), 3, colour))
        for v, anchor, dx in ((series[0], 'start', 6), (series[-1], 'end', -6)):
            y = dens(data[v], 'stdlib', fam)
            body.append(text(X(dates[v]) + dx, Y(y) - 8, f'{y:.1f}', 11, c['ink2'], anchor))
        for yr in (2001, 2013, 2025):
            body.append(text(X(date(yr, 1, 1)), H - B + 18, str(yr), 11, c['muted'], 'middle'))
    return svg(W, H, body, c['surface'], 'Rule families in the library proper, per thousand lines, by release')


def fig_eras(c: dict = LIGHT) -> str:
    W, H = 1200, 520
    co = json.loads((DATA / 'cohorts' / '3.14.0.json').read_text())
    sens_path = DATA / 'sensitivity' / '3.14.0.json'
    sens = json.loads(sens_path.read_text())['eras'] if sens_path.exists() else {}
    eras = [e['name'] for e in co['eras']]
    st = co['by_category']['stdlib']['eras']
    L, R, T, B = 70, 40, 110, 80
    ymax = 90
    n = len(eras)
    slot = (W - L - R) / n
    bw = slot * 0.5

    def Y(v: float) -> float:
        return T + (H - T - B) * (1 - v / ymax)

    body = [text(L, 36, 'Library proper of 3.14.0 by the era in which each line was last edited', 18, c['ink'], weight='600'),
            text(L, 56, 'Style diagnostics per thousand lines of the cohort, pycodestyle; the line-length rule stacked on top of everything else', 13, c['ink2'])]
    for t in nice_ticks(ymax, 4):
        body.append(line(L, Y(t), W - R, Y(t), c['grid']))
        body.append(text(L - 8, Y(t) + 4, f'{t:.0f}', 12, c['muted'], 'end'))
    body.append(line(L, H - B, W - R, H - B, c['axis']))
    for i, name in enumerate(eras):
        b = st[name]
        total = sum(n for k, n in b['pycodestyle']['by_code'].items()) / b['lines'] * 1000
        e5 = sum(n for k, n in b['pycodestyle']['by_code'].items() if k.startswith('E5')) / b['lines'] * 1000
        base = total - e5
        x = L + i * slot + (slot - bw) / 2
        body.append(bar_top_rounded(x, Y(base), bw, Y(0) - Y(base), c['blue'], 0))
        body.append(bar_top_rounded(x, Y(total), bw, Y(base) - Y(total) - 2, c['orange']))
        body.append(text(x + bw / 2, Y(total) - 10, f'{total:.1f}', 13, c['ink'], 'middle', '600'))
        body.append(text(x + bw / 2, Y(base) + 18 if Y(0) - Y(base) > 30 else Y(base) - 4, f'{base:.1f}', 12, c['surface'] if Y(0) - Y(base) > 30 else c['ink2'], 'middle'))
        if name in sens and sens[name].get('ci95_excl_e5'):
            lo, hi = sens[name]['ci95_excl_e5']
            xm = x + bw + 8
            body.append(line(xm, Y(lo), xm, Y(hi), c['ink2'], 1.5))
            body.append(line(xm - 3, Y(lo), xm + 3, Y(lo), c['ink2'], 1.5))
            body.append(line(xm - 3, Y(hi), xm + 3, Y(hi), c['ink2'], 1.5))
        frm = next(e['from'] for e in co['eras'] if e['name'] == name)
        share = b['lines'] / sum(v['lines'] for v in st.values()) * 100
        body.append(text(x + bw / 2, H - B + 22, name, 13, c['ink2'], 'middle', '600'))
        body.append(text(x + bw / 2, H - B + 40, (f'from {frm}' if frm else 'up to 2001-07-04') + f' · {share:.0f}% of lines', 12, c['muted'], 'middle'))
    body += legend(L, T - 26, [('Every other rule', c['blue']), ('Line length (E5)', c['orange'])], c)
    body.append(text(W - R, T - 26, 'whisker: 95% bootstrap interval of the blue part', 12, c['muted'], 'end'))
    return svg(W, H, body, c['surface'], 'Library proper of 3.14.0 by era of last edit, per thousand lines')


def fig_baselines(data: dict, c: dict = LIGHT) -> str:
    W, H = 1200, 420
    rows = []
    latest = select_series(list(data))[-1]
    for v in (latest, ):
        if is_prerelease(v):
            v = [s for s in select_series(list(data)) if not is_prerelease(s)][-1]
        d = data[v]
        rows.append((f'CPython {v} Lib/', dens(d, 'stdlib'), dens(d, 'stdlib', 'E5')))
    for p in sorted((DATA / 'baselines').glob('*.json')):
        b = json.loads(p.read_text())
        rows.append((f"{b['project']} {b['version']}", dens(b, 'stdlib'), dens(b, 'stdlib', 'E5')))
    rows.sort(key=lambda r: -(r[1] - r[2]))
    L, R, T, B = 200, 60, 96, 40
    xmax = 60
    rh = (H - T - B) / len(rows)
    bh = rh * 0.55

    def X(v: float) -> float:
        return L + v / xmax * (W - L - R)

    body = [text(30, 36, 'Against five other code bases, per thousand lines of each project’s own source', 18, c['ink'], weight='600'),
            text(30, 56, 'Same instrument and flags, 79 columns; the line-length rule stacked on top of everything else', 13, c['ink2'])]
    for t in nice_ticks(xmax, 6):
        body.append(line(X(t), T, X(t), H - B, c['grid']))
        body.append(text(X(t), H - B + 18, f'{t:.0f}', 12, c['muted'], 'middle'))
    for i, (name, total, e5) in enumerate(rows):
        y = T + i * rh + (rh - bh) / 2
        base = total - e5
        body.append(f'<rect x="{X(0):.1f}" y="{y:.1f}" width="{X(base) - X(0):.1f}" height="{bh:.1f}" fill="{c["blue"]}"/>')
        body.append(bar_right_rounded(X(base) + 2, y, X(total) - X(base) - 2, bh, c['orange']))
        body.append(text(L - 12, y + bh / 2 + 5, name, 13, c['ink'], 'end'))
        body.append(text(X(total) + 8, y + bh / 2 + 5, f'{total:.1f}  ({base:.1f} without line length)', 12, c['ink2']))
    body += legend(L, T - 18, [('Every other rule', c['blue']), ('Line length (E5)', c['orange'])], c)
    return svg(W, H, body, c['surface'], 'Density against five other code bases, per thousand lines')


def fig_where(data: dict, c: dict = LIGHT) -> str:
    W, H = 1200, 300
    v = [s for s in select_series(list(data)) if not is_prerelease(s)][-1]
    d = data[v]
    cats = [('stdlib', 'Library proper', c['blue']), ('tests', 'Test suite', c['orange']), ('generated', 'Generated files', c['aqua'])]
    lines_tot = sum(d['lines'].values())
    diag_tot = sum(style_in(d['pycodestyle'], k) for k, _, _ in cats)
    rows = [('Lines', {k: d['lines'][k] / lines_tot for k, _, _ in cats}),
            ('Diagnostics', {k: style_in(d['pycodestyle'], k) / diag_tot for k, _, _ in cats})]
    L, R, T, B = 150, 40, 80, 30
    bh = 56
    body = [text(30, 36, f'Where the lines are, and where the diagnostics are: Lib/ of {v}', 18, c['ink'], weight='600'),
            text(30, 56, 'Shares of physical lines and of pycodestyle style diagnostics, by category', 13, c['ink2'])]
    for i, (label, shares) in enumerate(rows):
        y = T + i * (bh + 24)
        x = L
        body.append(text(L - 12, y + bh / 2 + 5, label, 14, c['ink'], 'end', '600'))
        for k, name, colour in cats:
            w = shares[k] * (W - L - R)
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w - 2, 0):.1f}" height="{bh}" fill="{colour}"/>')
            if w > 70:
                body.append(text(x + w / 2, y + bh / 2 + 5, f'{shares[k] * 100:.0f}%', 14, c['surface'], 'middle', '600'))
            else:
                body.append(text(x + w / 2, y - 6, f'{shares[k] * 100:.1f}%', 12, c['ink2'], 'middle'))
            x += w
    body += legend(L, H - 12, [(name, colour) for _, name, colour in cats], c)
    return svg(W, H, body, c['surface'], 'Shares of lines and of diagnostics by category')


def hero(data: dict, c: dict = DARK) -> str:
    W, H = 1600, 900
    series = [v for v in select_series(list(data)) if v.startswith('3.') and not is_prerelease(v) and v in data]
    minors = ['.'.join(v.split('.')[:2]) for v in series]
    corrected = [dens(data[v], 'stdlib') for v in series]
    idx_c = [x / corrected[0] * 100 for x in corrected]
    idx_n = [NOVEMBER[m] / NOVEMBER['3.0'] * 100 for m in minors]
    L, R, T, B = 110, 90, 250, 110
    ymax = 400
    n = len(minors)

    def X(i: int) -> float:
        return L + i / (n - 1) * (W - L - R)

    def Y(v: float) -> float:
        return T + (H - T - B) * (1 - v / ymax)

    body = [text(L, 92, 'Python PEP8: Practice what you preach, take two', 44, c['ink'], weight='700'),
            text(L, 138, 'The same standard library, two rulers. Both series start at 100 in Python 3.0.', 22, c['ink2']),
            text(L, 168, 'November 2025: a raw count of 25 ruff rules at 88 columns, whole Lib/ · This time: pycodestyle at 79 columns, per thousand lines, library proper', 17, c['muted'])]
    for t in (0, 100, 200, 300, 400):
        body.append(line(L, Y(t), W - R, Y(t), c['grid']))
        body.append(text(L - 14, Y(t) + 6, str(t), 15, c['muted'], 'end'))
    body.append(line(L, Y(100), W - R, Y(100), c['axis'], 1.5))
    for i, m in enumerate(minors):
        body.append(text(X(i), H - B + 30, m, 15, c['muted'], 'middle'))
    ix = minors.index('3.13')
    body.append(line(X(ix) + (X(ix + 1) - X(ix)) * 0.55, T - 10, X(ix) + (X(ix + 1) - X(ix)) * 0.55, H - B, c['axis'], 1, 'stroke-dasharray="4 6"'))
    body.append(text(X(ix) + (X(ix + 1) - X(ix)) * 0.55 - 12, T + 16, 'from 3.13.8 the tarball ships a .ruff.toml: 79 columns', 15, c['ink2'], 'end'))
    body.append(text(X(ix) + (X(ix + 1) - X(ix)) * 0.55 - 12, T + 38, 'the ruler changed, not the library', 15, c['ink2'], 'end'))
    body.append(polyline([(X(i), Y(v)) for i, v in enumerate(idx_n)], c['orange'], 3))
    body.append(polyline([(X(i), Y(v)) for i, v in enumerate(idx_c)], c['blue'], 3))
    for i in range(n):
        body.append(dot(X(i), Y(idx_n[i]), 5.5, c['orange']))
        body.append(dot(X(i), Y(idx_c[i]), 5.5, c['blue']))
    body.append(text(X(n - 1) + 14, Y(idx_n[-1]) + 7, f'{idx_n[-1]:.0f}', 20, c['ink'], weight='600'))
    body.append(text(X(n - 1) + 14, Y(idx_c[-1]) + 7, f'{idx_c[-1]:.0f}', 20, c['ink'], weight='600'))
    body += legend(L, T - 60, [('November 2025, the count that said the quality is falling', c['orange']),
                              ('This measurement: PEP 8 density, halving', c['blue'])], c, 17)
    return svg(W, H, body, c['surface'], 'The same standard library under two rulers, indexed to Python 3.0')


def main() -> None:
    argv = sys.argv[1:]
    hero_dir = None
    if '--hero' in argv:
        i = argv.index('--hero')
        hero_dir = Path(argv[i + 1])
    data = load_measurements()
    OUT.mkdir(parents=True, exist_ok=True)
    figures = {
        'series': fig_series(data), 'families': fig_families(data), 'eras': fig_eras(),
        'baselines': fig_baselines(data), 'where': fig_where(data),
    }
    for name, content in figures.items():
        (OUT / f'{name}.svg').write_text(content)
        print(f'wrote {OUT / name}.svg ({len(content)} bytes)')
    if hero_dir:
        hero_dir.mkdir(parents=True, exist_ok=True)
        (hero_dir / 'hero.svg').write_text(hero(data))
        print(f'wrote {hero_dir / "hero.svg"}')


if __name__ == '__main__':
    main()
