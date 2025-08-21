# Makefile à placer à la racine du projet

PYTHON := /home/pipo/envs/vmix/bin/python3
PIP := pip
PKG    := mixonaut

# ----------------------------------------
# ENVIRONNEMENT
# ----------------------------------------
# -------- Install dev / hooks --------
install-dev:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -r dev-requirements.txt
	$(PYTHON) -m pre_commit install

hooks:
	$(PYTHON) -m pre_commit run --all-files

# -------- Format / Docstrings / Imports --------
docstrings:
	$(PYTHON) -m docformatter --in-place --recursive $(PKG)/

format:
	$(PYTHON) -m isort --profile black $(PKG)/
	$(PYTHON) -m black $(PKG)/

check-format:
	$(PYTHON) -m isort --profile black --check-only $(PKG)/
	$(PYTHON) -m black --check $(PKG)/

# -------- Lint / Types --------
lint:
	$(PYTHON) -m flake8 $(PKG)/

types:
	$(PYTHON) -m mypy $(PKG)/

# -------- All-in-one rapide --------
qa: docstrings format lint types

# -------- Clean --------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
