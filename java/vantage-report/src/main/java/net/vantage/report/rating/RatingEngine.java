package net.vantage.report.rating;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

import net.vantage.report.charge.Charge;
import net.vantage.report.charge.LoyaltyCredit;
import net.vantage.report.charge.OverageCharge;
import net.vantage.report.charge.PlanFeeCharge;
import net.vantage.report.charge.TaxCharge;
import net.vantage.report.model.Account;
import net.vantage.report.model.Invoice;
import net.vantage.report.model.UsageRecord;
import net.vantage.report.util.Money;

/**
 * Rates mediated usage into invoices.
 *
 * <p>Mirrors {@code app/billing}: usage is rated to the exact megabyte, tax is
 * charged on the pre-discount subtotal, and the loyalty discount is applied
 * after tax as a credit.
 */
public final class RatingEngine {

    public static final BigDecimal OVERAGE_RATE_PER_MB = new BigDecimal("0.012");
    public static final long MB_PER_GB = 1024L;

    private static final Map<String, BigDecimal> PLAN_FEES = Map.of(
            "ENTERPRISE-FLEX", new BigDecimal("2400.00"),
            "BUSINESS-FLEX", new BigDecimal("650.00"),
            "METRO-BURST", new BigDecimal("310.00"));

    private final Map<String, Account> accountsById;

    public RatingEngine(List<Account> accounts) {
        this.accountsById = Collections.unmodifiableMap(accounts.stream().collect(Collectors.toMap(
                Account::getAccountId, Function.identity(), (first, second) -> second, LinkedHashMap::new)));
    }

    public long overageMb(long usageMb, int includedGb) {
        long includedMb = includedGb * MB_PER_GB;
        long overage = usageMb - includedMb;
        return overage > 0L ? overage : 0L;
    }

    public BigDecimal rateOverage(long usageMb, int includedGb) {
        long overage = overageMb(usageMb, includedGb);
        return Money.round(BigDecimal.valueOf(overage).multiply(OVERAGE_RATE_PER_MB));
    }

    public BigDecimal planFee(String planCode) {
        BigDecimal fee = PLAN_FEES.get(planCode);
        if (fee == null) {
            throw new IllegalArgumentException("unknown plan code: " + planCode);
        }
        return fee;
    }

    /** Sums usage per account, dropping records that have no billing account. */
    public Map<String, Long> mediate(List<UsageRecord> records) {
        Map<String, Long> totals = new LinkedHashMap<>();
        for (UsageRecord record : records) {
            if (!accountsById.containsKey(record.getAccountId())) {
                continue;
            }
            totals.merge(record.getAccountId(), record.getUsageMb(), Long::sum);
        }
        return totals;
    }

    /** Usage that could not be attached to any account, newest first. */
    public List<UsageRecord> unlinked(List<UsageRecord> records) {
        return records.stream()
                .filter(record -> !accountsById.containsKey(record.getAccountId()))
                .sorted(Comparator.comparing(UsageRecord::getPeriod, Comparator.reverseOrder())
                        .thenComparing(UsageRecord::getAccountId))
                .toList();
    }

    public Optional<Account> findAccount(String accountId) {
        return Optional.ofNullable(accountsById.get(accountId));
    }

    public Invoice buildInvoice(String accountId, String period, long usageMb) {
        Account account = findAccount(accountId)
                .orElseThrow(() -> new IllegalArgumentException("no such account: " + accountId));

        List<Charge> charges = new ArrayList<>();
        charges.add(new PlanFeeCharge(account.getPlanCode(), planFee(account.getPlanCode())));

        long overage = overageMb(usageMb, account.getIncludedGb());
        if (overage > 0L) {
            charges.add(new OverageCharge(
                    overage, OVERAGE_RATE_PER_MB, rateOverage(usageMb, account.getIncludedGb())));
        }

        BigDecimal taxable = BigDecimal.ZERO;
        for (Charge charge : charges) {
            taxable = taxable.add(charge.signedAmount());
        }
        taxable = Money.round(taxable);

        BigDecimal tax = Money.percentOf(taxable, account.getTaxPct());
        charges.add(new TaxCharge(account.getTaxPct(), taxable, tax));

        if (account.hasLoyaltyDiscount()) {
            BigDecimal postTax = Money.round(taxable.add(tax));
            charges.add(new LoyaltyCredit(
                    account.getLoyaltyDiscountPct(),
                    Money.percentOf(postTax, account.getLoyaltyDiscountPct())));
        }

        return new Invoice(account, period, charges);
    }

    /** Invoices for every account with mediated usage, ordered by account id. */
    public List<Invoice> buildInvoices(String period, List<UsageRecord> records) {
        return mediate(records).entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .map(entry -> buildInvoice(entry.getKey(), period, entry.getValue()))
                .toList();
    }
}
