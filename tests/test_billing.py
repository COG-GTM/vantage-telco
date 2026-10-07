from decimal import Decimal

from app.billing import invoices as invoice_service
from app.billing.discounts import loyalty_discount
from app.billing.rating import overage_mb, rate_overage


def test_measured_overage_megabytes_are_still_reported():
    assert overage_mb(3_000_000, 2000) == 3_000_000 - 2000 * 1024


def test_rate_overage_rounds_up_to_whole_gigabytes_at_ten_dollars():
    assert rate_overage(2000 * 1024 + 1000, 2000) == Decimal("10.00")
    assert rate_overage(2000 * 1024 + 1025, 2000) == Decimal("20.00")


def test_no_overage_when_under_allowance():
    assert rate_overage(1000, 2000) == Decimal("0.00")


def test_loyalty_discount_comes_off_the_subtotal():
    assert loyalty_discount(Decimal("1000.00"), 8.0) == Decimal("80.00")


def test_enterprise_account_invoice():
    found = invoice_service.list_invoices(account_id="VANTAGE-BILL-88213", period="2026-07")
    assert len(found) == 1
    assert found[0]["legal_name"] == "Beacon Manufacturing Corp"
    assert found[0]["province"] == "BC"


def test_usage_without_an_account_is_not_invoiced():
    unlinked = invoice_service.unlinked_usage()
    assert {u["usage_id"] for u in unlinked} == {"VU-2026-06-0447", "VU-2026-07-0447"}
    assert invoice_service.billed_usage_mb() < invoice_service.mediated_usage_mb()
