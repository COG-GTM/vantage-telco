from telco_capacity import RULE, can_support, vectors

from app.inventory.capacity import available_capacity, utilization_pct
from app.inventory.locations import AVAILABILITY_RULE


def test_shared_vectors():
    assert AVAILABILITY_RULE == RULE
    for vector in vectors():
        assert available_capacity(
            vector["total"], vector["allocated"], vector["buffer"]
        ) == vector["available"]
        assert utilization_pct(
            vector["total"], vector["allocated"], vector["buffer"]
        ) == vector["utilization_pct"]
        assert can_support(vector["available"], vector["available"]) is True
        assert can_support(vector["available"], vector["available"] + 1) is False
