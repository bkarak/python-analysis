# Results — 2026-09-28

Every number below is reproducible from this tree with `make fetch`,
`make measure` and `make results`, against the tarballs whose digests are in
[data/tarballs.sha256](data/tarballs.sha256), with pycodestyle 2.15.0 and
ruff 0.14.4 under Python 3.14 (`uv.lock`). Protocol, categories and metrics:
[PROTOCOL.md](PROTOCOL.md); read *Known problems* there before citing
anything. The instrument line and the tables are `make results`'s output,
pasted verbatim; the reading is written by hand and says which table it
reads from.

## Reading

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
  instances, about its 3.0 count; E261 comment spacing and E203 whitespace before `:` follow.
  The rules that describe the shape of code fell three- to sixteen-fold:
  E231 comma spacing 2342 → 895, E225 operator spacing 725 → 274, E701
  several statements on a line 616 → 283, E301 761 → 294, E211 whitespace
  before `(` 275 → 17 (rule table).
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
  here; the level was under a tenth of it (4479 against 59804 diagnostics for
  3.0.1) because most of pycodestyle was not run.

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
