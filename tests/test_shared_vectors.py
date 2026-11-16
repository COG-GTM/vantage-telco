"""Golden vectors from COG-GTM/telco-capacity-rules (spec/vectors.json).

Meridian runs the same file through bin/capacity-test, so both stacks agree.
"""

import pytest
import telco_capacity

from app.inventory import capacity
from app.inventory.capacity import available_capacity, site_capacity, utilization_pct

VECTORS = telco_capacity.vectors()
NAMES = {v["name"] for v in VECTORS}


def test_required_cases_present():
    assert {"normal", "buffer_exceeds_remainder", "zero_total", "zero_buffer"} <= NAMES


def test_capacity_module_reexports_shared_rule():
    assert capacity.available_capacity is telco_capacity.available_capacity
    assert capacity.utilization_pct is telco_capacity.utilization_pct


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_golden_vector(vector):
    total, allocated, buffer_mbps = vector["total"], vector["allocated"], vector["buffer"]
    assert available_capacity(total, allocated, buffer_mbps) == vector["available"]
    assert utilization_pct(total, allocated, buffer_mbps) == vector["utilization_pct"]

    site = site_capacity(
        {
            "total_capacity_mbps": total,
            "allocated_mbps": allocated,
            "maintenance_buffer_mbps": buffer_mbps,
        }
    )
    assert site["available_mbps"] == vector["available"]
    assert site["utilization_pct"] == vector["utilization_pct"]
