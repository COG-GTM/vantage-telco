package net.vantage.report.charge;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * Base type for every line that can appear on an invoice.
 *
 * <p>The hierarchy is sealed, so callers dispatch with an exhaustive
 * {@code switch} over the permitted subtypes.
 */
public abstract sealed class Charge
        permits LoyaltyCredit, OverageCharge, PlanFeeCharge, ProrationAdjustment, TaxCharge {

    private final String code;
    private final BigDecimal amount;

    protected Charge(String code, BigDecimal amount) {
        this.code = Objects.requireNonNull(code, "code");
        this.amount = Objects.requireNonNull(amount, "amount");
    }

    public String getCode() {
        return code;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    /** Signed contribution of this charge to the invoice total. */
    public abstract BigDecimal signedAmount();

    @Override
    public String toString() {
        return getClass().getSimpleName() + "{code=" + code + ", amount=" + amount + '}';
    }
}
