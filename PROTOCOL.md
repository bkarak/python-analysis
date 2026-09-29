# Protocol: does the standard library practice what PEP 8 preaches?

PEP 8 names the code in `Lib/` as its subject. This project measures how far
that code conforms to PEP 8, how the conformance has moved from 3.0 (2008) to
3.14 (2025), and where the non-conformance sits. It replaces the pipeline
behind the November 2025 post [Python PEP8: Practice what you
preach](https://bkarak.wizhut.tech/blog/2025/15112025), whose numbers were
reproduced and taken apart in [validation/README.md](validation/README.md):
they were right and their trend was an artifact of the tool's configuration.
Everything below exists to make that impossible to repeat.

Run: `make fetch` then `make measure`; tables with `make results`;
`make cpython` and `make cohorts` for the age cohorts; `make analyses` for
everything from the age cohorts on. Numbers and their reading:
[RESULTS.md](RESULTS.md).

## Question

Two hypotheses were left open in November 2025: *nobody cares about PEP 8*,
or *the standard library is getting less Pythonic*. The series here answers
the second. The first is what **Age cohorts** answers: PEP 8 tells
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
- **The sensitivity set** is every other release python.org offers: all
  the patch releases of every minor, 264 tarballs in all together with the
  series (`make measure-all` fetches, measures and purges them one at a
  time, keeping only their JSON). They are reported per minor as the spread
  of a minor's releases around its first, and never averaged into the
  series. A patch release only backports fixes, so the twenty-five patch
  releases of 3.9 are twenty-five near-copies of one point; averaging them
  weights minors unequally, and in 2025 it averaged two instruments into one
  number for 3.13.
- **A pre-release** of the next x.y.0 (3.15.0rc2 in September 2026) stands
  in for its final until the final ships, flagged as such in the series
  table and used for nothing else. Ruff's target version is clamped to
  py314, the newest ruff 0.14.4 knows, so any 3.15 syntax it cannot parse
  counts as non-style, not as style.
- **Python 2** is in the series as 2.0.1 and 2.7 (python.org has no
  `Python-2.0.tgz`, so the first patch release stands in for 2.0). See
  **Python 2** below for what the instruments can do with it.

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

## Age cohorts

The series says whether the library is getting less Pythonic. Whether
anyone cares is a different question, because PEP 8 tells maintainers not
to reformat code that already works: old lines keep their old style by
policy, and the test is the code written after the guide. `make cohorts`
runs it for the latest series release (`COHORT=` picks another; its tag,
tarball and raw diagnostics must exist).

- **Blame.** Every `.py` under `Lib/` at the release's tag is blamed with
  `git blame --line-porcelain <tag> -- Lib/<file>` in the clone at
  `work/cpython` (`make cpython`, once, about 1 GB). Each line is dated by
  the **author time** of the commit that last edited it. That is the last
  edit, not the line's origin: a line reformatted in 2010 is 2010's. For a
  style question that is the right date, since the last editor was the
  last person with a chance to make the line conform; the cost is under
  Known problems 9 to 11. No `-w` (a whitespace change is an edit here),
  no `-M` or `-C` (moved code is dated at the move).
- **Alignment.** The tarball's files are compared with the tag's blobs by
  git object hash, and a file is skipped if they differ or if blame and
  the inventory disagree on its line count; the cohort JSON records what
  was skipped and how many diagnostics could not be attributed. For
  3.14.0 all 1830 files match and nothing is lost.
- **Attribution.** A diagnostic belongs to the cohort of the line it is
  reported on. Blank-line rules (E3) are reported on the definition after
  the gap, so they blame that line's editor.
- **Cohorts.** By calendar year, and by era, each era starting on the day
  of an event in how CPython's code was written or reviewed: PEP 8's
  creation (2001-07-05), the 3.0 release (2008-12-03), the move to GitHub
  pull requests (2017-02-10) and the first ruff hook in CPython's
  pre-commit configuration (2023-09-12, gh-60283). Density is style
  diagnostics per thousand lines of the cohort, by category and rule
  family as elsewhere; the era table also gives the density without E5,
  because line length behaves unlike every other family.
- **Output.** `data/cohorts/<v>.json` (committed): per category, per year
  and per era, the lines and each instrument's style counts by rule.
  `work/raw/<v>.blame.tsv` (not committed): the author time of every line.

## Naming

PEP 8's naming conventions are not pycodestyle's business, so a third
instrument covers them: ruff's N rules, its port of pep8-naming (N801 to
N818: class, function, argument and variable names, `self` and `cls`,
import aliases, error suffixes), run `--isolated --select N` on the same
file list as everything else and stored in each measurement under `naming`.
Counted per category and, through the blame dump, per cohort. It is a rule
count like the others, with the same denominator; n/a for 2.x, which ruff
cannot parse.

