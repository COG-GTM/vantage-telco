PY ?= python3
PORT ?= 8000
PERIOD ?= 2026-07
MERIDIAN_DIR ?= ../meridian-telco
COV_MIN ?= 85

.PHONY: install test run fixtures parity demo lint typecheck audit coverage sbom

install:
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy

audit:
	$(PY) -m pip_audit -r requirements.txt -r requirements-dev.txt

coverage:
	$(PY) -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=$(COV_MIN)

sbom:
	command -v syft >/dev/null || (echo "syft not installed: see docs/modernization/secrets.md#sbom" && exit 1)
	syft dir:. -o cyclonedx-json > sbom-python.cdx.json
	syft dir:java/vantage-report -o cyclonedx-json > sbom-java.cdx.json

run:
	$(PY) -m uvicorn app.main:app --port $(PORT)

fixtures:
	$(PY) tools/fixtures/generate_fixtures.py --meridian-dir $(MERIDIAN_DIR)

parity:
	$(PY) tools/parity/parity.py --period $(PERIOD) --meridian-dir $(MERIDIAN_DIR)

# Both invoice registers side by side:
#   vantage  http://localhost:8000/dashboard/billing
#   meridian http://localhost:8083/billing.html  (invoice-api on :8082)
demo:
	$(MAKE) -C $(MERIDIAN_DIR) demo & \
	$(PY) -m uvicorn app.main:app --port $(PORT) & \
	wait
