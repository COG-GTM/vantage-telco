PY ?= python3
PORT ?= 8000
PERIOD ?= 2026-07
MERIDIAN_DIR ?= ../meridian-telco

.PHONY: install capacity-lib test run fixtures parity capacity-parity demo

install: capacity-lib
	$(PY) -m pip install -r requirements.txt

# shared capacity rule, vendored as a git submodule (loaded with ctypes)
capacity-lib:
	@test -f vendor/capacity-lib/Makefile || git submodule update --init vendor/capacity-lib
	$(MAKE) -s -C vendor/capacity-lib lib

test: capacity-lib
	$(MAKE) -s -C vendor/capacity-lib check
	$(PY) -m pytest -q

run:
	$(PY) -m uvicorn app.main:app --port $(PORT)

fixtures:
	$(PY) tools/fixtures/generate_fixtures.py --meridian-dir $(MERIDIAN_DIR)

parity:
	$(PY) tools/parity/parity.py --period $(PERIOD) --meridian-dir $(MERIDIAN_DIR)

capacity-parity: capacity-lib
	$(PY) tools/parity/capacity_parity.py --meridian-dir $(MERIDIAN_DIR)

# Both invoice registers side by side:
#   vantage  http://localhost:8000/dashboard/billing
#   meridian http://localhost:8083/billing.html  (invoice-api on :8082)
# and both capacity checks:
#   vantage  http://localhost:8000/capacity?requested_mbps=350
#   meridian http://localhost:8083/capacity.html  (inventory-api on :8081)
demo:
	$(MAKE) -C $(MERIDIAN_DIR) demo & \
	$(PY) -m uvicorn app.main:app --port $(PORT) & \
	wait
