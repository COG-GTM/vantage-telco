"""Each rule that the two estates disagree on, pinned from both sides.

These are the differences the merge had to keep. A change that makes one of
these tests fail has silently adopted one estate's rule for the other.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from oss.billing.discounts import credit_base, loyalty_discount
from oss.billing.latefee import late_fee
from oss.billing.lines import multi_line_discount
from oss.billing.money import line
from oss.billing.promo import promo_credit
from oss.billing.proration import daily_rate, days_in_period, prorated_plan_charge
from oss.billing.rating import rate_overage, rated_units
from oss.billing.suspension import suspension_credit
from oss.billing.tax import federal_tax, provincial_tax, rates_for_province
from oss.policy import MERIDIAN, VANTAGE, VANTAGE_REPORT

MER = MERIDIAN.billing
VAN = VANTAGE.billing
REPORT = VANTAGE_REPORT.billing


class TestRating:
    """Meridian bills whole GB rounded up at $10; Vantage bills exact MB."""

    def test_a_partial_gigabyte_is_a_whole_billed_gigabyte_on_meridian(self) -> None:
        assert rated_units(10241, 10, MER) == 1
        assert rate_overage(10241, 10, MER) == Decimal("10.00")

    def test_the_same_partial_gigabyte_is_one_megabyte_on_vantage(self) -> None:
        assert rated_units(10241, 10, VAN) == 1
        assert rate_overage(10241, 10, VAN) == Decimal("0.01")

    def test_usage_inside_the_allowance_is_free_on_both(self) -> None:
        assert rate_overage(10240, 10, MER) == Decimal("0")
        assert rate_overage(10240, 10, VAN) == Decimal("0")

    def test_a_full_extra_gigabyte_costs_ten_dollars_either_way(self) -> None:
        # 1024 MB * $0.012 = $12.29 on Vantage, so the estates do not converge.
        assert rate_overage(11264, 10, MER) == Decimal("10.00")
        assert rate_overage(11264, 10, VAN) == Decimal("12.29")


class TestProration:
    """Meridian's month is always 30 days; Vantage uses the calendar."""

    def test_meridian_bills_a_thirty_day_month_in_february(self) -> None:
        assert days_in_period("2026-02", MER) == 30
        assert daily_rate(Decimal("300"), "2026-02", MER) == Decimal("10")

    def test_vantage_bills_the_days_february_actually_has(self) -> None:
        assert days_in_period("2026-02", VAN) == 28
        assert daily_rate(Decimal("280"), "2026-02", VAN) == Decimal("10")

    def test_a_midmonth_plan_change_splits_on_the_estates_month_length(self) -> None:
        meridian = prorated_plan_charge(Decimal("60"), Decimal("30"), 16, "2026-01", MER)
        vantage = prorated_plan_charge(Decimal("62"), Decimal("31"), 16, "2026-01", VAN)
        assert meridian == Decimal("45.00")  # 15 days at $1/day + 15 at $2/day
        assert vantage == Decimal("47.00")  # 15 days at $1/day + 16 at $2/day, January has 31

    def test_no_change_day_bills_the_whole_fee(self) -> None:
        charge = prorated_plan_charge(Decimal("80"), Decimal("40"), 0, "2026-01", MER)
        assert charge == Decimal("80")


class TestPromoExpiry:
    """Meridian honours a promo in its issue cycle only; Vantage for 30 days."""

    PROMO = Decimal("25")

    def test_meridian_drops_a_promo_the_month_after_it_was_issued(self) -> None:
        assert promo_credit(self.PROMO, "2026-06-28", "2026-06", MER) == self.PROMO
        assert promo_credit(self.PROMO, "2026-06-28", "2026-07", MER) == Decimal("0")

    def test_vantage_carries_the_same_promo_into_the_next_cycle(self) -> None:
        assert promo_credit(self.PROMO, "2026-06-28", "2026-07", VAN) == self.PROMO

    def test_vantage_drops_it_once_the_window_closes(self) -> None:
        assert promo_credit(self.PROMO, "2026-05-28", "2026-07", VAN) == Decimal("0")

    def test_an_unissued_promo_is_never_credited(self) -> None:
        assert promo_credit(self.PROMO, None, "2026-07", VAN) == Decimal("0")


