# Protocol: does the standard library practice what PEP 8 preaches?

PEP 8 names the code in `Lib/` as its subject. This project measures how far
that code conforms to PEP 8, how the conformance has moved from 3.0 (2008) to
3.14 (2025), and where the non-conformance sits. It replaces the pipeline
behind the November 2025 post [Python PEP8: Practice what you
preach](https://bkarak.wizhut.tech/blog/2025/15112025), whose numbers were
reproduced and taken apart in [validation/README.md](validation/README.md):
they were right and their trend was an artifact of the tool's configuration.
Everything below exists to make that impossible to repeat.

Run: `make fetch` then `make measure`; tables with `make results`. Numbers
and their reading: [RESULTS.md](RESULTS.md).

## Question

Two hypotheses were left open in November 2025: *nobody cares about PEP 8*,
or *the standard library is getting less Pythonic*. The series here answers
the second. The first needs the age analysis under **Planned**: PEP 8 tells
maintainers not to reformat old code, so whether 1991 code follows a 2001
guide says nothing about whether anyone cares; whether code written after
2001 follows it does.

## Corpus

- **Releases** are the source tarballs `Python-<v>.tgz` from
  `https://www.python.org/ftp/python/<v>/`, extracted into `work/`
  (gitignored). The SHA-256 of every tarball measured is in
  [data/tarballs.sha256](data/tarballs.sha256).
- **What is measured** is every `*.py` under `Lib/`, symlinks skipped. Not
  `Tools/`, `Doc/`, `Demo/`, `Modules/` or `.pyi` files: `Lib/` is what "the
  standard library" means to a user, and the other trees changed shape too
  much across versions to compare.
- **The series** is the first release of every minor, 3.0 to 3.14, fifteen
  points. For 3.0, 3.1 and 3.2 that tarball is `Python-3.0.tgz` and so on;
  the 2025 pipeline's regex skipped those three.
- **The sensitivity set** is a handful of patch releases (3.0.1, 3.1.1,
  3.2.1, 3.12.11, 3.13.9), reported next to their minor's first release and
  never averaged into the series. A patch release only backports fixes, so
  the twenty-six patch releases of 3.9 are twenty-six near-copies of one
  point; averaging them weights minors unequally, and in 2025 it averaged two
  instruments into one number for 3.13.
- **Not in the corpus yet**: 2.x. pycodestyle can tokenise it; ruff cannot
  parse it. See **Planned**.

## Instruments

Two, always both, always with every configuration file ignored, always on
the same explicit file list, so that neither tool's default excludes nor any
`.gitignore` play a part.

1. **pycodestyle 2.15.0**, `--max-line-length=79` (its default, spelled
   out), everything else at its defaults, including the default ignore list
   (E121, E123, E126, E226, E24, E704, W503, W504: the rules pycodestyle's
   maintainers consider contested, and the contradictory W503/W504 pair).
   pycodestyle is the reference implementation of PEP 8's checkable rules; it
   was called `pep8` until 2016. "A PEP 8 violation" in this project means
   "what pycodestyle reports". It runs under Python 3.14
   ([.python-version](.python-version)); the interpreter matters because
   pycodestyle borrows its `tokenize`. It is single-threaded, so
   `harness/measure.py` runs it in `JOBS` batches balanced by file size.
2. **ruff 0.14.4**, `ruff check --isolated --preview --select E,W
   --line-length 79 --target-version py3XX`, XX being the release's minor
   (minimum py37, the oldest ruff knows). `--isolated` ignores every
   `pyproject.toml`, `ruff.toml` and `.ruff.toml`, including the ones CPython
   ships inside its own tree since 3.12 and this project's own; `--preview`
   enables the 42 pycodestyle rules ruff keeps behind that flag (all of E1,
   E2, E3 and W391), without which `--select E,W` means 25 rules;
   `--target-version` stops ruff from reporting a release's own syntax as an
   error. Ruff is the cross-check: where the two instruments disagree on a
   family, the disagreement is reported, not averaged.

What the 2025 pipeline did instead, for the record: ruff's stable 25 rules
at 88 columns, a target version inferred from the analysis repo's own
`pyproject.toml`, and CPython's shipped `.ruff.toml` honoured wherever it
existed, which from 3.13.8 on meant 79 columns and a 3.10 target for two
releases out of fifteen. The instrument definitions live in
[harness/measure.py](harness/measure.py); change them and this section
together, then re-measure everything.

## Categories

Every file is exactly one of three, decided in
[harness/classify.py](harness/classify.py):

- **tests**: any directory component named `test`, `tests`, `idle_test`,
  `testdata`, `test_data` or `tokenizedata` (`Lib/test/`, `lib2to3/tests/`,
  `ctypes/test/`, `idlelib/idle_test/` …). Test code exercises syntax on
  purpose and carries fixtures that are meant to be wrong.
- **generated**: files whose first fifteen lines carry a generation marker
  CPython actually uses (`# Auto-generated by …`, `# Generated by h2py …`,
  `This file is automatically generated`, `DO NOT EDIT`, gencodec's codec
  docstring), plus `msilib/schema.py` and `msilib/sequence.py`, table dumps
  with no marker. Tests win over generated. Each measurement lists what it
  classified (`generated_files`), and `make generated` prints the lists:
  in 3.14.0 it is 56 files, the charmap codecs, `pydoc_data/topics.py`,
  `keyword.py`, `token.py`, `_opcode_metadata.py`, `re/_casefix.py` and
  `stringprep.py`; in 3.0.1 it is 77, adding `symbol.py`, the `plat-*`
  header translations and the two msilib tables.
- **stdlib**: everything else, the library a user imports. The headline
  number of the project is this category's density under pycodestyle.

Vendored code (`tomllib` from tomli, `_pyrepl` from PyPy,
`importlib.metadata` from importlib_metadata, `zipfile._path` from zipp …)
is not distinguished and counts as stdlib. See **Known problems**.

## Metrics

- **Style diagnostics**: every diagnostic except the non-style ones,
  which are pycodestyle's E9 codes (E901 syntax or tokenize failure, E902 I/O
  failure) and ruff's `invalid-syntax`, E902 and E999. Non-style counts are
  reported beside the style counts and never added to them. In old releases
  they are deliberate bad-syntax fixtures and lib2to3's Python 2 grammar
  samples; in a new release they would mean the instrument does not know the
  release's syntax.
