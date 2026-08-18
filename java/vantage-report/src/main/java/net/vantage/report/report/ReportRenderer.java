package net.vantage.report.report;

import java.math.BigDecimal;
import java.util.List;

import net.vantage.report.charge.Charge;
import net.vantage.report.model.Invoice;
import net.vantage.report.model.UsageRecord;
import net.vantage.report.util.Money;

/**
 * Renders invoices as the plain-text artifacts the NOC archives per cycle.
 *
 * <p>Every template is assembled with explicit concatenation and {@code \n}
 * escapes so the output stays byte-identical to the legacy Perl renderer.
 */
public final class ReportRenderer {

    private static final String RULE = "--------------------------------------------------------";
    private static final int LABEL_WIDTH = 38;

    private final ChargeDescriber describer = new ChargeDescriber();

    public String renderInvoice(Invoice invoice) {
        StringBuilder out = new StringBuilder();
        out.append("VANTAGE NETWORK SERVICES\n");
        out.append("Invoice for period ").append(invoice.getPeriod()).append("\n");
        out.append(RULE).append("\n");
        out.append("Account:  ").append(invoice.getAccount().getAccountId()).append("\n");
        out.append("Customer: ").append(invoice.getAccount().getLegalName()).append("\n");
        out.append("Plan:     ").append(invoice.getAccount().getPlanCode()).append("\n");
        out.append(RULE).append("\n");

        for (Charge charge : invoice.getCharges()) {
            String label = describer.describe(charge);
            out.append(pad(label)).append(Money.format(charge.signedAmount())).append("\n");
        }

        out.append(RULE).append("\n");
        out.append(pad("TOTAL DUE")).append(Money.format(invoice.total())).append("\n");
        return out.toString();
    }

    public String renderCycleSummary(String period, List<Invoice> invoices, List<UsageRecord> unlinked) {
        BigDecimal billed = invoices.stream()
                .map(Invoice::total)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        StringBuilder out = new StringBuilder();
        out.append("BILLING CYCLE SUMMARY\n");
        out.append("Period:            ").append(period).append("\n");
        out.append("Invoices rendered: ").append(invoices.size()).append("\n");
        out.append("Amount billed:     ").append(Money.format(billed)).append("\n");
        out.append("Unlinked records:  ").append(unlinked.size()).append("\n");

        if (!unlinked.isEmpty()) {
            out.append(RULE).append("\n");
            out.append("UNLINKED USAGE (no billing account)\n");
            for (UsageRecord record : unlinked) {
                out.append("  ")
                        .append(record.getAccountId())
                        .append("  device=")
                        .append(record.getDeviceUuid())
                        .append("  ")
                        .append(record.getUsageMb())
                        .append(" MB\n");
            }
        }
        return out.toString();
    }

    public String renderCsv(List<Invoice> invoices) {
        StringBuilder out = new StringBuilder();
        out.append("account_id,period,category,code,amount\n");
        for (Invoice invoice : invoices) {
            for (Charge charge : invoice.getCharges()) {
                out.append(invoice.getAccount().getAccountId())
                        .append(',')
                        .append(invoice.getPeriod())
                        .append(',')
                        .append(describer.category(charge))
                        .append(',')
                        .append(charge.getCode())
                        .append(',')
                        .append(Money.round(charge.signedAmount()).toPlainString())
                        .append('\n');
            }
        }
        return out.toString();
    }

    private static String pad(String label) {
        if (label.length() >= LABEL_WIDTH) {
            return label;
        }
        return label + " ".repeat(LABEL_WIDTH - label.length());
    }
}
