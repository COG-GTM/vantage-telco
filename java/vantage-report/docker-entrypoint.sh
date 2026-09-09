#!/bin/sh
# Render one billing cycle and write it to $OUTPUT_DIR/invoices-<period>.txt
# (the same content `mvn exec:java -Dexec.args="<period>"` prints to stdout).
set -eu

PERIOD="${1:-2026-07}"
OUTPUT_DIR="${OUTPUT_DIR:-/out}"
OUT_FILE="${OUTPUT_DIR}/invoices-${PERIOD}.txt"

mkdir -p "${OUTPUT_DIR}"
java -jar /srv/vantage/vantage-report.jar "$@" > "${OUT_FILE}"
echo "wrote ${OUT_FILE} ($(wc -l < "${OUT_FILE}") lines)"
