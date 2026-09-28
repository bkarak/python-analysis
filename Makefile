# One point per minor release, plus patch releases as a sensitivity check.
SERIES      := 3.0 3.1 3.2 3.3.0 3.4.0 3.5.0 3.6.0 3.7.0 3.8.0 3.9.0 3.10.0 3.11.0 3.12.0 3.13.0 3.14.0
SENSITIVITY := 3.0.1 3.1.1 3.2.1 3.12.11 3.13.9
VERSIONS    ?= $(SERIES) $(SENSITIVITY)
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

results:         ## print the RESULTS.md tables from data/measurements/
	uv run harness/results.py

generated:       ## list the files the classifier calls generated, per release (eyeball this after changing it)
	for v in $(VERSIONS); do echo "== $$v"; uv run harness/classify.py work/Python-$$v/Lib; done

cpython:         ## clone CPython into work/cpython (once, ~1 GB); blame needs the history
	@test -d work/cpython || git clone https://github.com/python/cpython.git work/cpython

cohorts: cpython ## blame every line of $(COHORT) and report density by edit date -> data/cohorts/
	uv run harness/cohorts.py --jobs $(JOBS) $(COHORT)

validation:      ## re-run the check of the November 2025 post (17 releases, see validation/README.md)
	uv run validation/breakdown.py && uv run validation/isolated.py

clean-work:      ## delete the extracted trees, tarballs and raw diagnostics (not the measurements)
	rm -rf work/Python-* work/raw

.PHONY: default help setup list-releases fetch measure results generated cpython cohorts validation clean-work
