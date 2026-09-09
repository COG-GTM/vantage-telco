"""Runtime settings resolution.

Every setting ``NAME`` is resolved in order:

1. ``<NAME>_FILE`` — path to a file whose contents are the value (Docker / Kubernetes
   secret mounts such as ``/run/secrets/mongo_uri``). Surrounding whitespace and the
   trailing newline are stripped.
2. ``NAME`` — the plain environment variable (local development fallback).
3. ``None``.

A ``_FILE`` variable that points at a missing or empty file falls through to the plain
environment variable rather than raising, so a misconfigured mount degrades to "unset".
"""

from __future__ import annotations

import os
from pathlib import Path

FILE_SUFFIX = "_FILE"


def get_setting(name: str) -> str | None:
    file_path = os.environ.get(f"{name}{FILE_SUFFIX}")
    if file_path:
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value:
            return value
    return os.environ.get(name) or None
