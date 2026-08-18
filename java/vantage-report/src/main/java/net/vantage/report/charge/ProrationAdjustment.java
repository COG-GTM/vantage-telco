package net.vantage.report.charge;

import java.math.BigDecimal;

/** Mid-cycle adjustment, positive when charged and negative when refunded. */
public final class ProrationAdjustment extends Charge {

    private final int daysInService;
    private final int daysInPeriod;
    private final boolean refund;

    public ProrationAdjustment(int daysInService, int daysInPeriod, boolean refund, BigDecimal amount) {
        super("PRORATION", amount);
        if (daysInPeriod <= 0) {
            throw new IllegalArgumentException("daysInPeriod must be positive: " + daysInPeriod);
        }
        if (daysInService < 0 || daysInService > daysInPeriod) {
            throw new IllegalArgumentException("daysInService out of range: " + daysInService);
        }
        this.daysInService = daysInService;
        this.daysInPeriod = daysInPeriod;
        this.refund = refund;
    }

    public int getDaysInService() {
        return daysInService;
    }

    public int getDaysInPeriod() {
        return daysInPeriod;
    }

    public boolean isRefund() {
        return refund;
    }

    @Override
    public BigDecimal signedAmount() {
        return refund ? getAmount().negate() : getAmount();
    }
}
