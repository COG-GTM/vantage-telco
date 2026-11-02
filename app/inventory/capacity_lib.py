"""ctypes binding to the shared capacity-lib (``vendor/capacity-lib``).

meridian-telco compiles the same library into its C++ binaries, so both estates
run one implementation of the capacity rule. The shared object is built on first
use with ``make -C vendor/capacity-lib lib``; set ``CAPACITY_LIB_PATH`` to load a
prebuilt ``libcapacity.so`` instead.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from functools import lru_cache
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[2] / "vendor" / "capacity-lib"


@lru_cache(maxsize=1)
def _lib() -> ctypes.CDLL:
    path = os.environ.get("CAPACITY_LIB_PATH")
    if not path:
        if not (LIB_DIR / "src" / "capacity.cpp").exists():
            raise RuntimeError(f"{LIB_DIR} is missing: run git submodule update --init")
        built = LIB_DIR / "build" / "libcapacity.so"
        subprocess.run(["make", "-s", "-C", str(LIB_DIR), "lib"], check=True)
        path = str(built)
    lib = ctypes.CDLL(path)
    for name in ("capacity_available_capacity", "capacity_can_support"):
        getattr(lib, name).argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        getattr(lib, name).restype = ctypes.c_int
    lib.capacity_maintenance_buffer_mbps.argtypes = [ctypes.c_int]
    lib.capacity_maintenance_buffer_mbps.restype = ctypes.c_int
    lib.capacity_maintenance_buffer_pct.argtypes = []
    lib.capacity_maintenance_buffer_pct.restype = ctypes.c_int
    for name in ("capacity_rule", "capacity_lib_version"):
        getattr(lib, name).argtypes = []
        getattr(lib, name).restype = ctypes.c_char_p
    return lib


def available_capacity(total_mbps: int, alloc_mbps: int, buffer_mbps: int) -> int:
    return _lib().capacity_available_capacity(int(total_mbps), int(alloc_mbps), int(buffer_mbps))


def maintenance_buffer_mbps(total_mbps: int) -> int:
    return _lib().capacity_maintenance_buffer_mbps(int(total_mbps))


def can_support(total_mbps: int, alloc_mbps: int, requested_mbps: int) -> bool:
    return bool(_lib().capacity_can_support(int(total_mbps), int(alloc_mbps), int(requested_mbps)))


def maintenance_buffer_pct() -> int:
    return _lib().capacity_maintenance_buffer_pct()


def rule() -> str:
    return _lib().capacity_rule().decode()


def version() -> str:
    return _lib().capacity_lib_version().decode()
