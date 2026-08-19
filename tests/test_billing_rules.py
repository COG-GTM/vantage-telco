"""Billing rules as vantage now bills them.

The rules themselves live in the shared library (COG-GTM/telco-billing-rules,
vendored into vendor/) and are covered there by conformance vectors captured
from the meridian register. These checks state the behaviour vantage depends on,
so a shared-library change that moved it would fail here.
"""

from decimal import Decimal

from app.billing import invoices as invoice_service
from app.billing.rules import (
    federal_tax,
    late_fee,
    multi_line_discount,
    multi_line_pct,
    promo_credit,
    promo_is_live,
    prorated_plan_charge,
    provincial_tax,
    rates_for_province,
    suspended_days,
    suspension_credit,
)


def test_proration_uses_a_fixed_thirty_day_month():
    # Half the billing month on each plan, whatever the calendar says.
    assert prorated_plan_charge(Decimal("300"), Decimal("600"), 16, "2026-07") == Decimal("450")


def test_proration_of_a_full_month_is_the_plan_fee():
    assert prorated_plan_charge(Decimal("640"), Decimal("0"), 0, "2026-07") == Decimal("640")


def test_february_days_cost_the_same_as_july_days():
    february = prorated_plan_charge(Decimal("280"), Decimal("560"), 15, "2026-02")
    july = prorated_plan_charge(Decimal("280"), Decimal("560"), 15, "2026-07")
    assert february == july


def test_promo_credit_lives_only_in_the_cycle_it_was_issued_in():
    assert promo_is_live("2026-07-04", "2026-07")
    assert promo_credit(Decimal("120"), "2026-07-04", "2026-07") == Decimal("120")


def test_promo_credit_from_a_previous_cycle_is_dead():
    assert not promo_is_live("2026-06-24", "2026-07")
    assert promo_credit(Decimal("120"), "2026-06-24", "2026-07") == Decimal("0")


def test_suspended_days_stay_billed():
    assert suspended_days(10, 14) == 5
    assert suspension_credit(Decimal("620"), 10, 14, "2026-07") == Decimal("0")


def test_no_suspension_means_no_credit():
    assert suspension_credit(Decimal("620"), 0, 0, "2026-07") == Decimal("0")


def test_multi_line_discount_tiers():
    assert multi_line_pct(2) == Decimal("0")
    assert multi_line_pct(3) == Decimal("5")
    assert multi_line_pct(10) == Decimal("10")
    assert multi_line_discount(Decimal("1000"), 12) == Decimal("100")


def test_late_fee_waived_inside_grace():
    assert late_fee(Decimal("500"), "2026-06-30", "2026-07") == Decimal("0")


def test_late_fee_charged_past_grace():
    assert late_fee(Decimal("500"), "2026-06-01", "2026-07") == Decimal("7.5")


def test_harmonized_province_has_no_separate_provincial_line():
    rates = rates_for_province("ON")
    assert rates.federal_label == "HST"
    assert provincial_tax(Decimal("100"), Decimal("10"), rates) == Decimal("0")


def test_provincial_tax_is_assessed_after_the_loyalty_discount():
    rates = rates_for_province("BC")
    assert federal_tax(Decimal("100"), rates) == Decimal("5")
    assert provincial_tax(Decimal("100"), Decimal("10"), rates) == Decimal("6.30")


def test_quebec_uses_qst():
    rates = rates_for_province("QC")
    assert rates.provincial_label == "QST"
    assert provincial_tax(Decimal("1000"), Decimal("100"), rates) == Decimal("89.78")


def test_invoice_carries_province_and_tax_lines():
    invoice = invoice_service.list_invoices(account_id="VANTAGE-BILL-70013", period="2026-07")[0]
    assert invoice["province"] == "ON"
    assert invoice["federal_tax_label"] == "HST"
    expected = (
        Decimal(str(invoice["subtotal"]))
        - Decimal(str(invoice["loyalty_discount"]))
        + Decimal(str(invoice["federal_tax"]))
        + Decimal(str(invoice["provincial_tax"]))
    )
    assert abs(Decimal(str(invoice["invoice_total"])) - expected) <= Decimal("0.01")


def test_fixture_book_covers_every_province():
    invoices = invoice_service.list_invoices(period="2026-07")
    assert len(invoices) == 200
    assert {i["province"] for i in invoices} == {"BC", "AB", "ON", "QC"}
