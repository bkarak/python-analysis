# Validation of the "Practice what you preach" numbers — 2026-09-28

Checks the figures published in
[Python PEP8: Practice what you preach](https://bkarak.wizhut.tech/blog/2025/15112025)
(2025-11-15) against the pipeline in [bkarak/python-analysis](https://github.com/bkarak/python-analysis)
(HEAD `fe6a6fa`, ruff 0.14.4 as pinned in its `uv.lock`).

## Verdict

The published numbers are genuine and reproduce bit-for-bit, but the metric does
not measure PEP 8 adherence, and its headline trend is an instrument change, not
a code change. Measured with one fixed instrument and normalised by size, the
standard library's violation density has roughly **halved** between 3.0 and 3.14.

## What reproduces

- The exact command (`ruff check --select E,W work/Python-<v>/Lib`, run from the
  repo directory) gives the blog's single-release figures exactly:
  3.0.1 → **4479**, 3.14.0 → **16560**. So the published numbers came from the
  `Lib/`-only run, even though the blog's sample diagnostic is from `Demo/`
  (the Lib-only change is commit `9c4ac28`, 2025-11-16, after the post's date).
- The script's version regex matches **182** release directories that existed on
  python.org by 2025-11-15 (202 today). It skips the `3.0`, `3.1`, `3.2`
  directories, i.e. the x.y.0 releases of the first three minors.

## Defects found

1. **The instrument changed inside the series.** CPython added a project-wide
   `.ruff.toml` on main on 2025-05-01 (python/cpython#133124) and backported it
   to 3.13 on 2025-08-25 (#137670). It ships in the tarballs of **3.13.8, 3.13.9
   and 3.14.x** and sets `line-length = 79` and `target-version = "py310"`. Ruff
   applies the closest config file to each file, so those releases were linted
   at 79 columns while every earlier release was linted at ruff's default 88.
   Between 3.13.0 and 3.13.9, E501 goes 3718 → 12690 (+8972); every other rule
   moves by less than 100. The blog's 3.13 average (8403) mixes eight releases on
   one instrument with two on another; the 3.14 figure is entirely the new one.
2. **No size normalisation.** `Lib/` grew from 359 k to 960 k lines (2.7×).
   Absolute counts rising 4479 → 7640 (same instrument) is a density *fall* from
   12.5 to 8.0 per thousand lines. Everything except E501 is flat in absolute
   terms (2896 → 2840 diagnostics over fifteen years).
3. **Rule coverage is 25 of 67 pycodestyle rules.** In ruff 0.14.4 all E1/E2/E3
   rules (indentation, whitespace, blank lines — the bulk of PEP 8) are
   preview-only and are silently not run by `--select E,W`. What remains is
   dominated by E501: 33 % of the count in 3.0.1, 63 % in 3.14.0 at 88 columns,
   51 % → 83 % at PEP 8's 79 columns.
4. **The rule list omits rules that are in the totals.** `uniq-violated-rules`
   greps `^E` only. W605 (2147 over the 17 sampled releases, the third-largest
   rule in 3.0–3.5), W293 (678), E902 io-error (127) and syntax errors (1019)
   are counted but unlisted — 3.5 % of all counted diagnostics.
5. **Non-style diagnostics counted as PEP 8 errors.** Syntax errors (deliberate
   `badsyntax_*.py` fixtures, lib2to3's Python 2 grammar files) and E902
   (non-UTF-8 test modules) are in the totals. Separately, ruff infers
   `target-version = 3.13` from the repo's own `pyproject.toml`
   (`requires-python >= 3.13`, no `[tool.ruff]` section), so 3.14 syntax would
   be reported as errors; in practice only 23 such diagnostics appear in 3.14.0
   because CPython's shipped config takes precedence, but it is a landmine.
6. **CPython's shipped `Lib/test/.ruff.toml` (3.12+) excludes files** —
   `test_grammar.py`, `tokenizedata/*.py`, the encoded modules — worth about
   500 diagnostics, so 3.12+ is not measured like 3.11 and earlier either.
7. **Test code dominates.** 76 % of the 3.13.0 diagnostics are in test
   directories (`test_typing.py` 294, `test_dis.py` 210, `test_ast/snippets.py`
   192, `test_grammar.py` 147 …), most of them syntax being exercised on purpose.
   The stdlib proper went from 2330 to 1479 diagnostics (11.2 → 4.8 per k lines).
8. **Makefile.** `average-error-count` says "per file" but is per release; the
   3.0 and 3.14 buckets print a sum, not an average (3.14 now has eight
   releases); each bucket fails if empty. `results/` is git-ignored, so the
   published numbers cannot be regenerated from the repo without re-downloading
   ~5 GB.

## Numbers (17 sampled releases: every x.y.0 plus 3.12.11 and 3.13.9)

`blog` = the repo's exact settings. `iso88` / `iso79` = `--isolated`
(ignores every config file) with `--target-version` matched to the release
(minimum py37) at 88 / 79 columns. `full` = `--preview --line-length 79`
with matched target: all 67 pycodestyle rules (still subject to CPython's
shipped excludes in 3.12+). Rates are per thousand physical lines of `.py`
under `Lib/`; `stdlib` and `tests` split by path (`test`, `tests`,
`idle_test`, `testdata`, `tokenizedata` components).

| version | lines | blog | /k | stdlib /k | tests /k | iso88 | /k | iso79 | full | /k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.0.1 | 359148 | 4479 | 12.5 | 11.2 | 14.2 | 4479 | 12.5 | 6133 | 59091 | 164.5 |
| 3.1.1 | 382246 | 4597 | 12.0 | 10.8 | 13.6 | 4597 | 12.0 | 6430 | 60315 | 157.8 |
| 3.2.1 | 446331 | 4797 | 10.7 | 9.9 | 11.7 | 4797 | 10.7 | 7134 | 64648 | 144.8 |
| 3.3.0 | 517181 | 4962 | 9.6 | 9.0 | 10.2 | 4962 | 9.6 | 7735 | 68259 | 132.0 |
| 3.4.0 | 587286 | 5315 | 9.1 | 8.2 | 9.8 | 5315 | 9.1 | 8527 | 71231 | 121.3 |
| 3.5.0 | 642148 | 5317 | 8.3 | 7.1 | 9.3 | 5317 | 8.3 | 8768 | 70923 | 110.4 |
| 3.6.0 | 664121 | 4896 | 7.4 | 6.3 | 8.3 | 4896 | 7.4 | 9267 | 71103 | 107.1 |
| 3.7.0 | 706590 | 5062 | 7.2 | 6.2 | 7.9 | 5062 | 7.2 | 9813 | 72013 | 101.9 |
| 3.8.0 | 754276 | 5385 | 7.1 | 6.0 | 8.0 | 5385 | 7.1 | 10659 | 72995 | 96.8 |
| 3.9.0 | 781304 | 5654 | 7.2 | 5.9 | 8.1 | 5654 | 7.2 | 11365 | 73458 | 94.0 |
| 3.10.0 | 804054 | 5848 | 7.3 | 5.9 | 8.2 | 5848 | 7.3 | 12111 | 74662 | 92.9 |
| 3.11.0 | 843217 | 6211 | 7.4 | 5.9 | 8.3 | 6211 | 7.4 | 13055 | 76128 | 90.3 |
| 3.12.0 | 856400 | 5581 | 6.5 | 5.9 | 6.9 | 6673 | 7.8 | 14251 | 71385 | 83.4 |
| 3.12.11 | 886470 | 6456 | 7.3 | 6.9 | 7.5 | 7294 | 8.2 | 14974 | 73748 | 83.2 |
| 3.13.0 | 894488 | 6204 | 6.9 | 4.8 | 8.0 | 6706 | 7.5 | 15475 | 71262 | 79.7 |
| 3.13.9 | 909004 | 15356 | 16.9 | 12.6 | 19.0 | 7197 | 7.9 | 15670 | 74929 | 82.4 |
| 3.14.0 | 959898 | 16560 | 17.3 | 13.0 | 19.3 | 7640 | 8.0 | 16880 | 76636 | 79.8 |

Per-rule counts under the blog's settings:

| rule | 3.0.1 | 3.4.0 | 3.8.0 | 3.12.0 | 3.13.0 | 3.13.9 | 3.14.0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| E401 | 244 | 184 | 133 | 107 | 96 | 98 | 93 |
| E402 | 203 | 435 | 383 | 399 | 399 | 415 | 421 |
| E501 | 1493 | 1961 | 2436 | 3259 | 3718 | 12690 | 13830 |
| E701 | 1228 | 1159 | 1217 | 896 | 982 | 1077 | 1087 |
| E702 | 183 | 191 | 193 | 121 | 120 | 130 | 156 |
| E703 | 31 | 53 | 53 | 31 | 40 | 40 | 44 |
| E711 | 13 | 5 | 6 | 2 | 2 | 2 | 2 |
| E712 | 1 | 4 | 4 | 4 | 6 | 6 | 4 |
| E713 | 60 | 64 | 61 | 55 | 48 | 53 | 48 |
| E714 | 6 | 7 | 6 | 7 | 8 | 8 | 8 |
| E721 | 60 | 48 | 51 | 38 | 38 | 38 | 41 |
| E722 | 267 | 245 | 227 | 236 | 241 | 234 | 211 |
| E731 | 78 | 134 | 180 | 162 | 193 | 203 | 219 |
| E741 | 153 | 227 | 275 | 244 | 287 | 309 | 338 |
| E742 | 14 | 18 | 31 | 18 | 24 | 33 | 33 |
| E743 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |
| E902 | 16 | 11 | 11 | 0 | 0 | 0 | 0 |
| W293 | 94 | 52 | 45 | 0 | 0 | 0 | 0 |
| W605 | 261 | 411 | 1 | 1 | 1 | 1 | 1 |
| syntax | 74 | 105 | 71 | 0 | 0 | 18 | 23 |

Everything except E501 under `iso88`, absolute and per thousand lines:
3.0.1 2896 (8.06) · 3.4.0 3238 (5.51) · 3.8.0 2867 (3.80) · 3.12.0 2933 (3.42)
· 3.13.0 2761 (3.09) · 3.14.0 2840 (2.96).

Under the full rule set the top rules in 3.14.0 are E262 (24973, inline
comment spacing), E501 (13830), E226 (6385), E231 (6269), E302 (5547),
E306 (3724): whitespace and blank-line rules, none of which the blog measured.

## Reproduce

From this project. The seventeen releases are the series without 3.0, 3.1 and
3.2 (whose x.y.0 tarballs the 2025 regex skipped), plus 3.0.1, 3.1.1, 3.2.1,
3.12.11 and 3.13.9; `make fetch` puts them in `work/`.

```bash
make fetch VERSIONS="3.0.1 3.1.1 3.2.1 3.3.0 3.4.0 3.5.0 3.6.0 3.7.0 3.8.0 3.9.0 3.10.0 3.11.0 3.12.0 3.12.11 3.13.0 3.13.9 3.14.0"
make validation
```

`breakdown.py` reproduces the post's settings by relying on the same ruff
inference the post did: ruff 0.14.4 (through `uvx`) run from a directory
whose `pyproject.toml` says `requires-python >= 3.13` and has no
`[tool.ruff]` section, which is still true of this project's
`pyproject.toml`, and with every `.ruff.toml` CPython ships honoured, which
`--isolated` in `isolated.py` switches off. The pipeline as it was is commit
`fe6a6fa` in this repo's history. `breakdown.json` and `isolated.json` here
are the outputs of the 2026-09-28 run: per release, lines and files by
category, then per variant the total, counts by rule, by category and by
file. The extracted trees and the raw ruff text output are not kept.
