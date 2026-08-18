package net.vantage.report.charge;

import java.math.BigDecimal;
import java.util.Objects;

/** Recurring monthly fee for the account's plan. */
public final class PlanFeeCharge extends Charge {

    private final String planCode;

    public PlanFeeCharge(String planCode, BigDecimal amount) {
        super("PLAN-FEE", amount);
        this.planCode = Objects.requireNonNull(planCode, "planCode");
    }

    public String getPlanCode() {
        return planCode;
    }

    @Override
    public BigDecimal signedAmount() {
        return getAmount();
    }
}
