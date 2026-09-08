from decimal import Decimal

from app.billing import invoices as invoice_service
from app.billing.discounts import loyalty_discount
from app.billing.rating import overage_mb, rate_overage


def test_overage_keeps_the_existing_raw_megabyte_field():
    assert overage_mb(3_000_000, 2000) == 3_000_000 - 2000 * 1024


def test_rate_overage_uses_per_gb_rate():
    assert rate_overage(2000 * 1024 + 1000, 2000) == Decimal("10.00")


def test_no_overage_when_under_allowance():
    assert rate_overage(1000, 2000) == Decimal("0.00")


def test_loyalty_discount_comes_off_the_subtotal():
    assert loyalty_discount(Decimal("1000.00"), 8.0) == Decimal("80.00")


def test_enterprise_account_invoice():
    found = invoice_service.list_invoices(account_id="VANTAGE-BILL-88213", period="2026-07")
    assert len(found) == 1
    assert found[0]["legal_name"] == "Beacon Manufacturing Corp"
    assert found[0]["province"] == "BC"


def test_beacon_invoice_uses_shared_meridian_rules():
    invoice = invoice_service.list_invoices(
        account_id="VANTAGE-BILL-88213", period="2026-07"
    )[0]
    assert invoice["invoice_total"] == Decimal("28640.59")
    assert invoice["overage_charges"] == Decimal("22970.00")
    assert invoice["promo_credit"] == Decimal("0.00")
    assert invoice["federal_tax"] == Decimal("1329.40")
    assert invoice["provincial_tax"] == Decimal("1786.71")


def test_usage_without_an_account_is_not_invoiced():
    unlinked = invoice_service.unlinked_usage()
    assert {u["usage_id"] for u in unlinked} == {"VU-2026-06-0447", "VU-2026-07-0447"}
    assert invoice_service.billed_usage_mb() < invoice_service.mediated_usage_mb()
