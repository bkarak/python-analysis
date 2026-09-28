# Results — 2026-09-28

Every number below is reproducible from this tree with `make fetch`,
`make measure` and `make results`, plus `make cpython` and `make cohorts`
for the age cohorts, against the tarballs whose digests are in
[data/tarballs.sha256](data/tarballs.sha256) and the CPython tag `v3.14.0`,
with pycodestyle 2.15.0 and ruff 0.14.4 under Python 3.14 (`uv.lock`).
Protocol, categories and metrics: [PROTOCOL.md](PROTOCOL.md); read *Known
problems* there before citing anything. The instrument line and the tables
are `make results`'s output, pasted verbatim; the reading is written by
hand and says which table it reads from.

## Reading the series

- **The library proper conforms to PEP 8 about twice as well as it did in
  3.0.** Its density fell from 87.6 to 48.1 style diagnostics per thousand
  lines between 3.0 (2008) and 3.14.0 (2025), and it fell at every step but
  one (3.11 → 3.12, +0.2). The test suite fell from 99.1 to 56.0. Both
  instruments agree within 2.5 % at every point (series table, columns
  `stdlib /k`, `tests /k`, `/k`).
- **Every rule family fell but one: line length.** In the library proper
  E5 rose from 5.5 to 10.9 per thousand lines, and E501 is the only rule in
  the top twenty with more instances in 3.14.0 (2951) than in 3.0 (886).
  Whitespace (E2) fell from 43.1 to 16.0, blank lines (E3) from 24.0 to
  13.8, statements (E7) from 6.0 to 2.4, indentation (E1) from 6.7 to 4.4.
  The W families are zero throughout: CPython has stripped trailing
  whitespace since before 3.0; W605 (invalid escape sequence) went from 159
  to 0 once Python itself began warning about it in 3.6 (family and rule
  tables).
- **What remains is layout, not code.** After line length, E302 (two blank
  lines before a top-level definition) is the largest rule left, 2457
  instances, about its 3.0 count; E261 comment spacing and E203 whitespace
  before `:` follow. The rules that describe the shape of code fell three-
  to sixteen-fold: E231 comma spacing 2342 → 895, E225 operator spacing
  725 → 274, E701 several statements on a line 616 → 283, E301 761 → 294,
  E211 whitespace before `(` 275 → 17 (rule table).
- **Where the diagnostics are.** In 3.14.0 the library proper holds 17 %
  of all diagnostics on 28 % of the lines, the test suite 47 % on 67 %, and
  78 generated files, 4.5 % of the lines, hold 36 %: 645 per thousand
  lines, because the charmap codecs are tables of one-line entries with
  two-space inline comments. A count that does not split these measures
  gencodec's output style (category table).
- **Patch releases drift by at most 3 per thousand lines** from their
  minor's first release (3.13.9 against 3.13.0: 83.0 against 84.7), which
  is why the series has one point per minor and why averaging patch
  releases, as in November 2025, hid nothing except an instrument change
  (sensitivity table).
- **Against the 2025 post.** It ran 25 rules at 88 columns and saw 12.5
  → 6.9 per thousand lines from 3.0.1 to 3.13.0, then 17.3 for 3.14.0
  under a different configuration ([validation/README.md](validation/README.md)).
  Where the releases were measured alike the direction was the same as
  here; the level was under a tenth of it (4479 against 59804 diagnostics
  for 3.0.1) because most of pycodestyle was not run.

## Reading the cohorts

Every line of 3.14.0 is dated by the commit that last edited it, and the
diagnostics on it go to that date's cohort (cohort tables; method and
caveats in PROTOCOL.md, *Age cohorts* and Known problems 9 to 11).

- **Apart from line length, code from every era is cleaner than the
  last.** Without E5, the library proper's density by the era of a line's
  last edit is 47.3 before PEP 8, 66.0 from PEP 8 to 3.0, 30.3 from 3.0 to
  the GitHub move, 24.2 from then to the first ruff hook, and 19.5 since
  (era table, `excl. E5 /k`). Whitespace (E2) runs 36.4 → 10.0 → 9.1 →
  5.9 over the last four eras, blank lines (E3) 20.6 → 13.2 → 9.9 → 6.7,
  and in the rules-by-era table E261, E231, E265, E221 and E303 each fall
  eight- to twenty-fold from their peak.