class TestSuspensionCredit:
    """Meridian credits nothing for a suspension; Vantage credits the days."""

    def test_meridian_charges_the_full_fee_through_a_suspension(self) -> None:
        assert suspension_credit(Decimal("90"), 5, 14, "2026-06", MER) == Decimal("0")

    def test_vantage_credits_the_daily_rate_for_each_suspended_day(self) -> None:
        # 10 days of a $90 fee over a 30 day June.
        assert suspension_credit(Decimal("90"), 5, 14, "2026-06", VAN) == Decimal("30")

    def test_an_end_before_the_start_credits_nothing(self) -> None:
        assert suspension_credit(Decimal("90"), 14, 5, "2026-06", VAN) == Decimal("0")


class TestTaxBase:
    """Both charge GST pre-discount; only Meridian discounts the PST base."""

    RATES = rates_for_province("BC")
    SUBTOTAL = Decimal("1000")
    LOYALTY = Decimal("100")

    def test_federal_tax_ignores_the_loyalty_credit_on_both_estates(self) -> None:
        assert federal_tax(self.SUBTOTAL, self.LOYALTY, self.RATES, MER) == Decimal("50.00")
        assert federal_tax(self.SUBTOTAL, self.LOYALTY, self.RATES, VAN) == Decimal("50.00")

    def test_meridian_charges_pst_on_what_the_customer_pays(self) -> None:
        assert provincial_tax(self.SUBTOTAL, self.LOYALTY, self.RATES, MER) == Decimal("63.00")

    def test_vantage_charges_pst_on_the_full_invoice(self) -> None:
        assert provincial_tax(self.SUBTOTAL, self.LOYALTY, self.RATES, VAN) == Decimal("70.00")

    def test_a_province_without_a_provincial_component_is_untaxed_locally(self) -> None:
        assert provincial_tax(self.SUBTOTAL, self.LOYALTY, rates_for_province("ON"), MER) == 0


class TestLoyaltyStage:
    """The archived report credits loyalty after tax, the services before it."""

    def test_the_live_estates_credit_loyalty_off_the_subtotal(self) -> None:
        assert credit_base(Decimal("1000"), Decimal("120"), MER) == Decimal("1000")
        assert credit_base(Decimal("1000"), Decimal("120"), VAN) == Decimal("1000")

    def test_the_report_credits_loyalty_off_the_taxed_amount(self) -> None:
        assert credit_base(Decimal("1000"), Decimal("120"), REPORT) == Decimal("1120")

    def test_which_makes_the_report_credit_larger_for_the_same_rate(self) -> None:
        live = loyalty_discount(
            credit_base(Decimal("1000"), Decimal("120"), VAN), Decimal("10"), VAN
        )
        archived = loyalty_discount(
            credit_base(Decimal("1000"), Decimal("120"), REPORT), Decimal("10"), REPORT
        )
        assert archived > live


class TestRounding:
    """Meridian rounds every line as a double; Vantage rounds once, at the end."""

    def test_meridian_rounds_a_line_to_cents_as_it_is_produced(self) -> None:
        assert line(Decimal("10.005"), MER) == Decimal("10.01")

    def test_vantage_carries_the_line_at_full_precision(self) -> None:
        assert line(Decimal("10.005"), VAN) == Decimal("10.005")

    def test_meridian_rounds_a_half_cent_the_way_the_legacy_register_did(self) -> None:
        # float(125.445) * 100 lands just above the half cent, so it rounds up;
        # rounding the decimal value would give 125.44 and move the invoice.
        assert line(Decimal("125.445"), MER) == Decimal("125.45")
        assert line(Decimal("143.325"), MER) == Decimal("143.32")


class TestSharedRules:
    """Rules the estates agree on, kept in one place by the merge."""

    @pytest.mark.parametrize("policy", [MER, VAN])
    def test_multi_line_tiers_are_the_same_schedule(self, policy) -> None:
        assert multi_line_discount(Decimal("100"), 2, policy) == Decimal("0")
        assert multi_line_discount(Decimal("100"), 3, policy) == Decimal("5")
        assert multi_line_discount(Decimal("100"), 10, policy) == Decimal("10")

    @pytest.mark.parametrize("policy", [MER, VAN])
    def test_a_late_fee_needs_a_balance_past_the_grace_period(self, policy) -> None:
        assert late_fee(Decimal("200"), "2026-06-25", "2026-07", policy) == Decimal("0")
        assert late_fee(Decimal("200"), "2026-05-01", "2026-07", policy) == Decimal("3.00")
        assert late_fee(Decimal("0"), "2026-05-01", "2026-07", policy) == Decimal("0")
