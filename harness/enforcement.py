#!/usr/bin/env python3
"""What CPython enforces against what it conforms to.

    uv run harness/enforcement.py 3.14.0

Reads the release's .pre-commit-config.yaml for its ruff hooks, resolves the
rules each hook selects from the .ruff.toml chain of the tree it covers, and
counts those rules three ways: in that tree under CPython's own configuration
(what the hook sees; expected to be zero at release), in that tree with the
configuration ignored, and in the library proper, where no hook runs. Writes
data/enforcement/<v>.json. PROTOCOL.md, "Enforcement".
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure import ROOT, WORK, inventory, is_error  # noqa: E402

OUT = ROOT / 'data' / 'enforcement'
DEFAULT_SELECT = ['E4', 'E7', 'E9', 'F']  # ruff's default rule selection


def hooks_in(text: str) -> tuple[str | None, list[dict]]:
    """The ruff-pre-commit rev and every `ruff` hook (id, name, files pattern), from a minimal read of the YAML."""
    rev, hooks, cur = None, [], None
    in_ruff_repo = False
    for line in text.splitlines():
        m = re.match(r'\s*-\s*repo:\s*(\S+)', line)
        if m:
            in_ruff_repo = 'ruff-pre-commit' in m.group(1)
            continue
        m = re.match(r'\s*rev:\s*(\S+)', line)
        if m and in_ruff_repo:
            rev = m.group(1)
            continue
        m = re.match(r'\s*-\s*id:\s*(\S+)', line)
        if m:
            cur = {'id': m.group(1), 'name': None, 'files': None} if m.group(1) == 'ruff' else None
            if cur:
                hooks.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r'\s*name:\s*(.+)', line)
        if m:
            cur['name'] = m.group(1).strip()
        m = re.match(r'\s*files:\s*(.+)', line)
        if m:
            cur['files'] = m.group(1).strip()
    return rev, hooks


def tree_of(pattern: str | None) -> str | None:
    """`^Lib/test/` -> `Lib/test`; anything more elaborate is left alone."""
    m = re.fullmatch(r'\^([A-Za-z0-9_./-]+?)/?', pattern or '')
    return m.group(1).rstrip('/') if m else None


def config_chain(root: Path, tree: str) -> list[Path]:
    """The ruff configs that govern `tree`, outermost first: the closest one plus what it extends."""
    d = root / tree
    closest = None
    while True:
        for name in ('.ruff.toml', 'ruff.toml'):
            if (d / name).exists():
                closest = d / name
                break
        if closest or d == root:
            break
        d = d.parent
    chain: list[Path] = []
    cfg = closest
    while cfg is not None:
        chain.insert(0, cfg)
        ext = tomllib.loads(cfg.read_text()).get('extend')
        cfg = (cfg.parent / ext).resolve() if ext else None
    return chain


def selection(chain: list[Path]) -> tuple[list[str], list[str], int]:
    """The rules selected and ignored, and the line length, after the whole chain has applied."""
    select, ignore, line_length = list(DEFAULT_SELECT), [], 88
    for cfg in chain:
        t = tomllib.loads(cfg.read_text())
        line_length = t.get('line-length', line_length)
        lint = t.get('lint', t)
        if 'select' in lint:
            select = list(lint['select'])
        select += list(lint.get('extend-select', []))
        ignore += list(lint.get('ignore', []))
    return select, ignore, line_length


def count(args: list[str], cwd: Path) -> int:
    proc = subprocess.run(['ruff', 'check', '--no-cache', '--no-fix', '--output-format', 'json', '--exit-zero', *args],
                          cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'ruff failed: {proc.stderr[:400]}')
    return sum(1 for d in json.loads(proc.stdout) if not is_error(d.get('code') or 'invalid-syntax'))


def main(version: str) -> None:
    root = WORK / f'Python-{version}'
    cfg = root / '.pre-commit-config.yaml'
    if not cfg.exists():
        sys.exit(f'{cfg} is missing')
    rev, hooks = hooks_in(cfg.read_text())
    lib_files = inventory(root / 'Lib')
    stdlib = sorted(rel for rel, f in lib_files.items() if f['category'] == 'stdlib')
    stdlib_lines = sum(lib_files[r]['lines'] for r in stdlib)
    out = []
    for h in hooks:
        tree = tree_of(h['files'])
        row = {'name': h['name'], 'files': h['files'], 'tree': tree}
        if tree is None or not (root / tree).is_dir():
            row['note'] = 'pattern not resolved to one directory'
            out.append(row)
            continue
        chain = config_chain(root, tree)
        select, ignore, line_length = selection(chain)
        tree_files = inventory(root / tree)
        rules = ['--select', ','.join(select), f'--line-length={line_length}'] + (['--ignore', ','.join(ignore)] if ignore else [])
        row.update({
            'configs': [str(c.relative_to(root)) for c in chain],
            'select': select, 'ignore': ignore, 'line_length': line_length,
            'tree_files': len(tree_files), 'tree_lines': sum(f['lines'] for f in tree_files.values()),
            'in_tree_own_config': count([tree], root),
            'in_tree_isolated': count(['--isolated', *rules, *[f'{tree}/{r}' for r in tree_files]], root) if tree_files else 0,
            'in_stdlib_isolated': count(['--isolated', *rules, *[f'Lib/{r}' for r in stdlib]], root),
            'stdlib_lines': stdlib_lines,
        })
        out.append(row)
        print(f"{h['name'] or h['files']:40} rules {','.join(select):18} own config {row['in_tree_own_config']:5}  "
              f"tree isolated {row['in_tree_isolated']:5}  Lib proper {row['in_stdlib_isolated']:6}", flush=True)
    result = {'version': version, 'measured': date.today().isoformat(), 'ruff_pre_commit_rev': rev, 'hooks': out}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{version}.json').write_text(json.dumps(result, indent=1) + '\n')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
