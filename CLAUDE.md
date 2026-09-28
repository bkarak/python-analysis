# CLAUDE.md

## What this is

Research workspace for **"does CPython's standard library practice what PEP 8
preaches?"**: a fixed-instrument measurement of PEP 8 conformance across
CPython releases, normalised per thousand lines and split into the library
proper, its tests and its generated files. Protocol:
[PROTOCOL.md](PROTOCOL.md). Current numbers: [RESULTS.md](RESULTS.md).

It grew out of the November 2025 post [Python PEP8: Practice what you
preach](https://bkarak.wizhut.tech/blog/2025/15112025) and the repo
`bkarak/python-analysis` (private since 2026-09-28; transferred the same day from the `wizhut` organisation to the personal account, so the post's original link redirects), whose git history this tree carries (the old
pipeline is commit `fe6a6fa`). [validation/](validation/README.md) is the
2026-09-28 check of that post: its numbers reproduce exactly and its trend is
a ruff configuration artifact. The harness here is the replacement.

Sibling research projects: `research/kyori`.

## Commands

- `make setup` — uv environment with pycodestyle 2.15.0 and ruff 0.14.4 under Python 3.14
- `make fetch` — download and extract the series and the sensitivity set into `work/` (about 450 MB down, 2.2 GB on disk, gitignored); records SHA-256s in `data/tarballs.sha256`
- `make measure` — both instruments on every release, about 40 s each with `JOBS=12` → `data/measurements/<v>.json`, raw diagnostics in `work/raw/`
- `make results` — prints the RESULTS.md tables
- `make generated` — prints what the classifier calls generated, per release; eyeball it after touching `harness/classify.py`
- `make cpython` — clones CPython into `work/cpython` once (about 1 GB); `make cohorts` blames every line of `COHORT` (default 3.14.0) and writes `data/cohorts/<v>.json` in about two minutes; `make results` then prints the cohort tables too
- `make validation` — re-runs the November 2025 check (its 17 releases must be in `work/`)
- `VERSIONS="3.15.0" make fetch measure` — add a release; `make list-releases` shows what python.org has

## Layout

| Path | Role |
|---|---|
| `PROTOCOL.md` | Question, corpus, instruments, categories, metrics, known problems, planned work, claims |
| `RESULTS.md` | Current tables with the reading and caveats; tables come from `make results` |
| `harness/releases.py` | List python.org releases; fetch and extract tarballs; record checksums |
| `harness/measure.py` | The two instruments, the file inventory, the per-release JSON |
| `harness/classify.py` | tests / generated / stdlib rules |
| `harness/results.py` | Aggregates the measurements and cohorts into the tables |
| `harness/cohorts.py` | git blame at the release's tag; lines and diagnostics by the year and era of their last edit |
| `data/measurements/` | One JSON per release: counts by rule, category, category × rule, top files, the generated list, the instrument that produced it |
| `data/tarballs.sha256` | Digest of every tarball measured |
| `data/cohorts/` | One JSON per blamed release: per category, per year and per era, lines and style counts by rule |
| `validation/` | The check of the 2025 post: its own two scripts, their JSON, and a README with the findings |
| `work/` | Tarballs, extracted trees, raw diagnostics; gitignored |

## Conventions

- Never set a number produced under one instrument configuration beside one produced under another. Bumping pycodestyle, ruff, the Python version or a flag means re-measuring every release and saying so in RESULTS.md.
- The harness runs ruff with `--isolated`. Keep `pyproject.toml` free of a `[tool.ruff]` section and at `requires-python >= 3.13`: `validation/breakdown.py` reproduces the 2025 numbers by relying on the target-version inference that combination produces.
- The series is the first release of each minor. Patch releases are the sensitivity set, never averaged in.
- Categories are decided tests first, then generated, then stdlib. The headline number is the stdlib category's density under pycodestyle.
- Style counts exclude syntax and I/O failures; those are reported beside them, never added.
- Commit `data/measurements/*.json`, `data/cohorts/*.json` and `data/tarballs.sha256`; never `work/` (tarballs, trees, the CPython clone, raw diagnostics, the blame dump).
- A cohort is the date of a line's last edit, never its origin; say so when citing one.
- When a number in RESULTS.md changes, update whatever cites it in the same pass: the follow-up post drafted on 2026-09-28 at `~/devel/personal/html-bkarak/web-app/public/blog-data/2026/28092026.html` ("Python PEP8: Practice what you preach, take two"; it quotes Tables 1 and 2 of RESULTS.md and the cohort era table), and a `/labs` page on corporate-site if one exists by then.
- Read *Known problems* in PROTOCOL.md before citing anything.
