from decimal import Decimal

from app.billing import invoices as invoice_service
from app.billing.latefee import late_fee
from app.billing.lines import multi_line_discount, multi_line_pct
from app.billing.promo import promo_credit, promo_is_live
from app.billing.proration import prorated_plan_charge
from app.billing.suspension import suspended_days, suspension_credit
from app.billing.tax import federal_tax, provincial_tax, rates_for_province


def test_proration_uses_actual_calendar_days():
    # 30 days on the old plan, 1 on the new, in a 31 day month.
    charge = prorated_plan_charge(Decimal("310"), Decimal("620"), 31, "2026-07")
    assert charge == Decimal("620") / 31 * 30 + Decimal("310") / 31


def test_proration_of_a_full_month_is_the_plan_fee():
    assert prorated_plan_charge(Decimal("640"), Decimal("0"), 0, "2026-07") == Decimal("640")


def test_february_days_cost_more_than_july_days():
    february = prorated_plan_charge(Decimal("280"), Decimal("560"), 15, "2026-02")
    july = prorated_plan_charge(Decimal("280"), Decimal("560"), 15, "2026-07")
    assert february > july


def test_promo_credit_lives_thirty_days_past_issue():
    assert promo_is_live("2026-06-24", "2026-07")
    assert promo_credit(Decimal("120"), "2026-06-24", "2026-07") == Decimal("120")


def test_promo_credit_expires_after_thirty_days():
    assert not promo_is_live("2026-05-20", "2026-07")
    assert promo_credit(Decimal("120"), "2026-05-20", "2026-07") == Decimal("0")


def test_suspended_days_are_credited_back():
    days = suspended_days(10, 14)
    assert days == 5
    assert suspension_credit(Decimal("620"), 10, 14, "2026-07") == Decimal("620") / 31 * 5


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


def test_provincial_tax_is_assessed_before_the_loyalty_discount():
    rates = rates_for_province("BC")
    assert federal_tax(Decimal("100"), rates) == Decimal("5")
    assert provincial_tax(Decimal("100"), Decimal("10"), rates) == Decimal("7")


def test_quebec_uses_qst():
    rates = rates_for_province("QC")
    assert rates.provincial_label == "QST"
    assert provincial_tax(Decimal("1000"), Decimal("0"), rates) == Decimal("99.750")


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
