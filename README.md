# Python analysis: does the standard library practice what PEP 8 preaches?

A fixed-instrument measurement of PEP 8 conformance in CPython's `Lib/`
across releases. pycodestyle 2.15.0 (the reference implementation of PEP 8's
checkable rules) and ruff 0.14.4 as a cross-check, both with every
configuration file ignored, at 79 columns, on the same explicit file list;
one point per minor release from 3.0 to 3.14; rates per thousand lines,
split into the library proper, its tests and its generated files.
Protocol: [PROTOCOL.md](PROTOCOL.md). Current numbers: [RESULTS.md](RESULTS.md).

**The finding so far** (2026-09-28): the library proper went from 87.6 to
48.1 style diagnostics per thousand lines between 3.0 and 3.14.0. Every
rule family fell except line length, which doubled. Of everything a naive
count sees in 3.14.0, the test suite is 47 % and 78 generated files are
36 %; the library a user imports is 17 %. Dated by the commit that last
edited each line, code from every era is cleaner than the last except for
line length: long lines rise from 2 per thousand in code untouched since
before PEP 8 to 28 in code edited since 2023.

It grew out of the November 2025 post [Python PEP8: Practice what you
preach](https://bkarak.wizhut.tech/blog/2025/15112025) and its script, which
is this repo's history up to `fe6a6fa`. [validation/](validation/README.md)
reproduces that post's numbers exactly and shows its rising trend to be a
ruff configuration artifact: CPython 3.13.8 and later ship a `.ruff.toml`
that the pipeline honoured for those releases only.

## Setup

```bash
make setup          # uv: .venv with pycodestyle 2.15.0 and ruff 0.14.4 under Python 3.14
```

## Run

```bash
make fetch          # the series + sensitivity set into work/ (~450 MB down, ~2.2 GB on disk)
make measure        # both instruments on every release -> data/measurements/<v>.json (~3 s each)
make results        # the RESULTS.md tables
make generated      # what the classifier calls generated, per release
make cpython        # clone CPython into work/ (once, ~1 GB); blame needs the history
make cohorts        # blame every line of 3.14.0 -> data/cohorts/3.14.0.json (~2 min)

VERSIONS="3.15.0" make fetch measure    # add a release
make list-releases                       # what python.org offers
make validation                          # the check of the 2025 post (its 17 releases)
```

| Path | Role |
|---|---|
| `harness/releases.py` | list python.org releases; fetch, extract, checksum tarballs |
| `harness/measure.py` | the two instruments and the per-release JSON |
| `harness/classify.py` | tests / generated / stdlib |
| `harness/results.py` | the tables |
| `harness/cohorts.py` | blame at the tag, density by the date a line was last edited |
| `data/measurements/` | one JSON per release, committed |
| `data/cohorts/` | one JSON per blamed release, committed |
| `data/tarballs.sha256` | digest of every tarball measured |
| `validation/` | the 2025 check: scripts, JSON, findings |
| `work/` | tarballs, trees, raw diagnostics; gitignored |

Every tarball comes from `https://www.python.org/ftp/python/<v>/Python-<v>.tgz`;
`data/tarballs.sha256` says which bytes were measured.