## Rule severity

A bare `except` is not a missing blank line. The semantic rules are E711 to
E714 (comparisons to None, True and False, membership and identity tests),
E721 (type comparison), E722 (bare except), E731 (lambda assignment), E741
to E743 (ambiguous names) and the W6 deprecations: they describe what the
code does. Everything else describes how it is laid out and is cosmetic.
Both are reported per release and per era. The headline density counts
both, and says so; the list lives in `harness/results.py`.

## Line length

E501 counts lines over 79. The distribution says where they sit: per
release and per era, the share of lines over 79, 88, 99 and 120 characters
and the median, 90th percentile and maximum length of the lines over 79,
measured as pycodestyle measures E501 (characters after decoding, trailing
whitespace stripped, a tab counting one; the URL exception not applied).
PEP 8's 72-column limit for docstrings and comments, which pycodestyle only
checks when asked, is counted as W505 with `--max-doc-length=72`.
`make linelength`; `data/linelength/<v>.json`.

## Two datings

Blame dates the last edit of a line. `make cohorts-content` dates it a
second way, with `git blame -w -M -C`: whitespace-only edits are ignored,
and lines moved or copied between files keep their origin. The two datings
are reported side by side for the era table; where they differ, the
difference is the share of lines whose last edit was cosmetic or a move.
Neither is the line's birth: an edit that changed the text (the Python 3
conversion, a renamed variable) moves the line under both.
`data/cohorts/<v>-content.json`.

## Enforcement

CPython's `.pre-commit-config.yaml` runs ruff on some trees and not on
others, each tree under its own `.ruff.toml` chain. `make enforcement`
reads the hooks, resolves the rules and the line length each one's chain
selects (ruff's defaults, E4, E7, E9 and F at 88 columns, where the chain
says nothing) and counts those rules three ways with the ruff pinned here:
in the tree under CPython's configuration, which is what the hook checks
and should be zero at release; in the tree with the configuration's
excludes dropped; and in the library proper, where no hook runs. The ruff
version CPython pinned is recorded (`ruff_pre_commit_rev`); a newer ruff
reports rules the pinned one did not have, which is why a hook can show a
non-zero count under its own configuration. `data/enforcement/<v>.json`.

## Fix behaviour

Does a violation go away when its line is touched, and are violating lines
touched more than others? `make survival` takes an older release and the
latest. The start is the merge base of the two tags, the commit where the
older minor branched off main (release tags live on release branches and
are not ancestors of later tags); its `Lib/` is archived and measured with
pycodestyle, and every line is reverse-blamed to the end tag with
`git blame --reverse`. A line reported under the end commit is unchanged
there, at a known place; any other line was edited or removed. A violation
survives when its line is unchanged and the end release's own diagnostics
carry the same rule at that place. Reported for the stdlib proper of the
start, per rule, next to the survival of all its lines.
`data/survival/<from>-<to>.json`.

## Packages and vendored code

`make packages` groups the stdlib proper of a release by top-level package
or module and reports the density of each, so that a reader can see
whether the non-conformance is a few packages or the whole tree. Vendored
code, meaning code maintained outside CPython and synced in, is listed in
`harness/packages.py` with its origin (tomllib, `_pyrepl`,
`importlib.metadata`, `importlib.resources`, `zipfile._path`); its density
and the library's without it are reported. It stays inside the `stdlib`
category everywhere else: it is what a user imports, and the headline moves
by about a point without it. `data/packages/<v>.json`.

## Sensitivity

