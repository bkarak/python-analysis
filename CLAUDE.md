# CLAUDE.md

## What this is

Research workspace for **"does CPython's standard library practice what PEP 8
preaches?"**: a fixed-instrument measurement of PEP 8 conformance across
CPython releases, normalised per thousand lines and split into the library
proper, its tests and its generated files. Protocol:
[PROTOCOL.md](PROTOCOL.md). Current numbers: [RESULTS.md](RESULTS.md).

It grew out of the November 2025 post [Python PEP8: Practice what you
preach](https://bkarak.wizhut.tech/blog/2025/15112025) and the public repo
`wizhut/python-analysis`, whose git history this tree carries (the old
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
| `harness/results.py` | Aggregates the measurements into the tables |
| `data/measurements/` | One JSON per release: counts by rule, category, category × rule, top files, the generated list, the instrument that produced it |
| `data/tarballs.sha256` | Digest of every tarball measured |
| `validation/` | The check of the 2025 post: its own two scripts, their JSON, and a README with the findings |
| `work/` | Tarballs, extracted trees, raw diagnostics; gitignored |

## Conventions

- Never set a number produced under one instrument configuration beside one produced under another. Bumping pycodestyle, ruff, the Python version or a flag means re-measuring every release and saying so in RESULTS.md.
- The harness runs ruff with `--isolated`. Keep `pyproject.toml` free of a `[tool.ruff]` section and at `requires-python >= 3.13`: `validation/breakdown.py` reproduces the 2025 numbers by relying on the target-version inference that combination produces.
- The series is the first release of each minor. Patch releases are the sensitivity set, never averaged in.
- Categories are decided tests first, then generated, then stdlib. The headline number is the stdlib category's density under pycodestyle.
- Style counts exclude syntax and I/O failures; those are reported beside them, never added.
- Commit `data/measurements/*.json` and `data/tarballs.sha256`; never `work/`.
- When a number in RESULTS.md changes, update whatever cites it in the same pass: the blog post's correction, and a `/labs` page on corporate-site if one exists by then.
- Read *Known problems* in PROTOCOL.md before citing anything.