- **Density**: style diagnostics per thousand physical lines of `.py`,
  blank and comment lines included, because PEP 8 has rules about both.
  Source lines (non-blank, non-comment) are stored in every measurement for
  anyone who prefers them as the denominator.
- **By category** and **by rule family**, the family being the code's first
  two characters: E1 indentation, E2 whitespace, E3 blank lines, E4 imports,
  E5 line length, E7 statements, W1 to W3 the warning counterparts, W5 line
  breaks, W6 deprecated constructs.
- **By rule**, first release of the series against the latest, stdlib
  proper.

## Comparability rules

- Never compare a count produced under one instrument configuration with a
  count produced under another. Every measurement's `instruments` block
  records what produced it; when an instrument is bumped, everything is
  re-measured and RESULTS.md says so.
- Never average patch releases into a minor.
- A release is the tarball whose SHA-256 is in `data/tarballs.sha256`; a
  different digest is a different release.

## Known problems, not yet fixed

1. **Line length is a third to a half of everything counted.** E501
   dominates both instruments. The family table exists so that the other
   rules stay visible; a 72-column docstring limit (W505) is not enabled.
2. **Physical lines as the denominator** flatter releases with more blank
   and comment lines. Source lines are stored; the ordering of the series
   does not change under them, but check when a claim is close.
3. **`generated` is a heuristic.** It catches what carries a marker;
   generated files without one land in `stdlib`. The classifier's docstring
   names the false positives it avoids; new ones would show up in
   `make generated`.
4. **Vendored code counts as stdlib.**
5. **The two instruments disagree in level.** Ruff's preview E2/E3 rules
   are ports of pycodestyle's, not the same code, and its E501 counts
   characters differently. Read the ruff column as a second opinion on
   direction, not on level.
6. **Old files under a new tokenizer.** pycodestyle tokenises 3.0-era files
   with Python 3.14's tokenizer and ruff parses them with `--target-version
   py37`. A few dozen files per old release fail (the non-style column), all
   of them test fixtures or lib2to3's Python 2 samples.
7. **One point per minor.** The sensitivity set shows how far a late patch
   release drifts from its first (3.13.9 against 3.13.0); it is not a
   confidence interval.
8. **No 2.x yet.**

## Planned

- **Age cohorts.** Blame every violating line of the latest release to the
  year it was written (this needs a CPython git clone, not a tarball) and
  report density by cohort. This is the test of "practice what you preach":
  whether code written after PEP 8 follows it.
- **2.x.** pycodestyle only, from 2.0 or 2.7, to put the pre-PEP 8 library
  on the chart.
- **What CPython enforces.** Since 2023 CPython runs ruff in pre-commit on
  `Lib/test`, `Tools` and `Doc` with a narrow rule set; counting those rules
  separately would show enforcement in the data.

## Claims

Say *density*, never *errors*. Name the instrument. Give the release, not
the minor's average. Never add non-style counts to style counts. Never set a
number from `validation/` beside a number from `data/measurements/`: they
come from different instruments. A test-suite count is a statement about the
test suite, not about the library.
