package net.vantage.report.report;

import net.vantage.report.charge.Charge;
import net.vantage.report.charge.LoyaltyCredit;
import net.vantage.report.charge.OverageCharge;
import net.vantage.report.charge.PlanFeeCharge;
import net.vantage.report.charge.ProrationAdjustment;
import net.vantage.report.charge.TaxCharge;

/**
 * Human-readable labels for charges.
 *
 * <p>Both {@link #describe(Charge)} and {@link #category(Charge)} switch
 * exhaustively over the sealed {@link Charge} hierarchy, so a new charge type
 * is a compile error here until it is handled.
 */
public final class ChargeDescriber {

    public String describe(Charge charge) {
        return switch (charge) {
            case PlanFeeCharge fee -> "Monthly plan fee (" + fee.getPlanCode() + ")";
            case OverageCharge overage -> "Usage overage: " + overage.getOverageMb() + " MB at "
                    + overage.getRatePerMb().toPlainString() + "/MB";
            case TaxCharge tax -> "Sales tax at " + tax.getRatePct().toPlainString() + "% on "
                    + tax.getTaxableBase().toPlainString();
            case LoyaltyCredit credit ->
                    "Loyalty credit of " + credit.getDiscountPct().toPlainString() + "% (post-tax)";
            case ProrationAdjustment adjustment -> "Proration "
                    + (adjustment.isRefund() ? "refund" : "charge")
                    + " for " + adjustment.getDaysInService()
                    + " of " + adjustment.getDaysInPeriod() + " days";
        };
    }

    public String category(Charge charge) {
        return switch (charge) {
            case OverageCharge ignored -> "USAGE";
            case PlanFeeCharge ignored -> "RECURRING";
            case TaxCharge ignored -> "TAX";
            case LoyaltyCredit ignored -> "CREDIT";
            case ProrationAdjustment adjustment -> adjustment.isRefund() ? "CREDIT" : "ADJUSTMENT";
        };
    }
}
