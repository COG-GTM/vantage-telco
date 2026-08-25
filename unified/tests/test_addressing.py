"""Management addressing, which both estates number the same way."""

from __future__ import annotations

import ipaddress

import pytest

from oss.network import addressing
from oss.service import get_estate


@pytest.fixture(scope="module")
def devices():
    return get_estate("vantage").devices()


def test_the_plan_is_a_sixteen_with_a_growth_pool_carved_out() -> None:
    assert addressing.MANAGEMENT_SUPERNET == ipaddress.ip_network("10.20.0.0/16")
    assert addressing.GROWTH_POOL.subnet_of(addressing.MANAGEMENT_SUPERNET)
    assert addressing.in_supernet("10.20.7.5")
    assert not addressing.in_supernet("10.30.7.5")
    assert addressing.in_growth_pool("10.20.250.9")


def test_every_managed_device_is_numbered_inside_the_supernet(devices) -> None:
    outside = [d.device_name for d in devices if not addressing.in_supernet(d.mgmt_ip)]
    assert outside == []


def test_subnet_usage_accounts_for_every_device(devices) -> None:
    assert sum(addressing.subnet_usage(devices).values()) == len(devices)


def test_duplicate_detection_flags_a_reused_address(devices) -> None:
    duplicates = addressing.duplicate_addresses(devices)
    for names in duplicates.values():
        assert len(names) > 1


def test_orphan_check_only_reports_management_addresses_no_device_owns(devices) -> None:
    assigned = set(addressing.assigned_addresses(devices))
    for ip in addressing.orphaned_references(devices):
        assert ip not in assigned
        assert addressing.in_supernet(ip)


def test_a_summary_can_be_produced_for_either_estate() -> None:
    for name in ("meridian", "vantage"):
        summary = get_estate(name).addressing_summary()
        assert summary["device_count"] > 0
        assert summary["config_files"] > 0
