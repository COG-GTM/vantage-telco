PY ?= python3
PORT ?= 8000
PERIOD ?= 2026-07
MERIDIAN_DIR ?= ../meridian-telco

.PHONY: install test run fixtures parity demo

install:
	$(PY) -m pip install -r requirements.txt

test:
	$(PY) -m pytest -q

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