`make sensitivity` checks the cohort result three ways, on the stdlib
proper: every era boundary moved a year earlier and a year later; source
lines (non-blank, non-comment) as the denominator instead of physical
lines; and a bootstrap over files, the unit of resampling, 1000 resamples
with replacement under a fixed seed, giving a 95 % interval (2.5th to
97.5th percentile) for each era's density with and without E5. Cohorts are
populations, not samples; the interval says how much a number depends on
which files carry it. `data/sensitivity/<v>.json`.

## Baselines

`make baselines` runs the same instruments, flags and categories on the
current sdists of Django, NumPy, pip, requests and black, downloaded from
PyPI and pinned by SHA-256 in each result, measuring each project's own
source tree (pip without its `_vendor` directory; black without its
vendored `blib2to3`) with ruff's target at py310. Their densities put a
ceiling and a floor around the library's. A black-formatted project scores
high on E501 and E203 at 79 columns by construction, which is what the
`excl. E5` column is for. `data/baselines/<name>.json`.

## Python 2

pycodestyle tokenises Python 2 with Python 3.14's tokenizer and reports it,
so 2.0.1 and 2.7 are in the series under pycodestyle. ruff cannot parse
Python 2: its columns are n/a for 2.x, its non-style count there is the
parser giving up, and the naming instrument, which is ruff, is n/a too.

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
7. **One point per minor.** The spread of a minor's other releases is
   reported, not folded in; it is not a confidence interval, and for 2.7,
   whose eighteen patch releases span ten years, it is 20 per thousand
   lines, which the series does not show.
8. **No 2.x yet.**
9. **Blame dates the last edit.** The 2006 to 2008 cohorts hold every line
   the Python 3 conversion rewrote, whatever its origin, and any later mass
   edit (a reindent, an import cleanup) pulls lines forward. The pre-2001
   cohort is what survived untouched, a biased sample of what was written
   then.
10. **Moved code is dated at the move**, since blame runs without `-M` or
    `-C`: a package split or a rename turns 2005 code into a 2019 cohort.
11. **Backports keep their author time.** A fix written on main and
    cherry-picked to a release branch is dated when it was written, which
    is what is wanted; but a release branch's own commits can predate the
    tag by months, so the newest cohort is a little older than the tag.
12. **The severity split is a judgement.** E741 (a variable called `l`) is
    semantic here because the name reads as a digit; E703 (a trailing
    semicolon) is cosmetic although it is a statement rule. Change the list
    and both columns move.
13. **Naming has one instrument**, ruff's port of pep8-naming, with no
    second opinion.
14. **Enforcement is measured with today's ruff, not the pinned one.** A
    hook's count under its own configuration reports rules added since
    CPython pinned its version, not a hook that failed.
15. **Survival cannot tell edited from removed**, any more than blame can:
    a rewritten line and a deleted line both count as changed. Its start is
    the branch point, not the release: the 373 files that changed between
    the 3.8 branch point and 3.8.0 are measured as they were at the branch
    point.
16. **The baselines are five projects at one version each**, chosen by
    hand. They bound the library's number; they do not place it in a
    distribution.

## Planned

What is not done. Nothing here changes what the tables mean until it is
done and written into RESULTS.md.

1. **3.15.0**, due in October 2026: `VERSIONS=3.15.0 make fetch measure`,
   then `COHORT=3.15.0 make analyses`, and the post's promise is kept.
2. **A birth date for lines.** The content dating still moves a line under
   any edit of its text. A first-appearance date (the commit that
   introduced the line's text, through `git log -S` or a line-history
   walk) would bound the Python 3 conversion's pull properly; it is
   expensive and not done.
3. **The older imports** (`email` from mimelib, `ctypes`, `multiprocessing`,
   `json` from simplejson, `unittest`, `argparse`, `logging` …) arrived
   from outside too, decades ago, and are maintained in-tree since. They
   are not vendored here; a per-package origin list would let a reader
   split them out.

## Claims

Say *density*, never *errors*. Name the instrument. Give the release, not
the minor's average. Never add non-style counts to style counts. Never set a
number from `validation/` beside a number from `data/measurements/`: they
come from different instruments. A test-suite count is a statement about the
test suite, not about the library.
