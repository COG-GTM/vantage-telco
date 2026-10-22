"""Vantage billing.

The billing rules are not implemented here: they come from
COG-GTM/telco-billing-rules, vendored under ``vendor/`` (meridian-telco builds
from the same ruleset). Change a rule there and re-vendor; never patch
``vendor/`` in place — ``vendor/vendor_check.py`` fails CI if you do.
"""

import sys
from pathlib import Path

_VENDORED = str(Path(__file__).resolve().parents[2] / "vendor" / "python")
if _VENDORED not in sys.path:
    sys.path.insert(0, _VENDORED)
