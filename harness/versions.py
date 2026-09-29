"""Version strings as python.org spells them: '3.14.0', '3.0', '2.0.1', '3.15.0rc2'."""
from __future__ import annotations

import re

_PATTERN = re.compile(r'^(\d+)\.(\d+)(?:\.(\d+))?(?:(a|b|rc)(\d+))?$')
_RANK = {'a': 0, 'b': 1, 'rc': 2, None: 3}
SERIES_EXTRA = {'2.0.1'}  # python.org has no Python-2.0.tgz; the first patch release stands in for 2.0


def parse(v: str) -> tuple[int, int, int, str | None, int]:
    m = _PATTERN.match(v)
    if not m:
        raise ValueError(f'not a python.org version: {v!r}')
    major, minor, patch, pre, n = m.groups()
    return int(major), int(minor), int(patch or 0), pre, int(n or 0)


def vkey(v: str) -> tuple[int, ...]:
    """Sortable; a pre-release sorts before its final."""
    major, minor, patch, pre, n = parse(v)
    return major, minor, patch, _RANK[pre], n


def numeric(v: str) -> str:
    """The release directory on python.org: '3.15.0rc2' -> '3.15.0'."""
    major, minor, patch, _pre, _n = parse(v)
    return f'{major}.{minor}.{patch}' if '.' in v[len(f'{major}.{minor}'):] else f'{major}.{minor}'


def minor_of(v: str) -> str:
    major, minor, *_ = parse(v)
    return f'{major}.{minor}'


def is_prerelease(v: str) -> bool:
    return parse(v)[3] is not None


def is_first_of_minor(v: str) -> bool:
    """x.y or x.y.0, final or pre-release, plus the stand-ins in SERIES_EXTRA."""
    return v in SERIES_EXTRA or parse(v)[2] == 0


def select_series(versions: list[str]) -> list[str]:
    """One point per minor: the final x.y.0 when measured, else its latest pre-release."""
    by_minor: dict[str, list[str]] = {}
    for v in versions:
        if is_first_of_minor(v):
            by_minor.setdefault(minor_of(v), []).append(v)
    out = []
    for minor, vs in by_minor.items():
        finals = [v for v in vs if not is_prerelease(v)]
        out.append(sorted(finals, key=vkey)[0] if finals else sorted(vs, key=vkey)[-1])
    return sorted(out, key=vkey)
