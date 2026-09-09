"""Runtime settings: read from ``<NAME>_FILE`` (a mounted secret) or ``<NAME>``."""

from __future__ import annotations

import os
from pathlib import Path


def setting(name: str, default: str | None = None) -> str | None:
    """Return ``name`` from ``<name>_FILE`` or the environment."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        return Path(path).read_text(encoding="utf-8").rstrip("\r\n")
    return os.environ.get(name, default)
