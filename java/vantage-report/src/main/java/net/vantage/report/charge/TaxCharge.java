package net.vantage.report.charge;

import java.math.BigDecimal;
import java.util.Objects;

/** Sales tax applied to the taxable subtotal, before loyalty credits. */
public final class TaxCharge extends Charge {

    private final BigDecimal ratePct;
    private final BigDecimal taxableBase;

    public TaxCharge(BigDecimal ratePct, BigDecimal taxableBase, BigDecimal amount) {
        super("TAX", amount);
        this.ratePct = Objects.requireNonNull(ratePct, "ratePct");
        this.taxableBase = Objects.requireNonNull(taxableBase, "taxableBase");
    }

    public BigDecimal getRatePct() {
        return ratePct;
    }

    public BigDecimal getTaxableBase() {
        return taxableBase;
    }

    @Override
    public BigDecimal signedAmount() {
        return getAmount();
    }
}
