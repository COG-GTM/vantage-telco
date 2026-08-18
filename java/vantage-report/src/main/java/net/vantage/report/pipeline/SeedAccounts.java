package net.vantage.report.pipeline;

import java.math.BigDecimal;
import java.util.List;

import net.vantage.report.model.Account;

/**
 * The accounts the report module runs against locally, kept in step with
 * {@code data/seed/accounts.json}.
 */
public final class SeedAccounts {

    private SeedAccounts() {
        throw new AssertionError("no instances");
    }

    public static List<Account> load() {
        return List.of(
                new Account(
                        "VANTAGE-BILL-88213",
                        "Beacon Manufacturing Corp",
                        "ENTERPRISE-FLEX",
                        3000,
                        new BigDecimal("8.0"),
                        new BigDecimal("6.25")),
                new Account(
                        "VANTAGE-BILL-70000",
                        "Northgate Logistics LLC",
                        "BUSINESS-FLEX",
                        500,
                        new BigDecimal("0.0"),
                        new BigDecimal("6.25")),
                new Account(
                        "VANTAGE-BILL-70013",
                        "Cedar Point Health Systems",
                        "BUSINESS-FLEX",
                        1000,
                        new BigDecimal("4.0"),
                        new BigDecimal("6.25")),
                new Account(
                        "VANTAGE-BILL-70044",
                        "Harborline Transit Authority",
                        "METRO-BURST",
                        250,
                        new BigDecimal("2.5"),
                        new BigDecimal("6.25")));
    }
}
