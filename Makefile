# Makefile à placer à la racine du projet

PYTHON := /home/pipo/envs/vmix/bin/python3
PIP    ?= $(PYTHON) -m pip
PKG    ?= .

# ------- Phony -------
.PHONY: install-dev hooks fmt check lint types qa clean help

# ------- Install / Dev env -------
install-dev:
	$(PIP) install -U pip
	# deps projet (si tu as un fichier, sinon enlève la ligne)
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@if [ -f dev-requirements.txt ]; then $(PIP) install -r dev-requirements.txt; fi
	# outils qualité
	$(PIP) install ruff mypy pre-commit
	# (optionnel) docstrings auto - si tu veux conserver docformatter
	@if [ -f .use-docformatter ]; then $(PIP) install docformatter; fi
	# install editable du package
	$(PIP) install -e .

hooks:
	$(PYTHON) -m pre_commit install
	# passage initial sur tout le repo
	$(PYTHON) -m pre_commit run --all-files || true

# ------- Format & Lint -------
# Format code (remplace Black)
format:
	ruff format $(PKG)

# Auto-fix lint (imports/isort, pyupgrade, espaces, etc.)
fix:
	ruff check $(PKG) --fix

# Combo format + auto-fix (recommandé)
fmt: fix format

# Vérif sans modifier
check:
	ruff format $(PKG) --check
	ruff check $(PKG)

# Lint alias
lint: check

# ------- Types -------
types:
	mypy $(PKG)

# ------- All-in-one qualité -------
qa: fmt types

# ------- Clean -------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	rm -rf .mypy_cache .pytest_cache .ruff_cache

# ------- Help -------
help:
	@echo "Targets:"
	@echo "  install-dev   : installe deps projet + ruff+mypy+pre-commit"
	@echo "  hooks         : installe les hooks pre-commit et lance un scan"
	@echo "  fmt           : ruff check --fix + ruff format (auto-fix)"
	@echo "  check|lint    : vérifie le format et le lint sans modifier"
	@echo "  types         : lance mypy sur $(PKG)"
	@echo "  qa            : fmt + types"
	@echo "  clean         : nettoie caches et pyc"
