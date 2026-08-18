package net.vantage.report.charge;

import java.math.BigDecimal;

/** Usage billed beyond the plan allowance, rated to the exact megabyte. */
public final class OverageCharge extends Charge {

    private final long overageMb;
    private final BigDecimal ratePerMb;

    public OverageCharge(long overageMb, BigDecimal ratePerMb, BigDecimal amount) {
        super("USAGE-OVERAGE", amount);
        if (overageMb < 0L) {
            throw new IllegalArgumentException("overageMb must not be negative: " + overageMb);
        }
        this.overageMb = overageMb;
        this.ratePerMb = ratePerMb;
    }

    public long getOverageMb() {
        return overageMb;
    }

    public BigDecimal getRatePerMb() {
        return ratePerMb;
    }

    @Override
    public BigDecimal signedAmount() {
        return getAmount();
    }
}