- **Line length is being abandoned.** E501 rises from 1.9 per thousand
  lines in code untouched since before PEP 8 to 6.5, 16.5 and 27.9 in the
  three latest eras, and it is why the newest cohort's total (47.4) sits
  above the 2008 to 2017 cohort's (36.9). Nothing enforces it: CPython's
  pre-commit runs ruff on the test suite, the docs and the tools, not on
  the library proper, and selects no line-length rule where it does run
  (rules-by-era table).
- **The worst cohort is Python 2's.** Lines last edited between PEP 8 and
  3.0 carry 70.2 per thousand, more than the pre-PEP 8 survivors (49.3):
  E231 comma spacing 8.7, E261 comment spacing 8.6, E203 whitespace before
  `:` 6.2. This is the code of the large 2002 to 2006 packages together
  with every line the Python 3 conversion rewrote (Known problems 9).
- **The library is old.** 63 % of the library proper's lines were last
  edited before the GitHub move in February 2017 and 9 % before PEP 8
  existed; 15 % were edited in the two years since ruff entered
  pre-commit, and 2024 alone touched 7.4 % (era and year tables).
- **Ruff agrees on every ordering**, within 9 % on the two oldest cohorts,
  where its ports of the E2 rules differ most from pycodestyle, and within
  6 % on the three latest (era table, `ruff /k`).

## Caveats

- The headline number moves with the generated heuristic: the seven
  charmap codecs whose docstring lacks the word "generated" are 1 % of the
  library's lines and were worth 8 per thousand lines of its density until
  the codec docstring itself became the marker. `make generated` prints the
  list; check it after any change to `harness/classify.py`.
