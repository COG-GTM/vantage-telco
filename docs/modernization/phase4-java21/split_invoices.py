#!/usr/bin/env python3
"""Split a rendered batch into one file per invoice and a cycle summary."""

import re
import sys
from pathlib import Path

ACCOUNT = re.compile(r"^Account:\s+(.+?)\s*$")


def blocks(text):
    current = []
    for line in text.splitlines(keepends=True):
        if line.strip():
            current.append(line)
        elif current:
            yield "".join(current)
            current = []
    if current:
        yield "".join(current)


def write_block(output_dir, name, content):
    output_dir.joinpath(name).write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} INPUT OUTPUT_DIR")

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    invoice_number = 0
    for block in blocks(input_path.read_text(encoding="utf-8")):
        first_line = block.splitlines()[0]
        if first_line == "BILLING CYCLE SUMMARY":
            write_block(output_dir, "cycle-summary.txt", block)
            continue
        if first_line != "VANTAGE NETWORK SERVICES":
            raise ValueError(f"unexpected block: {first_line!r}")
        account = next(
            (match.group(1) for line in block.splitlines() if (match := ACCOUNT.match(line))),
            None,
        )
        if account is None:
            raise ValueError("invoice block has no Account line")
        invoice_number += 1
        write_block(output_dir, f"{invoice_number:04d}-{account}.txt", block)


if __name__ == "__main__":
    main()
