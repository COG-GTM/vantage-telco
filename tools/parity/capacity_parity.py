"""Cross-estate capacity parity.

Asks meridian-telco's inventory-api (``GET /capacity?requested=N``) and this
service (``app.inventory.locations``) for the sales capacity check at every
serviceable location both estates carry, over a sweep of requested bandwidths,
and prints every location where buffer, availability or the can-support verdict
disagree.

    python tools/parity/capacity_parity.py [--meridian-dir ../meridian-telco] [--requested 0,250,350,...]

The meridian binaries are built on demand with ``make -C <meridian-dir>``.
Exit status is 0 when every location agrees, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.inventory import capacity_lib  # noqa: E402
from app.inventory.locations import list_locations  # noqa: E402

DEFAULT_REQUESTED = "0,100,250,300,350,500,1000,2500"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def meridian_inventory_api(meridian_dir: Path, build: bool = True) -> Iterator[str]:
    if build:
        subprocess.run(["make", "-s", "-C", str(meridian_dir), "bin/inventory-api"], check=True)
    binary = meridian_dir / "bin" / "inventory-api"
    if not binary.exists():
        raise SystemExit(f"{binary} not found; build meridian-telco first")
    port = _free_port()
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.Popen(
            [str(binary), "--port", str(port), "--db", str(Path(tmp) / "meridian.db"),
             "--locations", str(meridian_dir / "data" / "locations.csv")],
            cwd=str(meridian_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            yield base
        finally:
            proc.terminate()
            proc.wait(timeout=5)


def meridian_capacity(base: str, requested: int) -> Dict[str, Dict]:
    with urllib.request.urlopen(f"{base}/capacity?requested={requested}", timeout=10) as resp:
        body = json.load(resp)
    return {
        l["LOC_CD"]: {
            "total": l["TOTAL_CAP_MBPS"],
            "allocated": l["ALLOC_CAP_MBPS"],
            "buffer": l.get("BUFFER_CAP_MBPS", 0),
            "available": l["AVAIL_CAP_MBPS"],
            "can_support": l["CAN_SUPPORT"],
        }
        for l in body["locations"]
    }


def vantage_capacity(requested: int) -> Dict[str, Dict]:
    return {
        l["location_code"]: {
            "total": l["total_capacity_mbps"],
            "allocated": l["allocated_mbps"],
            "buffer": l["maintenance_buffer_mbps"],
            "available": l["available_mbps"],
            "can_support": l["can_support"],
        }
        for l in list_locations(requested_mbps=requested)
    }


def _yn(flag: bool) -> str:
    return "yes" if flag else "no"


def compare(meridian_dir: Path, requested: List[int], build: bool = True) -> int:
    diffs = []
    checks = 0
    with meridian_inventory_api(meridian_dir, build=build) as base:
        snapshot_req = 350 if 350 in requested else requested[0]
        snapshot = (meridian_capacity(base, snapshot_req), vantage_capacity(snapshot_req))
        shared = sorted(set(snapshot[0]) & set(snapshot[1]))
        only_one = sorted(set(snapshot[0]) ^ set(snapshot[1]))
        for req in requested:
            legacy = meridian_capacity(base, req)
            modern = vantage_capacity(req)
            for code in shared:
                checks += 1
                left, right = legacy[code], modern[code]
                fields = [k for k in ("total", "allocated", "buffer", "available", "can_support") if left[k] != right[k]]
                if fields:
                    diffs.append((req, code, left, right, fields))

    print(f"capacity parity  capacity-lib {capacity_lib.version()}  rule: {capacity_lib.rule()}")
    print(f"locations={len(shared)}  requested sweep={','.join(map(str, requested))} Mbps  checks={checks}  differing={len(diffs)}")
    if only_one:
        print(f"locations present in only one system: {', '.join(only_one)}")
    print()
    print(f"snapshot at requested={snapshot_req} Mbps")
    print(f"{'LOC':<7} {'TOTAL':>6} {'ALLOC':>6} | {'MER BUF':>7} {'MER AVAIL':>9} {'MER OK':>6} | {'VAN BUF':>7} {'VAN AVAIL':>9} {'VAN OK':>6} | MATCH")
    print("-" * 96)
    for code in shared:
        left, right = snapshot[0][code], snapshot[1][code]
        match = "==" if left == right else "DIFF"
        print(f"{code:<7} {left['total']:>6} {left['allocated']:>6} | {left['buffer']:>7} {left['available']:>9} {_yn(left['can_support']):>6} | "
              f"{right['buffer']:>7} {right['available']:>9} {_yn(right['can_support']):>6} | {match}")
    print("-" * 96)

    if not shared or only_one:
        print("\nCAPACITY PARITY FAILED: the two inventories do not cover the same locations")
        return 1
    if diffs:
        print()
        print("differences (requested, location, field: meridian -> vantage)")
        for req, code, left, right, fields in diffs[:40]:
            detail = "  ".join(f"{f}: {left[f]} -> {right[f]}" for f in fields)
            print(f"  {req:>5} {code:<7} {detail}")
        if len(diffs) > 40:
            print(f"  ... {len(diffs) - 40} more")
        print("\nCAPACITY PARITY FAILED")
        return 1
    print("\nCAPACITY PARITY OK: 0 differences")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--meridian-dir",
        default=os.environ.get("MERIDIAN_DIR", str(REPO_ROOT.parent / "meridian-telco")),
    )
    parser.add_argument("--requested", default=DEFAULT_REQUESTED, help="comma-separated requested Mbps values")
    parser.add_argument("--no-build", action="store_true", help="use the meridian binaries as they are")
    args = parser.parse_args()

    meridian_dir = Path(args.meridian_dir).resolve()
    if not (meridian_dir / "inventory-api").is_dir():
        raise SystemExit(f"{meridian_dir} does not look like a meridian-telco checkout")
    requested = [int(x) for x in args.requested.split(",") if x.strip()]
    return compare(meridian_dir, requested, build=not args.no_build)


if __name__ == "__main__":
    sys.exit(main())
