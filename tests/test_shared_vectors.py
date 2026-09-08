from telco_capacity import vectors

from app.inventory.capacity import available_capacity, utilization_pct


def test_shared_vectors():
    for vector in vectors():
        assert available_capacity(
            vector["total"], vector["allocated"], vector["buffer"]
        ) == vector["available"]
        assert utilization_pct(
            vector["total"], vector["allocated"], vector["buffer"]
        ) == vector["utilization_pct"]
