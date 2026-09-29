# One point per minor release, plus patch releases as a sensitivity check.
SERIES      := 3.0 3.1 3.2 3.3.0 3.4.0 3.5.0 3.6.0 3.7.0 3.8.0 3.9.0 3.10.0 3.11.0 3.12.0 3.13.0 3.14.0
SENSITIVITY := 3.0.1 3.1.1 3.2.1 3.12.11 3.13.9
PY2         := 2.0.1 2.7
VERSIONS    ?= $(PY2) $(SERIES) $(SENSITIVITY)
JOBS        ?= 12
COHORT      ?= 3.14.0

default: help

help:            ## this list
	awk 'BEGIN{FS=":.*## "} /^[a-z-]+:.*## /{printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	echo "  VERSIONS=... selects releases (default: the series + the sensitivity set)"

setup:           ## create .venv with the pinned instruments (uv)
	uv sync

list-releases:   ## every release directory on python.org, with its date
	uv run harness/releases.py list

fetch:           ## download + extract $(VERSIONS) into work/ (skips what is there), record SHA-256s
	uv run harness/releases.py fetch $(VERSIONS)

measure:         ## run both instruments on $(VERSIONS) -> data/measurements/<v>.json
	uv run harness/measure.py --jobs $(JOBS) $(VERSIONS)

measure-all:     ## every 2.x and 3.x release on python.org, fetched, measured and purged one by one (~1 hour, resumable)
	uv run harness/allreleases.py --jobs $(JOBS)

results:         ## print the RESULTS.md tables from data/measurements/
	uv run harness/results.py

generated:       ## list the files the classifier calls generated, per release (eyeball this after changing it)
	for v in $(VERSIONS); do echo "== $$v"; uv run harness/classify.py work/Python-$$v/Lib; done

cpython:         ## clone CPython into work/cpython (once, ~1 GB); blame needs the history
	@test -d work/cpython || git clone https://github.com/python/cpython.git work/cpython

cohorts: cpython ## blame every line of $(COHORT) and report density by edit date -> data/cohorts/
	uv run harness/cohorts.py --jobs $(JOBS) $(COHORT)

cohorts-content: cpython ## the second dating: blame $(COHORT) with -w -M -C -> data/cohorts/<v>-content.json
	uv run harness/cohorts.py --jobs $(JOBS) --dating content $(COHORT)

sensitivity:     ## era boundaries a year either way, source lines as denominator, bootstrap over files -> data/sensitivity/
	uv run harness/sensitivity.py $(COHORT)

linelength:      ## line-length distribution per release and per era, doc lines over 72 -> data/linelength/
	uv run harness/linelength.py --jobs $(JOBS) $(VERSIONS)

enforcement:     ## what CPython's own ruff hooks select, counted where they run and in Lib/ proper -> data/enforcement/
	uv run harness/enforcement.py $(COHORT)

survival: cpython ## reverse blame from the 3.8 branch point to $(COHORT): which violations survive -> data/survival/
	uv run harness/survival.py --jobs $(JOBS) 3.8.0 $(COHORT)

packages:        ## density per package of $(COHORT), and the vendored packages -> data/packages/
	uv run harness/packages.py $(COHORT)

baselines:       ## the same instruments on django, numpy, pip, requests and black -> data/baselines/
	uv run harness/baselines.py --jobs $(JOBS)

analyses: cohorts cohorts-content sensitivity linelength enforcement survival packages baselines ## everything after measure

charts:          ## the SVG figures of RESULTS.md from data/ -> data/charts/
	uv run harness/charts.py

POST_DIR ?= $(HOME)/devel/personal/html-bkarak/web-app/public/blog-data/2026/28092026
charts-post: charts ## the figures and the dark hero into the follow-up post's asset directory
	uv run harness/charts.py --hero $(POST_DIR) && cp data/charts/*.svg $(POST_DIR)/

validation:      ## re-run the check of the November 2025 post (17 releases, see validation/README.md)
	uv run validation/breakdown.py && uv run validation/isolated.py

clean-work:      ## delete the extracted trees, tarballs and raw diagnostics (not the measurements)
	rm -rf work/Python-* work/raw

.PHONY: default help setup list-releases fetch measure measure-all results generated charts charts-post cpython cohorts cohorts-content sensitivity linelength enforcement survival packages baselines analyses validation clean-work