- pycodestyle reports no non-style failures because it falls back to
  latin-1 on undecodable files and its tokenizer accepts everything the
  corpus contains; ruff's parser refused 74 to 149 files per release before
  3.13 (deliberate bad-syntax fixtures, lib2to3's Python 2 samples) and 5
  from 3.13 on. Those files' style is uncounted under ruff, which is part of
  why its totals sit 1 to 2.5 % under pycodestyle's in the old releases.
- Rates are per physical line. Source-line counts are in every
  measurement JSON for a different denominator.
- The series starts at 3.0, 3.1 and 3.2 themselves, not their first patch
  releases, which the 2025 pipeline used because its regex skipped the
  two-component directories.
- A cohort is the date of a line's last edit, not its origin. The oldest
  cohorts are what survived untouched; the 2006 to 2008 cohorts include
  what the Python 3 conversion rewrote; moved code is dated at the move.

Instruments: pycodestyle 2.15.0 at 79 columns with its defaults, and ruff 0.14.4 with `--isolated --preview --select E,W --line-length 79` and the target version matched to the release; Python 3.14.2; last measured 2026-09-28. Counts are style diagnostics only; syntax and I/O failures are the `non-style` column. Rates are per thousand physical lines of `.py` under `Lib/`.

## The series: one point per minor release

| release | files | lines | pycodestyle | /k | stdlib /k | tests /k | generated /k | ruff | /k | non-style pcs / ruff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.0 | 1093 | 356513 | 59701 | 167.5 | 87.6 | 99.1 | 805.7 | 58932 | 165.3 | 0 / 90 |
| 3.1 | 1192 | 381124 | 61193 | 160.6 | 84.9 | 96.8 | 792.9 | 60142 | 157.8 | 0 / 93 |
| 3.2 | 1299 | 442173 | 65351 | 147.8 | 80.6 | 89.8 | 813.2 | 64322 | 145.5 | 0 / 89 |
| 3.3.0 | 1364 | 517181 | 68839 | 133.1 | 75.4 | 81.1 | 810.2 | 68179 | 131.8 | 0 / 89 |
| 3.4.0 | 1472 | 587286 | 72005 | 122.6 | 69.0 | 75.4 | 817.2 | 71122 | 121.1 | 0 / 116 |
| 3.5.0 | 1541 | 642148 | 72537 | 113.0 | 60.6 | 70.4 | 632.9 | 70781 | 110.2 | 0 / 149 |
| 3.6.0 | 1552 | 664121 | 72452 | 109.1 | 58.6 | 67.0 | 753.7 | 71027 | 106.9 | 0 / 83 |
| 3.7.0 | 1611 | 706590 | 73165 | 103.5 | 56.5 | 63.1 | 746.6 | 71938 | 101.8 | 0 / 82 |
| 3.8.0 | 1664 | 754276 | 74239 | 98.4 | 52.6 | 61.3 | 745.3 | 72921 | 96.7 | 0 / 82 |
| 3.9.0 | 1711 | 781304 | 74846 | 95.8 | 51.5 | 60.3 | 738.6 | 73387 | 93.9 | 0 / 81 |
| 3.10.0 | 1722 | 804054 | 76009 | 94.5 | 51.2 | 60.1 | 722.9 | 74597 | 92.8 | 0 / 75 |
| 3.11.0 | 1772 | 843215 | 77464 | 91.9 | 50.3 | 58.8 | 717.0 | 76068 | 90.2 | 0 / 75 |
| 3.12.0 | 1741 | 856398 | 78667 | 91.9 | 50.5 | 59.4 | 704.0 | 77475 | 90.5 | 0 / 74 |
| 3.13.0 | 1726 | 894484 | 75747 | 84.7 | 48.8 | 57.4 | 629.2 | 75105 | 84.0 | 0 / 5 |
| 3.14.0 | 1830 | 959894 | 77208 | 80.4 | 48.1 | 56.0 | 645.0 | 77301 | 80.5 | 0 / 5 |

## Rule families in the stdlib proper (pycodestyle, per thousand lines)

| release | E1 | E2 | E3 | E4 | E5 | E7 | W1 | W2 | W3 | W5 | W6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.0 | 6.7 | 43.1 | 24.0 | 1.2 | 5.5 | 6.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.9 |
| 3.1 | 7.0 | 40.7 | 24.1 | 1.2 | 5.4 | 5.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.9 |
| 3.2 | 7.1 | 37.5 | 23.5 | 1.1 | 5.7 | 4.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.9 |
| 3.3.0 | 6.9 | 34.4 | 22.1 | 1.0 | 5.8 | 4.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.9 |
| 3.4.0 | 6.5 | 30.2 | 20.9 | 0.9 | 5.8 | 3.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.8 |
| 3.5.0 | 6.1 | 23.4 | 20.1 | 0.9 | 5.8 | 3.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.8 |
| 3.6.0 | 6.2 | 22.6 | 19.6 | 0.8 | 6.0 | 3.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.7.0 | 6.0 | 21.1 | 19.0 | 0.8 | 6.4 | 3.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.8.0 | 5.9 | 19.7 | 16.4 | 0.7 | 6.9 | 3.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.9.0 | 5.7 | 19.1 | 15.8 | 0.7 | 7.2 | 3.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.10.0 | 5.6 | 18.7 | 15.7 | 0.7 | 7.6 | 2.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.11.0 | 5.5 | 17.9 | 15.5 | 0.7 | 8.0 | 2.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.12.0 | 5.3 | 17.8 | 15.3 | 0.6 | 8.8 | 2.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.13.0 | 4.6 | 16.5 | 14.3 | 0.6 | 10.2 | 2.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 3.14.0 | 4.4 | 16.0 | 13.8 | 0.6 | 10.9 | 2.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Rules in the stdlib proper: 3.14.0 against 3.0 (pycodestyle)

| rule | 3.0 | /k | 3.14.0 | /k | what it is |
|---|---:|---:|---:|---:|---:|
| E501 | 886 | 5.2 | 2951 | 10.9 | line too long |
| E302 | 2346 | 13.8 | 2457 | 9.0 | expected 2 blank lines, found 1 |
| E231 | 2342 | 13.8 | 895 | 3.3 | missing whitespace after ',' |
| E261 | 1097 | 6.5 | 942 | 3.5 | at least two spaces before inline comment |
| E203 | 777 | 4.6 | 718 | 2.6 | whitespace before ':' |
| E301 | 761 | 4.5 | 294 | 1.1 | expected 1 blank line, found 0 |
| E225 | 725 | 4.3 | 274 | 1.0 | missing whitespace around operator |
| E128 | 547 | 3.2 | 620 | 2.3 | continuation line under-indented for visual indent |
| E701 | 616 | 3.6 | 283 | 1.0 | multiple statements on one line |
| E265 | 543 | 3.2 | 305 | 1.1 | block comment should start with '# ' |
| E305 | 459 | 2.7 | 452 | 1.7 | expected 2 blank lines after class or function definition, found 1 |
| E303 | 447 | 2.6 | 430 | 1.6 | too many blank lines |
| E251 | 358 | 2.1 | 242 | 0.9 | unexpected spaces around keyword / parameter equals |
| E266 | 343 | 2.0 | 259 | 1.0 | too many leading '#' for block comment |
| E221 | 298 | 1.8 | 302 | 1.1 | multiple spaces before operator |
| E127 | 253 | 1.5 | 288 | 1.1 | continuation line over-indented for visual indent |
| E211 | 275 | 1.6 | 17 | 0.1 | whitespace before '(' |
| E122 | 164 | 1.0 | 37 | 0.1 | continuation line missing indentation or outdented |
| E262 | 161 | 0.9 | 102 | 0.4 | inline comment should start with '# ' |
| W605 | 159 | 0.9 | 0 | 0.0 | invalid escape sequence |

## Where the diagnostics are in 3.14.0

| category | files | lines | pycodestyle | share | /k | ruff | share | /k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| stdlib | 575 | 271599 | 13076 | 17% | 48.1 | 13510 | 17% | 49.7 |
| tests | 1177 | 644872 | 36125 | 47% | 56.0 | 35947 | 47% | 55.7 |
| generated | 78 | 43423 | 28007 | 36% | 645.0 | 27844 | 36% | 641.2 |

## Sensitivity: patch releases against their minor's first release

| release | lines | pycodestyle /k | ruff /k | x.y.0 | pycodestyle /k | ruff /k |
|---|---:|---:|---:|---:|---:|---:|
| 3.0.1 | 359148 | 166.5 | 164.3 | 3.0 | 167.5 | 165.3 |
| 3.1.1 | 382246 | 160.9 | 157.5 | 3.1 | 160.6 | 157.8 |
| 3.2.1 | 446331 | 144.8 | 144.6 | 3.2 | 147.8 | 145.5 |
| 3.12.11 | 886466 | 89.2 | 88.7 | 3.12.0 | 91.9 | 90.5 |
| 3.13.9 | 909000 | 83.0 | 83.2 | 3.13.0 | 84.7 | 84.0 |

## Age cohorts of 3.14.0: density by the date a line was last edited

Every line of `Lib/` at tag `v3.14.0` (commit `ebf955df7a`) blamed with `git blame --line-porcelain v3.14.0 -- Lib/<file>`, dated by the commit's author time; a diagnostic belongs to the cohort of the line it is reported on. 1830 files blamed, 0 skipped, 0 pycodestyle and 0 ruff diagnostics unattributed. Rates are style diagnostics per thousand lines of the cohort.

### By era, stdlib proper (and the test suite)

| era | from | lines | share | pycodestyle /k | excl. E5 /k | ruff /k | E1 | E2 | E3 | E5 | E7 | test lines | tests /k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| before PEP 8 |  | 23404 | 9% | 49.3 | 47.3 | 53.6 | 4.1 | 17.3 | 19.7 | 2.0 | 5.9 | 4607 | 40.2 |
| PEP 8 to 3.0 | 2001-07-05 | 63419 | 23% | 70.2 | 66.0 | 75.6 | 4.0 | 36.4 | 20.6 | 4.1 | 3.9 | 81683 | 83.6 |
| 3.0 to GitHub | 2008-12-03 | 85418 | 31% | 36.9 | 30.3 | 37.2 | 5.3 | 10.0 | 13.2 | 6.6 | 1.4 | 207577 | 55.3 |
| GitHub to ruff | 2017-02-10 | 59292 | 22% | 40.8 | 24.2 | 42.1 | 3.6 | 9.1 | 9.9 | 16.6 | 1.1 | 211033 | 47.6 |
| ruff in pre-commit | 2023-09-12 | 40066 | 15% | 47.4 | 19.5 | 44.6 | 4.7 | 5.9 | 6.7 | 27.9 | 1.9 | 139972 | 54.3 |

### By year, stdlib proper

| year | lines | share | pycodestyle | /k | E1 | E2 | E3 | E5 | E7 | test lines | tests /k |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1990 | 76 | 0.0% | 17 | 223.7 | 0.0 | 78.9 | 131.6 | 0.0 | 0.0 | 0 | n/a |
| 1991 | 15 | 0.0% | 2 | 133.3 | 0.0 | 0.0 | 133.3 | 0.0 | 0.0 | 0 | n/a |
| 1992 | 222 | 0.1% | 17 | 76.6 | 0.0 | 4.5 | 67.6 | 0.0 | 4.5 | 16 | 0.0 |
| 1993 | 24 | 0.0% | 6 | 250.0 | 0.0 | 0.0 | 250.0 | 0.0 | 0.0 | 0 | n/a |
| 1994 | 287 | 0.1% | 23 | 80.1 | 0.0 | 41.8 | 34.8 | 0.0 | 0.0 | 21 | 0.0 |
| 1995 | 775 | 0.3% | 72 | 92.9 | 0.0 | 69.7 | 20.6 | 0.0 | 2.6 | 1 | 0.0 |
| 1996 | 139 | 0.1% | 18 | 129.5 | 0.0 | 57.6 | 64.7 | 0.0 | 0.0 | 32 | 0.0 |
| 1997 | 933 | 0.3% | 30 | 32.2 | 0.0 | 10.7 | 19.3 | 0.0 | 2.1 | 519 | 53.9 |
| 1998 | 2685 | 1.0% | 63 | 23.5 | 3.7 | 5.2 | 9.7 | 0.7 | 4.1 | 32 | 0.0 |
| 1999 | 370 | 0.1% | 22 | 59.5 | 0.0 | 16.2 | 37.8 | 0.0 | 5.4 | 124 | 16.1 |
| 2000 | 11598 | 4.3% | 536 | 46.2 | 4.7 | 17.3 | 14.8 | 3.0 | 6.2 | 725 | 27.6 |
| 2001 | 9262 | 3.4% | 470 | 50.7 | 3.8 | 15.9 | 23.5 | 1.9 | 5.2 | 5715 | 57.6 |
| 2002 | 8034 | 3.0% | 643 | 80.0 | 2.2 | 58.0 | 13.1 | 2.2 | 3.7 | 3806 | 60.4 |
| 2003 | 10084 | 3.7% | 688 | 68.2 | 2.8 | 40.3 | 16.5 | 5.9 | 2.0 | 11197 | 86.4 |
| 2004 | 7668 | 2.8% | 644 | 84.0 | 5.1 | 45.3 | 22.7 | 3.8 | 4.0 | 10042 | 93.2 |
| 2005 | 2543 | 0.9% | 191 | 75.1 | 3.5 | 38.5 | 13.8 | 5.5 | 13.8 | 2638 | 98.9 |
| 2006 | 8376 | 3.1% | 805 | 96.1 | 6.1 | 43.7 | 37.1 | 3.5 | 3.6 | 13513 | 91.7 |
| 2007 | 8844 | 3.3% | 410 | 46.4 | 2.6 | 19.0 | 13.1 | 6.1 | 5.0 | 17811 | 76.2 |
| 2008 | 15062 | 5.5% | 953 | 63.3 | 5.4 | 26.7 | 23.0 | 3.5 | 3.8 | 20494 | 81.4 |
| 2009 | 7494 | 2.8% | 467 | 62.3 | 8.5 | 23.1 | 21.4 | 6.4 | 2.8 | 14974 | 76.9 |
| 2010 | 13731 | 5.1% | 577 | 42.0 | 3.5 | 11.4 | 20.3 | 5.3 | 0.9 | 34865 | 61.6 |
| 2011 | 4255 | 1.6% | 167 | 39.2 | 10.3 | 8.5 | 5.9 | 13.2 | 1.4 | 19402 | 40.5 |
| 2012 | 15346 | 5.7% | 510 | 33.2 | 4.4 | 9.6 | 13.2 | 4.6 | 1.0 | 35166 | 83.2 |
| 2013 | 15759 | 5.8% | 473 | 30.0 | 2.9 | 5.6 | 14.6 | 5.8 | 0.9 | 37316 | 48.9 |
| 2014 | 14040 | 5.2% | 452 | 32.2 | 5.6 | 12.5 | 7.1 | 4.8 | 2.1 | 19235 | 39.7 |
| 2015 | 8446 | 3.1% | 258 | 30.5 | 4.9 | 3.9 | 8.6 | 10.8 | 2.1 | 23153 | 36.4 |
| 2016 | 6069 | 2.2% | 237 | 39.1 | 10.4 | 7.6 | 9.6 | 9.7 | 1.0 | 22496 | 43.6 |
| 2017 | 8654 | 3.2% | 219 | 25.3 | 3.8 | 4.7 | 5.0 | 10.2 | 1.3 | 22505 | 36.1 |
| 2018 | 8119 | 3.0% | 304 | 37.4 | 5.0 | 10.0 | 8.1 | 12.7 | 1.1 | 26321 | 40.3 |
| 2019 | 10075 | 3.7% | 429 | 42.6 | 3.2 | 17.4 | 8.5 | 12.6 | 0.8 | 27534 | 51.3 |
| 2020 | 7391 | 2.7% | 320 | 43.3 | 2.6 | 7.4 | 12.4 | 18.0 | 0.8 | 24156 | 40.5 |
| 2021 | 7619 | 2.8% | 346 | 45.4 | 5.0 | 7.7 | 10.5 | 21.0 | 0.9 | 33256 | 45.3 |
| 2022 | 11372 | 4.2% | 492 | 43.3 | 2.9 | 7.6 | 13.6 | 17.1 | 1.6 | 37535 | 56.8 |
| 2023 | 9967 | 3.7% | 524 | 52.6 | 3.1 | 5.0 | 9.8 | 33.3 | 1.3 | 61225 | 51.0 |
| 2024 | 20206 | 7.4% | 1049 | 51.9 | 6.1 | 7.8 | 6.7 | 28.5 | 2.5 | 65995 | 61.7 |
| 2025 | 16059 | 5.9% | 642 | 40.0 | 3.3 | 4.4 | 6.3 | 24.2 | 1.2 | 53052 | 48.5 |

### Rules by era, stdlib proper (pycodestyle, per thousand lines of the era)

| rule | before PEP 8 | PEP 8 to 3.0 | 3.0 to GitHub | GitHub to ruff | ruff in pre-commit |
|---|---:|---:|---:|---:|---:|
| E501 | 1.9 | 4.0 | 6.5 | 16.5 | 27.9 |
| E302 | 12.6 | 14.3 | 8.4 | 6.1 | 4.5 |
| E261 | 2.7 | 8.6 | 2.5 | 1.2 | 1.1 |
| E231 | 3.3 | 8.7 | 1.5 | 1.8 | 0.7 |
| E203 | 0.1 | 6.2 | 0.8 | 2.6 | 2.4 |
| E128 | 2.1 | 1.8 | 3.3 | 1.7 | 1.8 |
| E305 | 1.5 | 2.5 | 1.6 | 1.4 | 1.0 |
| E303 | 3.2 | 1.7 | 1.8 | 1.2 | 0.4 |
| E265 | 2.3 | 2.2 | 1.1 | 0.2 | 0.1 |
| E221 | 1.8 | 2.8 | 0.6 | 0.3 | 0.2 |
| E301 | 2.1 | 1.8 | 0.9 | 0.8 | 0.3 |
| E127 | 0.8 | 1.2 | 1.1 | 0.8 | 1.4 |
