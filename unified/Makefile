PY ?= python3
PORT ?= 8000
PERIOD ?= 2026-07

.PHONY: install test lint typecheck check run parity

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy

check: lint typecheck test

run:
	$(PY) -m uvicorn oss.api.main:app --port $(PORT)

parity:
	$(PY) tools/parity.py --period $(PERIOD)
