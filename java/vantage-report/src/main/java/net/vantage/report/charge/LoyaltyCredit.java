package net.vantage.report.charge;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * Loyalty discount. Vantage applies it after tax, as a credit against the
 * invoice total, so it never reduces the taxable base.
 */
public final class LoyaltyCredit extends Charge {

    private final BigDecimal discountPct;

    public LoyaltyCredit(BigDecimal discountPct, BigDecimal amount) {
        super("LOYALTY-CREDIT", amount);
        this.discountPct = Objects.requireNonNull(discountPct, "discountPct");
    }

    public BigDecimal getDiscountPct() {
        return discountPct;
    }

    @Override
    public BigDecimal signedAmount() {
        return getAmount().negate();
    }
}
