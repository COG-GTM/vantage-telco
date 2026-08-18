package net.vantage.report.model;

import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;

import net.vantage.report.charge.Charge;
import net.vantage.report.util.Money;

/** An invoice: the account it belongs to, the period, and its ordered charges. */
public final class Invoice {

    private final Account account;
    private final String period;
    private final List<Charge> charges;

    public Invoice(Account account, String period, List<Charge> charges) {
        this.account = Objects.requireNonNull(account, "account");
        this.period = Objects.requireNonNull(period, "period");
        this.charges = List.copyOf(charges);
    }

    public Account getAccount() {
        return account;
    }

    public String getPeriod() {
        return period;
    }

    public List<Charge> getCharges() {
        return charges;
    }

    public BigDecimal total() {
        BigDecimal total = charges.stream()
                .map(Charge::signedAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        return Money.round(total);
    }

    @Override
    public String toString() {
        return "Invoice{account=" + account.getAccountId()
                + ", period=" + period
                + ", charges=" + charges.size()
                + ", total=" + total()
                + '}';
    }
}
