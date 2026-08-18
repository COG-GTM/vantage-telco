package net.vantage.report.model;

import java.math.BigDecimal;
import java.util.Objects;

/**
 * A billing account as stored in the {@code accounts} collection.
 *
 * <p>Written as a plain immutable value class: constructor, getters, equals,
 * hashCode and toString are all maintained by hand.
 */
public final class Account {

    private final String accountId;
    private final String legalName;
    private final String planCode;
    private final int includedGb;
    private final BigDecimal loyaltyDiscountPct;
    private final BigDecimal taxPct;

    public Account(
            String accountId,
            String legalName,
            String planCode,
            int includedGb,
            BigDecimal loyaltyDiscountPct,
            BigDecimal taxPct) {
        this.accountId = Objects.requireNonNull(accountId, "accountId");
        this.legalName = Objects.requireNonNull(legalName, "legalName");
        this.planCode = Objects.requireNonNull(planCode, "planCode");
        if (includedGb < 0) {
            throw new IllegalArgumentException("includedGb must not be negative: " + includedGb);
        }
        this.includedGb = includedGb;
        this.loyaltyDiscountPct = Objects.requireNonNull(loyaltyDiscountPct, "loyaltyDiscountPct");
        this.taxPct = Objects.requireNonNull(taxPct, "taxPct");
    }

    public String getAccountId() {
        return accountId;
    }

    public String getLegalName() {
        return legalName;
    }

    public String getPlanCode() {
        return planCode;
    }

    public int getIncludedGb() {
        return includedGb;
    }

    public BigDecimal getLoyaltyDiscountPct() {
        return loyaltyDiscountPct;
    }

    public BigDecimal getTaxPct() {
        return taxPct;
    }

    public boolean hasLoyaltyDiscount() {
        return loyaltyDiscountPct.compareTo(BigDecimal.ZERO) > 0;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof Account that)) {
            return false;
        }
        return includedGb == that.includedGb
                && accountId.equals(that.accountId)
                && legalName.equals(that.legalName)
                && planCode.equals(that.planCode)
                && loyaltyDiscountPct.compareTo(that.loyaltyDiscountPct) == 0
                && taxPct.compareTo(that.taxPct) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(accountId, legalName, planCode, includedGb);
    }

    @Override
    public String toString() {
        return "Account{"
                + "accountId=" + accountId
                + ", legalName=" + legalName
                + ", planCode=" + planCode
                + ", includedGb=" + includedGb
                + ", loyaltyDiscountPct=" + loyaltyDiscountPct
                + ", taxPct=" + taxPct
                + '}';
    }
}
