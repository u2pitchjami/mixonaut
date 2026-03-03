PYTHON ?= python3
PIP    ?= $(PYTHON) -m pip
PKG    ?= src

.PHONY: init fmt check types qa clean patch compile help

init:
	./dev_scripts/rebuild_env.sh
	python -m pre_commit install

hooks:
	python -m pre_commit install

patch:
	./dev_scripts/patch.sh

compile:
	./dev_scripts/patch.sh compile

fmt:
	ruff check $(PKG) --fix
	ruff format $(PKG)

check:
	ruff check $(PKG)
	ruff format $(PKG) --check

types:
	mypy $(PKG)

vulture:
	vulture $(PKG) --min-confidence 80

qa: fmt types vulture

clean:
	rm -rf .venv .mypy_cache .ruff_cache
	find . -name "__pycache__" -type d -exec rm -rf {} +

test:
	pytest

help:
	@echo "Targets:"
	@echo "  init     : rebuild environment"
	@echo "  patch    : dependency patch management"
	@echo "  compile  : recompile lock files"
	@echo "  fmt      : auto-fix lint + format"
	@echo "  check    : lint + format check"
	@echo "  types    : run mypy"
	@echo "  qa       : fmt + types + vulture"
	@echo "  clean    : remove caches"
	@echo "  test     : run test suite"
	@echo "  vulture  : run vulture for dead code detection"